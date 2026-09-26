"""Separate BigSmall demonstration using its published 25-Hz input convention."""
import ast
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import signal
from signal_utils import ROOT,postprocess

def official_normalizers():
    path=ROOT/'third_party/rPPG-Toolbox/dataset/data_loader/BaseLoader.py'
    tree=ast.parse(path.read_text())
    base=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='BaseLoader')
    funcs=[x for x in base.body if isinstance(x,ast.FunctionDef) and x.name in ['standardized_data','diff_normalize_data']]
    for f in funcs:f.decorator_list=[]
    ns={'np':np};exec(compile(ast.Module(body=funcs,type_ignores=[]),str(path),'exec'),ns)
    return ns

def main(config):
    cfg=json.loads(config.read_text())
    assert (cfg['big_size'],cfg['small_size'],cfg['frame_depth'],cfg['batch_size'])==(144,9,3,30)
    assert cfg['spectrum_window']=='boxcar' and cfg['fft_length']=='next_power_of_2'
    out=ROOT/cfg['output_dir'];out.mkdir(parents=True,exist_ok=True)
    video=ROOT/cfg['video'];fs=cfg['fps']
    raw_probe=subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_frames','-show_entries','frame=best_effort_timestamp_time','-of','json',str(video)])
    pts=np.array([float(x['best_effort_timestamp_time']) for x in json.loads(raw_probe)['frames']]);pts-=pts[0]
    if np.any(np.diff(pts)<=0):raise ValueError('Nonmonotonic PTS')
    grid=np.arange(int(np.floor(pts[-1]*fs))+1)/fs
    right=np.searchsorted(pts,grid).clip(0,len(pts)-1);left=(right-1).clip(0,len(pts)-1)
    index=np.where(abs(pts[right]-grid)<abs(pts[left]-grid),right,left)
    if np.max(abs(pts[index]-grid))>1/30:raise ValueError('Source gap exceeds resampling tolerance')
    cap=cv2.VideoCapture(str(video));frames=[];x,y,w,h=cfg['crop_xywh']
    while True:
        ok,im=cap.read()
        if not ok:break
        if x<0 or y<0 or x+w>im.shape[1] or y+h>im.shape[0]:raise ValueError('Invalid crop')
        im=cv2.cvtColor(im,cv2.COLOR_BGR2RGB)
        frames.append(cv2.resize(im[y:y+h,x:x+w],(144,144),interpolation=cv2.INTER_AREA))
    cap.release()
    if len(frames)!=len(pts):raise ValueError('Decode/PTS mismatch')
    raw=np.asarray(frames)[index].astype(np.float64)
    funcs=official_normalizers()
    big=funcs['standardized_data'](raw.copy())
    # Official ordering: normalize differences at 144x144, THEN shrink to 9x9.
    difference=funcs['diff_normalize_data'](raw.copy())
    small=np.asarray([cv2.resize(f,(9,9),interpolation=cv2.INTER_AREA) for f in difference])
    n=len(grid)//3*3
    inputs=ROOT/('data/'+cfg['experiment']+'_inputs.npz')
    np.savez_compressed(inputs,big=big[:n].transpose(0,3,1,2).astype('float32'),small=small[:n].transpose(0,3,1,2).astype('float32'))
    subprocess.run([str(ROOT/'.venv-bigsmall/bin/python'),str(ROOT/'scripts/run_bigsmall_model.py'),'--inputs',str(inputs),'--output',str(out/'raw_outputs.npz')],check=True)
    arrays=dict(np.load(out/'raw_outputs.npz'))
    arrays.update(time_s=grid[:n],source_pts_s=pts,resample_grid_s=grid,resample_source_index=index,resample_source_pts_s=pts[index])
    summary={'kind':'real_video_inference_with_pulse_ground_truth_available' if cfg.get('ground_truth') else 'real_video_inference_demo_without_ground_truth','config':cfg,
             'runtime':json.loads((out/'raw_outputs.json').read_text()),
             'model_commit':subprocess.check_output(['git','-C',str(ROOT/'third_party/rPPG-Toolbox'),'rev-parse','HEAD'],text=True).strip(),
             'video_sha256':hashlib.sha256(video.read_bytes()).hexdigest(),
             'decoded_frames':len(pts),'resampled_frames':len(grid),'predicted_frames':n,
             'spectral_duration_s':n/fs,'max_resample_timing_error_s':float(np.max(abs(pts[index]-grid))),
             'gt_available':bool(cfg.get('ground_truth')),'gt_signals':['pulse'] if cfg.get('ground_truth') else [],'accuracy_metrics':None,
             'notes':['AU logits retained only as uninterpreted model output; no psychological inference.',
                      '25-Hz resampling and Toolbox frequency protocol differ from the MTTS-CAN demo; no ranking.',
                      'Respiration has no ground truth; predictions are unvalidated.']}
    fig,axes=plt.subplots(2,2,figsize=(12,6))
    for row,name in enumerate(['pulse','resp']):
        a,d,f=postprocess(arrays[name+'_raw_difference'],fs,cfg[name+'_band_hz'],cfg['detrend_lambda'],cfg['filter_order'])
        arrays.update({name+'_integrated':a,name+'_detrended':d,name+'_filtered':f})
        nfft=1<<(n-1).bit_length()
        hz,power=signal.periodogram(f,fs=fs,nfft=nfft,detrend=False)
        band=cfg[name+'_band_hz'];mask=(hz>=band[0])&(hz<=band[1]);k=np.flatnonzero(mask)[np.argmax(power[mask])]
        rate=float(hz[k]*60);summary[name+'_rate_per_min']=rate
        summary['fft_length']=nfft;summary['fft_grid_spacing_hz']=fs/nfft;summary['record_resolution_hz']=fs/n
        arrays.update({name+'_frequency_hz':hz,name+'_power':power})
        axes[row,0].plot(grid[:n],f,label='Prediction (reference evaluated separately)' if name=='pulse' and cfg.get('ground_truth') else 'Prediction (no ground truth)');axes[row,0].legend()
        axes[row,0].set(xlabel='Time (s)',ylabel='Amplitude (arbitrary units)',title=name.capitalize()+' prediction')
        axes[row,1].plot(hz,power,label='Prediction spectrum');axes[row,1].axvline(hz[k],color='r',ls='--',label=f'{rate:.1f} /min (exploratory)');axes[row,1].legend()
        axes[row,1].set(xlabel='Frequency (Hz)',ylabel='PSD (a.u.^2/Hz)',xlim=(0,4 if name=='pulse' else .8))
    fig.suptitle('BigSmall Fold 1 pretrained inference | '+cfg.get('display_name','MIT face')+' | Prediction only')
    fig.tight_layout();fig.savefig(out/'predictions.png',dpi=160);plt.close(fig)
    np.savez_compressed(out/'signals.npz',**arrays)
    np.savetxt(out/'signals.csv',np.column_stack([grid[:n],arrays['pulse_raw_difference'],arrays['resp_raw_difference'],arrays['pulse_filtered'],arrays['resp_filtered']]),delimiter=',',header='time_s,pulse_raw_difference,resp_raw_difference,pulse_filtered_au,resp_filtered_au',comments='')
    np.savetxt(out/'resampling.csv',np.column_stack([grid,index,pts[index]]),delimiter=',',header='target_time_s,source_frame_index,source_pts_s',comments='')
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    (out/'config.json').write_text(json.dumps(cfg,indent=2));print(json.dumps(summary,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,default=ROOT/'configs/bigsmall_mit_face.json')
    main(p.parse_args().config)
