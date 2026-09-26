"""Check timestamp alignment and metrics with synthetic fixtures in a temp dir."""
import argparse
import json
from pathlib import Path
import tempfile
import numpy as np
from signal_utils import ROOT
from evaluate_signals import evaluate

def main():
    with tempfile.TemporaryDirectory(prefix='video-vitals-check-') as tmp:
        p=Path(tmp);n=1800;fs=30;t=np.arange(n)/fs
        pulse=np.sin(2*np.pi*1.2*t);resp=np.sin(2*np.pi*.25*t)
        np.savez(p/'signals.npz',time_s=t,pulse_integrated=pulse,resp_integrated=resp)
        cfg={'fps':fs,'pulse_band_hz':[.75,2.5],'resp_band_hz':[.08,.5],'filter_order':1,'detrend_lambda':100}
        (p/'summary.json').write_text(json.dumps({'kind':'synthetic_fixture_only','config':cfg}))
        np.savetxt(p/'truth.csv',np.column_stack([t-2,pulse,resp]),delimiter=',',header='time_s,pulse,resp',comments='')
        args=argparse.Namespace(prediction_dir=p,ground_truth=p/'truth.csv',gt_offset_s=2,sync_note='Synthetic clock is deliberately offset by -2 s',output=p/'evaluation')
        evaluate(args)
        report=json.loads((p/'evaluation/evaluation.json').read_text())
        for name,count in [('pulse',2),('resp',1)]:
            r=report['signals'][name]
            assert r['valid_windows']==count
            assert r['metrics']['mae_per_min']==0
            assert all(abs(w['waveform_pearson_no_lag']-1)<1e-10 for w in r['windows'])
        np.savetxt(p/'truth.csv',np.column_stack([t-2,pulse]),delimiter=',',header='time_s,pulse',comments='')
        evaluate(args)
        report=json.loads((p/'evaluation/evaluation.json').read_text())
        assert report['signals']['resp']['status']=='no_corresponding_ground_truth'
    result={'kind':'synthetic_software_check_only','known_clock_offset_alignment':'passed','window_counts':'passed','known_rate_error':'passed','missing_resp_label_gate':'passed'}
    (ROOT/'results/evaluation_software_check.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
