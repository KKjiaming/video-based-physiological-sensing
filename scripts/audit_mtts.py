"""Strict checkpoint check. Random data is a software check, never an experiment."""
import os
os.environ.setdefault('CUDA_VISIBLE_DEVICES', '-1')
os.environ.setdefault('TF_NUM_INTRAOP_THREADS', '4')
os.environ.setdefault('TF_NUM_INTEROP_THREADS', '2')
from pathlib import Path
import hashlib
import json
import sys
import types
import traceback
import h5py
import numpy as np
import tensorflow as tf

ROOT = Path(__file__).resolve().parents[1]

def load_module(public_api=True):
    source = ROOT / 'third_party/MTTS-CAN/code/model.py'
    code = source.read_text()
    if public_api:
        code = code.replace('tensorflow.python.keras', 'tensorflow.keras')
    module = types.ModuleType('mtts_compat' if public_api else 'mtts_original')
    module.__file__ = str(source)
    sys.modules[module.__name__] = module
    exec(compile(code, str(source), 'exec'), module.__dict__)
    return module

def build_model():
    return load_module(True).MTTS_CAN(10, 32, 64, (36, 36, 3))

if __name__ == '__main__':
    weight = ROOT / 'third_party/MTTS-CAN/mtts_can.hdf5'
    report = {'kind': 'software_check_only', 'tensorflow': tf.__version__,
              'weight_sha256': hashlib.sha256(weight.read_bytes()).hexdigest(),
              'weight_bytes': weight.stat().st_size, 'devices': [str(x) for x in tf.config.list_physical_devices()]}
    with h5py.File(weight) as f:
        report['hdf5_attributes'] = {k: str(v) for k,v in f.attrs.items() if k != 'model_config'}
        shapes = {}
        f.visititems(lambda k,v: shapes.update({k:list(v.shape)}) if isinstance(v,h5py.Dataset) else None)
        report['weight_shapes'] = shapes
        if 'model_config' in f.attrs:
            report['saved_model_config'] = json.loads(f.attrs['model_config'])
    forward_outputs = {}
    for public in [False, True]:
        key = 'public_keras_compat' if public else 'unmodified_source'
        try:
            tf.keras.backend.clear_session()
            m = load_module(public).MTTS_CAN(10,32,64,(36,36,3))
            m.load_weights(str(weight))  # strict, no skip_mismatch or by_name
            mapping = {}
            with h5py.File(weight) as checkpoint:
                group=checkpoint['model_weights']
                for layer in m.layers:
                    if not layer.weights: continue
                    stored=[group[layer.name][name][()] for name in group[layer.name].attrs['weight_names']]
                    mapping[layer.name]=max(float(np.max(np.abs(a-b))) for a,b in zip(layer.get_weights(),stored))
            x = np.random.default_rng(2026).normal(size=(20,36,36,3)).astype('float32')
            ys = m([x,x], training=False)
            forward_outputs[key] = [v.numpy() for v in ys]
            report[key] = {'strict_load':'passed', 'per_layer_weight_max_abs_difference':mapping,'all_named_weights_match':all(v==0 for v in mapping.values()), 'input_shapes': [list(v.shape) for v in m.inputs],
                           'output_shapes':[list(v.shape) for v in ys], 'parameters':m.count_params(),
                           'finite':all(bool(np.isfinite(v.numpy()).all()) for v in ys)}
        except Exception:
            report[key] = {'error': traceback.format_exc()}
    if len(forward_outputs)==2:
        report['original_public_forward_max_abs_difference'] = max(float(np.max(np.abs(a-b))) for a,b in zip(forward_outputs['unmodified_source'],forward_outputs['public_keras_compat']))
    (ROOT/'results/mtts_audit.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k not in ['saved_model_config','weight_shapes','hdf5_attributes']},indent=2))

    if not report["public_keras_compat"].get("all_named_weights_match", False) or not report["public_keras_compat"].get("finite", False):
        raise SystemExit("Strict compatible model audit failed; inference must not be claimed.")
