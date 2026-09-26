"""Pretrained inference; preserves raw outputs, PTS, preprocessing and spectra."""
from audit_mtts import ROOT, build_model
import argparse
from pathlib import Path
import hashlib
import json
import subprocess
import time
import importlib.metadata
import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from signal_utils import postprocess, spectral_rate

def run(config):
    cfg=json.loads(config.read_text())
    if cfg['spectrum_window']!='hann':raise ValueError('This protocol supports only the fixed Hann spectrum window')
    out=ROOT/cfg['output_dir'];out.mkdir(parents=True,exist_ok=True)
    video=ROOT/cfg['video']
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_frames','-show_entries','frame=best_effort_timestamp_time','-of','json',str(video)]))
    pts=np.array([float(x['best_effort_timestamp_time']) for x in probe['frames']])
    if len(pts)<2 or np.any(np.diff(pts)<=0):raise ValueError('Missing/nonmonotonic video PTS')
    fs=cfg['fps']
    if np.max(np.abs(np.diff(pts)-1/fs))>1e-4:
        raise ValueError('Nonuniform/unexpected FPS; explicit resampling protocol is required')
    cap=cv2.VideoCapture(str(video)); frames=[]
    x,y,w,h=cfg['crop_xywh']
    while True:
        ok,frame=cap.read()
        if not ok:break
        if x<0 or y<0 or x+w>frame.shape[1] or y+h>frame.shape[0]:raise ValueError('Crop outside image')
        small=cv2.resize(frame[y:y+h,x:x+w].astype('float64')/255,(36,36),interpolation=cv2.INTER_AREA)
        if cfg['rotate_clockwise']:small=cv2.rotate(small,cv2.ROTATE_90_CLOCKWISE)
        small=cv2.cvtColor(small.astype('float32'),cv2.COLOR_BGR2RGB)
        frames.append(np.clip(small,1/255,1))
    cap.release()
    raw_frames=np.asarray(frames,dtype=np.float32)
    if len(raw_frames)!=len(pts):raise ValueError('Frame decode count differs from PTS count')
    # Match upstream's normalization and its zero final difference slot exactly.
    motion=np.zeros_like(raw_frames[:-1])
    motion[:-1]=(raw_frames[1:-1]-raw_frames[:-2])/(raw_frames[1:-1]+raw_frames[:-2])
    if motion.std()==0 or raw_frames.std()==0:raise ValueError('Degenerate video')
    normalization={'motion_std_before_scaling':float(motion.std()),'appearance_mean_before_scaling':float(raw_frames.mean()),'appearance_std_before_scaling':float(raw_frames.std())}
    motion/=motion.std()
    appearance=((raw_frames-raw_frames.mean())/raw_frames.std())[:-1]
    n=len(motion)//cfg['frame_depth']*cfg['frame_depth']
    if cfg['batch_size']%cfg['frame_depth']:raise ValueError('Batch size must be multiple of temporal depth')
    model=build_model();model.load_weights(str(ROOT/cfg['weights']))
    import h5py
    with h5py.File(ROOT/cfg['weights']) as checkpoint:
        group=checkpoint['model_weights']
        for layer in model.layers:
            if not layer.weights:continue
            stored=[group[layer.name][name][()] for name in group[layer.name].attrs['weight_names']]
            if len(stored)!=len(layer.weights) or not all(np.array_equal(a,b) for a,b in zip(layer.get_weights(),stored)):
                raise ValueError('Named weight mapping mismatch: '+layer.name)
    start=time.perf_counter()
    batches=[model([motion[k:min(k+cfg['batch_size'],n)],appearance[k:min(k+cfg['batch_size'],n)]],training=False) for k in range(0,n,cfg['batch_size'])]
    predictions=[np.concatenate([batch[j].numpy() for batch in batches]) for j in range(2)]
    elapsed=time.perf_counter()-start
    if len(predictions)!=2:raise ValueError('Expected verified dual outputs')
    t=pts[:n]-pts[0]
    arrays={'time_s':t,'source_pts_s':pts,'pulse_raw_difference':predictions[0].ravel(),'resp_raw_difference':predictions[1].ravel()}
    meta={'kind':'real_video_inference_with_pulse_ground_truth_available' if cfg.get('ground_truth') else 'real_video_inference_demo_without_ground_truth','model_execution':'official model with public Keras import compatibility, sequential eager batches, training=False','config':cfg,
          'video_sha256':hashlib.sha256(video.read_bytes()).hexdigest(),
          'weight_sha256':hashlib.sha256((ROOT/cfg['weights']).read_bytes()).hexdigest(),
          'model_commit':subprocess.check_output(['git','-C',str(ROOT/'third_party/MTTS-CAN'),'rev-parse','HEAD'],text=True).strip(),
          'normalization':normalization,
          'max_frame_interval_error_s':float(np.max(np.abs(np.diff(pts)-1/fs))),
          'runtime_versions':{p:importlib.metadata.version(p) for p in ['tensorflow-cpu','numpy','scipy','opencv-python-headless']},
          'script_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'scripts/audit_mtts.py',ROOT/'scripts/signal_utils.py']},
          'decoded_frames':len(pts),'predicted_frames':n,'spectral_duration_s':n/fs,
          'prediction_time_s':elapsed,'frequency_bin_width_hz':fs/n,'rate_bin_width_per_min':60*fs/n,
          'gt_available':bool(cfg.get('ground_truth')),'gt_signals':['pulse'] if cfg.get('ground_truth') else [],'accuracy_metrics':None,
          'rr_minimum_duration_met':n/fs>=cfg['minimum_rr_duration_s'],
          'warnings':(['Pulse reference available; accuracy is computed separately. No respiration truth.'] if cfg.get('ground_truth') else ['No ground truth: rates are predictions, not validated measurements.']) + (['Short recording: respiration rate is exploratory and strongly affected by boundaries.'] if n/fs<cfg['minimum_rr_duration_s'] else []) + ['Upstream final difference slot is zero; retained for preprocessing fidelity.', 'Explicit square face ROI and no rotation replace upstream orientation-specific crop.']}
    fig,axes=plt.subplots(2,2,figsize=(12,6))
    for row,name in enumerate(['pulse','resp']):
        a,d,f=postprocess(arrays[name+'_raw_difference'],fs,cfg[name+'_band_hz'],cfg['detrend_lambda'],cfg['filter_order'])
        if not np.isfinite(f).all():raise ValueError('Nonfinite model signal')
        arrays.update({name+'_integrated':a,name+'_detrended':d,name+'_filtered':f})
        rate,hz,power=spectral_rate(f,fs,cfg[name+'_band_hz'])
        arrays.update({name+'_frequency_hz':hz,name+'_power':power})
        meta[name+'_rate_per_min']=rate
        axes[row,0].plot(t,f,label='Prediction (reference evaluated separately)' if name=='pulse' and cfg.get('ground_truth') else 'Prediction (no ground truth)')
        axes[row,0].set(xlabel='Time (s)',ylabel='Amplitude (arbitrary units)',title=name.capitalize()+' prediction')
        axes[row,0].legend()
        axes[row,1].plot(hz,power,label='Prediction spectrum')
        axes[row,1].axvline(rate/60,color='r',ls='--',label=f'{rate:.1f} /min (exploratory)' if name=='resp' else f'{rate:.1f} beats/min')
        axes[row,1].set(xlabel='Frequency (Hz)',ylabel='PSD (a.u.^2/Hz)',xlim=(0,3 if name=='pulse' else .8))
        axes[row,1].legend()
    fig.suptitle('MTTS-CAN pretrained inference | '+cfg.get('display_name','MIT face')+' | Prediction only')
    fig.tight_layout();fig.savefig(out/'predictions.png',dpi=160);plt.close(fig)
    np.savez_compressed(out/'signals.npz',**arrays)
    np.savetxt(out/'signals.csv',np.column_stack([t,arrays['pulse_raw_difference'],arrays['resp_raw_difference'],arrays['pulse_filtered'],arrays['resp_filtered']]),delimiter=',',header='time_s,pulse_raw_difference,resp_raw_difference,pulse_filtered_au,resp_filtered_au',comments='')
    np.savetxt(out/'source_pts.csv',pts,delimiter=',',header='source_pts_s',comments='')
    # QC image is private input-derived data and is kept in ignored data/.
    cv2.imwrite(str(ROOT/('data/'+cfg['experiment']+'_model_input.png')),cv2.cvtColor((raw_frames[0]*255).astype('uint8'),cv2.COLOR_RGB2BGR))
    (out/'summary.json').write_text(json.dumps(meta,indent=2))
    (out/'config.json').write_text(json.dumps(cfg,indent=2))
    print(json.dumps(meta,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,default=ROOT/'configs/mit_face.json')
    run(p.parse_args().config)
