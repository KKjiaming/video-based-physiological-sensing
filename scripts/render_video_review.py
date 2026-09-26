"""Render saved predictions alongside their actual input video; never invent GT or heatmaps."""
from pathlib import Path
import json,subprocess,hashlib
import cv2
import numpy as np
ROOT=Path(__file__).resolve().parents[1]

def text(im,s,xy,scale=.58,color=(215,220,230),thickness=1):
    cv2.putText(im,s,xy,cv2.FONT_HERSHEY_SIMPLEX,scale,color,thickness,cv2.LINE_AA)

def main():
    out=ROOT/'results/mit_video_review';out.mkdir(exist_ok=True)
    runs=[]
    for key,label,color in [('mtts','MTTS-CAN',(245,165,60)),('bigsmall','BigSmall',(65,175,245))]:
        p=ROOT/f'results/{key}_mit_face_demo';meta=json.loads((p/'summary.json').read_text());a=dict(np.load(p/'signals.npz'))
        runs.append((label,color,meta,a))
    video=ROOT/runs[0][2]['config']['video'];cap=cv2.VideoCapture(str(video));fps=cap.get(cv2.CAP_PROP_FPS)
    assert fps==30 and int(cap.get(cv2.CAP_PROP_FRAME_COUNT))==301
    base=np.full((760,1320,3),(24,20,17),dtype=np.uint8)
    text(base,'OFFLINE PRETRAINED INFERENCE | NO GROUND TRUTH',(24,35),.8,(255,255,255),2)
    text(base,'MIT source video + actual ROI',(24,68),.62)
    text(base,'Full-clip spectral predictions (NOT instantaneous measurements)',(570,72),.6)
    for j,(label,color,meta,a) in enumerate(runs):
        text(base,f'{label}: HR {meta["pulse_rate_per_min"]:.1f}/min | RR {meta["resp_rate_per_min"]:.1f}/min',(570,104+j*28),.62,color,2)
    polys=[]
    for row,name in enumerate(['pulse','resp']):
        x0,y0,w,h=580,190+row*235,705,155
        text(base,('Pulse' if name=='pulse' else 'Respiration')+' prediction | amplitude: z-score',(x0,y0-18),.6)
        cv2.rectangle(base,(x0,y0),(x0+w,y0+h),(100,95,90),1)
        for tick in range(0,11,2):
            xx=x0+round(tick/10*w);cv2.line(base,(xx,y0),(xx,y0+h),(55,50,45),1)
            text(base,str(tick),(xx-7,y0+h+22),.45)
        text(base,'Time (s)',(x0+w-90,y0+h+43),.5)
        for label,color,meta,a in runs:
            z=a[name+'_filtered'];z=(z-z.mean())/z.std()
            pts=np.column_stack([x0+np.clip(a['time_s']/10,0,1)*w,y0+h/2-np.clip(z,-3,3)*(h/6)]).astype(np.int32)
            cv2.polylines(base,[pts],False,color,1,cv2.LINE_AA)
        polys.append((x0,y0,w,h))
    text(base,'10-second clip: RR is exploratory. Different model protocols; no accuracy ranking.',(24,713),.6,(160,190,245))
    text(base,'Video: Wu et al., Eulerian Video Magnification, SIGGRAPH 2012 | Models: Liu et al.; Narayanswamy et al.',(24,744),.5)
    target=out/'video_with_predictions.mp4'
    ff=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s','1320x760','-r','30','-i','-','-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],stdin=subprocess.PIPE)
    count=0;x,y,w,h=runs[0][2]['config']['crop_xywh']
    while True:
        ok,frame=cap.read()
        if not ok:break
        im=base.copy();display=cv2.resize(frame,(500,561));im[98:659,24:524]=display
        sx=500/frame.shape[1];sy=561/frame.shape[0]
        cv2.rectangle(im,(24+round(x*sx),98+round(y*sy)),(24+round((x+w)*sx),98+round((y+h)*sy)),(90,240,130),2)
        t=count/fps;text(im,f'Video time: {t:5.2f} s',(24,687),.6,(90,240,130))
        for x0,y0,pw,ph in polys:
            xx=x0+round(min(t,10)/10*pw);cv2.line(im,(xx,y0),(xx,y0+ph),(250,250,250),2)
        if count==150:cv2.imwrite(str(out/'preview.png'),im)
        ff.stdin.write(im.tobytes());count+=1
    cap.release();ff.stdin.close()
    if ff.wait()!=0:raise RuntimeError('ffmpeg failed')
    report={'kind':'offline_video_overlay_without_ground_truth','source_video':str(video.relative_to(ROOT)),'source_video_sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'output_frames':count,'fps':fps,'duration_s':count/fps,'plot_time_axis':'model output time relative to source video start','rates':'Full-clip spectral peaks from original saved results, not live estimates','amplitudes':'Each full-clip filtered waveform z-scored separately for display only; no signal timing, sign or rate adjustments','roi':'Actual fixed inference crop shown in green','privacy':'Author-provided public source video, local derived artifact only','script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (out/'summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
