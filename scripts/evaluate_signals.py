"""Evaluate only supplied synchronized ground truth; never infer labels from video.

CSV: time_s,pulse[,resp]; amplitudes are sensor waveforms, not HR/RR scalars.
Sensor time + --gt-offset-s must equal the video's relative time.
"""
from pathlib import Path
import argparse
import json
import hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import signal
from signal_utils import detrend, spectral_rate

def evaluate(args):
    summary=json.loads((args.prediction_dir/'summary.json').read_text())
    pred=np.load(args.prediction_dir/'signals.npz')
    gt=np.genfromtxt(args.ground_truth,delimiter=',',names=True)
    gt=np.atleast_1d(gt)
    if 'time_s' not in gt.dtype.names:raise ValueError('Ground truth must have time_s')
    times=gt['time_s']+args.gt_offset_s
    if len(times)<2 or not np.isfinite(times).all() or np.any(np.diff(times)<=0):raise ValueError('Invalid ground truth timestamps')
    gap_limit=getattr(args,'max_gt_gap_s',None) or 3*np.median(np.diff(times))
    if gap_limit<=0:raise ValueError('Gap limit must be positive')
    if np.max(np.diff(times))>gap_limit:raise ValueError('Large ground truth gap: define exclusions before evaluation')
    t=pred['time_s'];fs=summary['config']['fps']
    if np.max(np.abs(np.diff(t)-1/fs))>1e-4:raise ValueError('Prediction requires uniform sample times')
    args.output.mkdir(parents=True,exist_ok=True)
    report={'kind':'single_recording_evaluation','synchronization_note':args.sync_note,
            'gt_offset_s':args.gt_offset_s,'gt_gap_limit_s':float(gap_limit),'ground_truth_sha256':hashlib.sha256(args.ground_truth.read_bytes()).hexdigest(),
            'prediction_summary':summary,'signals':{},'generalization_claim':False,'rate_estimator':'common fixed Hann periodogram, no zero padding; recomputed from waveforms'}
    for name,seconds in [('pulse',30),('resp',60)]:
        if name not in gt.dtype.names:
            report['signals'][name]={'status':'no_corresponding_ground_truth'};continue
        if not np.isfinite(gt[name]).all():raise ValueError(f'{name}: missing/nonfinite labels must be explicitly handled')
        band=(getattr(args,'pulse_band_hz',None) or summary['config'][name+'_band_hz']) if name=='pulse' else summary['config'][name+'_band_hz']
        valid=(t>=times[0])&(t<=times[-1])
        common_t=t[valid]
        if len(common_t)<int(seconds*fs):
            report['signals'][name]={'status':'insufficient_common_duration','minimum_window_s':seconds};continue
        # No extrapolation and no learned/optimized time lag.
        truth=np.interp(common_t,times,gt[name])
        estimated=pred[name+'_integrated'][valid]
        b,a=signal.butter(summary['config']['filter_order'],band,btype='bandpass',fs=fs)
        truth=signal.filtfilt(b,a,detrend(truth,summary['config']['detrend_lambda']))
        estimated=signal.filtfilt(b,a,detrend(estimated,summary['config']['detrend_lambda']))
        rows=[]
        for start in range(0,len(common_t)-int(seconds*fs)+1,int(seconds*fs)):
            stop=start+int(seconds*fs);p=estimated[start:stop];g=truth[start:stop]
            if min(np.std(p),np.std(g))<1e-12:
                rows.append({'start_s':float(common_t[start]),'status':'excluded_constant_signal'});continue
            pr,_,_=spectral_rate(p,fs,band);gr,_,_=spectral_rate(g,fs,band)
            rows.append({'start_s':float(common_t[start]),'end_exclusive_s':float(common_t[start]+seconds),
                         'status':'valid','predicted_per_min':pr,'reference_waveform_derived_per_min':gr,
                         'error_per_min':pr-gr,'waveform_pearson_no_lag':float(np.corrcoef(p,g)[0,1])})
        errors=np.array([r['error_per_min'] for r in rows if r['status']=='valid'])
        metrics={'mae_per_min':float(np.mean(abs(errors))),'rmse_per_min':float(np.sqrt(np.mean(errors**2))),
                 'bias_per_min':float(np.mean(errors))} if len(errors) else None
        report['signals'][name]={'status':'evaluated','window_s':seconds,'band_hz':list(band),'valid_windows':len(errors),'windows':rows,'metrics':metrics,
                                 'gt_median_interval_s':float(np.median(np.diff(times))),
                                 'gt_max_interval_s':float(np.max(np.diff(times)))}
        def z(x):return (x-x.mean())/x.std()
        if min(truth.std(),estimated.std())>1e-12:
            fig,ax=plt.subplots(figsize=(11,3));ax.plot(common_t,z(estimated),label='Prediction');ax.plot(common_t,z(truth),alpha=.7,label='Ground truth')
            ax.set(xlabel='Video-relative time (s)',ylabel='Amplitude (z-score)',title=f'{name}: no fitted lag or sign flip');ax.legend();fig.tight_layout();fig.savefig(args.output/f'{name}_comparison.png',dpi=160);plt.close(fig)
    (args.output/'evaluation.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    print(json.dumps(report['signals'],indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prediction-dir',type=Path,required=True)
    p.add_argument('--ground-truth',type=Path,required=True)
    p.add_argument('--gt-offset-s',type=float,required=True)
    p.add_argument('--sync-note',required=True,help='Acquisition-based synchronization evidence, not fitted on predictions')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--max-gt-gap-s',type=float,help='Predeclared maximum reference gap allowed for interpolation; default 3 median intervals')
    p.add_argument('--pulse-band-hz',type=float,nargs=2,help='Optional band fixed before evaluating, for a shared protocol')
    evaluate(p.parse_args())
