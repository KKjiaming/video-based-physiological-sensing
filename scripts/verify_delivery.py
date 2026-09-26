"""Check actual files and numeric consistency; never proves physiological accuracy."""
from pathlib import Path
import hashlib
import json
import subprocess
import numpy as np
from scipy import signal

ROOT=Path(__file__).resolve().parents[1]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    checks={}
    sources=json.loads((ROOT/'configs/sources.json').read_text())
    for name,entry in sources.items():
        repo=ROOT/'third_party'/name
        assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()==entry['commit']
        assert sha(repo/entry['weight'])==entry['weight_sha256']
        checks[name+'_source_and_weight']='passed'
    data=json.loads((ROOT/'configs/data_source.json').read_text())
    assert sha(ROOT/'data/mit_face.mp4')==data['sha256']
    audit=json.loads((ROOT/'results/mtts_audit.json').read_text())
    assert audit['public_keras_compat']['all_named_weights_match']
    assert not audit['unmodified_source']['all_named_weights_match']
    assert json.loads((ROOT/'results/mtts_serialized_graph_check.json').read_text())['serialized_vs_source_max_abs_error']<1e-6
    big=json.loads((ROOT/'results/bigsmall_audit.json').read_text())
    assert big['strict_load']=='passed' and big['all_named_weights_match']
    assert big['original_repo']['strict_load']=='passed' and big['original_repo']['all_finite']
    for method in ['mtts','bigsmall']:
        out=ROOT/f'results/{method}_mit_face_demo';meta=json.loads((out/'summary.json').read_text())
        arrays=np.load(out/'signals.npz');n=meta['predicted_frames'];fs=meta['config']['fps']
        assert meta['kind']=='real_video_inference_demo_without_ground_truth'
        assert meta['gt_available'] is False and meta['accuracy_metrics'] is None
        assert len(arrays['time_s'])==n and np.all(np.diff(arrays['time_s'])>0)
        for name in ['pulse','resp']:
            for suffix in ['raw_difference','integrated','detrended','filtered']:
                x=arrays[name+'_'+suffix];assert x.shape==(n,) and np.isfinite(x).all()
            if method=='mtts':
                f,p=signal.periodogram(arrays[name+'_filtered'],fs=fs,window='hann',detrend='constant',nfft=n)
            else:
                f,p=signal.periodogram(arrays[name+'_filtered'],fs=fs,nfft=1<<(n-1).bit_length(),detrend=False)
            lo,hi=meta['config'][name+'_band_hz'];ix=np.flatnonzero((f>=lo)&(f<=hi));rate=60*f[ix[np.argmax(p[ix])]]
            assert abs(rate-meta[name+'_rate_per_min'])<1e-10
        assert (out/'predictions.png').read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
        checks[method+'_real_video_artifacts']='passed'
    for name in ['signal_math_check.json','evaluation_software_check.json']:
        assert json.loads((ROOT/'results'/name).read_text())['kind']=='synthetic_software_check_only'
    ignored=subprocess.check_output(['git','-C',str(ROOT),'check-ignore','data/mit_face.mp4','third_party/MTTS-CAN/mtts_can.hdf5','.venv/bin/python','.venv-bigsmall/bin/python'],text=True)
    assert len(ignored.strip().splitlines())==4
    assert subprocess.check_output(['git','-C',str(ROOT),'remote'],text=True).strip()==''
    checks['large_files_ignored_and_no_remote']='passed'
    report={'kind':'delivery_integrity_check_not_accuracy_evaluation','checks':checks,'passed':True}
    (ROOT/'results/delivery_verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':main()
