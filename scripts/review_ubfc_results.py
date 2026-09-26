"""Visualize a fixed public sample against actual contact PPG. No fitted delay/sign changes."""
from pathlib import Path
import json,hashlib,subprocess
import cv2,numpy as np
from scipy import signal
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from signal_utils import ROOT,detrend

def z(x):return (x-x.mean())/x.std()
def label(im,s,pos,scale=.57,color=(220,225,235),thick=1):cv2.putText(im,s,pos,cv2.FONT_HERSHEY_SIMPLEX,scale,color,thick,cv2.LINE_AA)
def main():
    out=ROOT/'results/ubfc_gt_review';out.mkdir(exist_ok=True)
    gt=np.genfromtxt(ROOT/'data/ubfc_subject3/ground_truth.csv',delimiter=',',names=True)
    items=[];report={'kind':'single_public_sample_contact_ppg_evaluation','selection':'whole uploaded recording; two fixed non-overlapping 30s windows','respiration':'no corresponding ground truth; not evaluated','synchronization':'container PTS for video, original GT timestamps, fixed zero offset; no independently measured clock correction','methods':{}}
    for key,title,color in [('mtts','MTTS-CAN','#2783dc'),('bigsmall','BigSmall','#df831d')]:
        meta=json.loads((ROOT/f'results/{key}_ubfc_subject3/summary.json').read_text());a=dict(np.load(ROOT/f'results/{key}_ubfc_subject3/signals.npz'))
        e=json.loads((ROOT/f'results/{key}_ubfc_evaluation/evaluation.json').read_text());ev=e['signals']['pulse'];assert ev['valid_windows']==2 and e['signals']['resp']['status']=='no_corresponding_ground_truth'
        fs=meta['config']['fps'];t=a['time_s'];truth=np.interp(t,gt['time_s'],gt['pulse'])
        b,c=signal.butter(1,[.75,2.5],btype='bandpass',fs=fs)
        p=signal.filtfilt(b,c,detrend(a['pulse_integrated'],100));g=signal.filtfilt(b,c,detrend(truth,100))
        item={'key':key,'title':title,'color':color,'t':t,'prediction':z(p),'truth':z(g),'evaluation':ev};items.append(item)
        for row in ev['windows']:
            mask=(gt['time_s']>=row['start_s'])&(gt['time_s']<row['end_exclusive_s']);row['device_hr_median_bpm_for_context']=float(np.median(gt['device_hr_bpm'][mask]))
        report['methods'][title]=ev
        report.setdefault('reference_caveat','GT has five gaps over100ms (all under250ms) and same-index timestamps can differ from container time by0.373s. No fitted lag, no discarded windows; waveform correlation has synchronization uncertainty.')
        np.savez_compressed(out/f'{key}_display_arrays.npz',time_s=t,prediction_zscore=item['prediction'],contact_ppg_zscore=item['truth'])
    fig,axes=plt.subplots(3,1,figsize=(12,9))
    for ax,item in zip(axes[:2],items):
        mask=item['t']<10
        ax.plot(item['t'][mask],item['truth'][mask],color='#2e995d',label='Ground truth: contact PPG',lw=1.5)
        ax.plot(item['t'][mask],item['prediction'][mask],color=item['color'],label=item['title']+' prediction',alpha=.85)
        ax.set(xlabel='Time (s)',ylabel='Amplitude (z-score)',title=item['title']+': fixed first 10s; no fitted lag or sign flip');ax.legend(loc='upper right');ax.grid(alpha=.2)
    ax=axes[2]
    for item in items:
        rows=item['evaluation']['windows'];mid=[(r['start_s']+r['end_exclusive_s'])/2 for r in rows]
        ax.plot(mid,[r['predicted_per_min'] for r in rows],'o-',color=item['color'],label=item['title']+' prediction')
        ax.plot(mid,[r['reference_waveform_derived_per_min'] for r in rows],'x--',color='#2e995d' if item['key']=='mtts' else '#687b6e',label='Contact PPG spectral HR ('+item['title']+' grid)')
    rows=items[0]['evaluation']['windows'];ax.plot(mid,[r['device_hr_median_bpm_for_context'] for r in rows],':',color='#555555',label='Device HR median (context only)')
    ax.set(xlabel='Window midpoint (s); each estimate uses 30s',ylabel='Heart rate (beats/min)',title='Both prespecified windows; one recording, not dataset performance');ax.legend(fontsize=8,ncol=2);ax.grid(alpha=.2)
    fig.suptitle('UBFC-rPPG subject3 | Actual contact PPG reference | Respiration unvalidated')
    fig.tight_layout();fig.savefig(out/'gt_comparison.png',dpi=160);plt.close(fig)
    (out/'comparison.json').write_text(json.dumps(report,indent=2))
    # Preserve the unfiltered reference and the independent device rate for inspection.
    fig,axes=plt.subplots(2,1,figsize=(12,5));mask=gt['time_s']<61
    axes[0].plot(gt['time_s'][mask],gt['pulse'][mask],lw=.6);axes[0].set(xlabel='Time (s)',ylabel='Contact PPG (raw units)',title='Unfiltered released contact PPG; no exclusions')
    axes[1].plot(gt['time_s'][mask],gt['device_hr_bpm'][mask]);axes[1].set(xlabel='Time (s)',ylabel='Device heart rate (beats/min)',title='Released device HR; smoothing/latency unspecified')
    fig.tight_layout();fig.savefig(out/'reference_quality.png',dpi=150);plt.close(fig)
    # Thirty-second video review; waveforms are computed offline using the full fixed clip.
    cap=cv2.VideoCapture(str(ROOT/'data/ubfc_subject3/input_30hz.avi'))
    target=out/'video_with_gt.mp4'
    proc=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s','1320x760','-r','30','-i','-','-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],stdin=subprocess.PIPE)
    for k in range(900):
        ok,frame=cap.read()
        if not ok:raise RuntimeError('Missing source frame')
        canvas=np.full((760,1320,3),(24,20,17),dtype=np.uint8);now=k/30
        label(canvas,'PRETRAINED INFERENCE WITH CONTACT PPG REFERENCE',(24,35),.8,(255,255,255),2)
        label(canvas,'UBFC-rPPG subject3 | first 30s video review',(24,67),.64)
        x,y,w,h=[230,20,260,260];cv2.rectangle(frame,(x,y),(x+w,y+h),(90,240,130),2)
        canvas[125:605,0:640]=frame
        label(canvas,f'Video time: {now:5.2f} s | Green box: actual inference ROI',(24,635),.59,(90,240,130))
        label(canvas,'Ground truth: contact PPG (green) | No respiration GT',(24,672),.57,(90,240,130))
        start=max(0,min(now-5,20));end=start+10
        for row,item in enumerate(items):
            px,py,pw,ph=690,190+row*300,600,140
            ev=item['evaluation']['windows'][0];rgb=tuple(int(item['color'][i:i+2],16) for i in (1,3,5));bgr=rgb[::-1]
            label(canvas,item['title']+' | first 30s window',(px,py-60),.65,bgr,2)
            label(canvas,f'HR pred {ev["predicted_per_min"]:.1f} | PPG ref {ev["reference_waveform_derived_per_min"]:.1f} beats/min',(px,py-30),.54)
            cv2.rectangle(canvas,(px,py),(px+pw,py+ph),(90,90,90),1)
            for tick in np.arange(start,end+.1,2):
                xx=px+round((tick-start)/10*pw);cv2.line(canvas,(xx,py),(xx,py+ph),(55,50,45),1);label(canvas,f'{tick:.1f}',(xx-10,py+ph+22),.43)
            for field,col in [('truth',(90,210,100)),('prediction',bgr)]:
                mask=(item['t']>=start)&(item['t']<=end);t=item['t'][mask];v=item[field][mask]
                pts=np.column_stack([px+(t-start)/10*pw,py+ph/2-np.clip(v,-3,3)*ph/6]).astype(np.int32)
                cv2.polylines(canvas,[pts],False,col,1,cv2.LINE_AA)
            xx=px+round((now-start)/10*pw);cv2.line(canvas,(xx,py),(xx,py+ph),(255,255,255),2)
            label(canvas,'Time (s) | amplitude: full-clip z-score',(px,py+ph+43),.47)
        label(canvas,'Offline analysis: traces and window HR use future frames. Fixed zero lag; no sign correction.',(24,711),.56)
        label(canvas,'Data: Bobbia et al., UBFC-rPPG, Pattern Recognition Letters. Local research visualization.',(24,743),.52)
        if k==450:cv2.imwrite(str(out/'preview.jpg'),canvas)
        proc.stdin.write(canvas.tobytes())
    cap.release();proc.stdin.close();assert proc.wait()==0
    (out/'video_metadata.json').write_text(json.dumps({'frames':900,'fps':30,'duration_s':30,'signals':'real saved model predictions and contact PPG; same fixed processing as evaluation','normalization':'full fixed clip z-score independently, display only','rate_labels':'first fixed 30s window, not instantaneous/live','script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2))
    print(json.dumps({k:v['metrics'] for k,v in report['methods'].items()},indent=2))
if __name__=='__main__':main()
