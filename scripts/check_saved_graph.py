"""Compare source-built model against architecture serialized in official HDF5."""
import json
import h5py
import numpy as np
from audit_mtts import ROOT,tf,load_module,build_model

mod=load_module(True)
weight=ROOT/'third_party/MTTS-CAN/mtts_can.hdf5'
with h5py.File(weight) as f:
    config=f.attrs['model_config']
restored=tf.keras.models.model_from_json(config,custom_objects={'TSM':mod.TSM,'Attention_mask':mod.Attention_mask})
restored.load_weights(str(weight))
tf.keras.backend.clear_session()
constructed=build_model()
constructed.load_weights(str(weight))
x=np.random.default_rng(2026).normal(size=(20,36,36,3)).astype('float32')
a=restored([x,x],training=False)
b=constructed([x,x],training=False)
error=max(float(np.max(abs(i.numpy()-j.numpy()))) for i,j in zip(a,b))
assert error<1e-6,error
report={'kind':'software_check_only','serialized_vs_source_max_abs_error':error,'passed':True}
(ROOT/'results/mtts_serialized_graph_check.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
