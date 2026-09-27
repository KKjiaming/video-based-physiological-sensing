"""Render saved UBFC review arrays without recomputing signals, fitting delay, or changing sign."""
import argparse,json,shutil,subprocess
from datetime import datetime, timezone
import cv2,numpy as np
from signal_utils import ROOT
OUT=ROOT/'results/ubfc_replication_uploaded_v1'
def label(im,s,pos,scale=.55,color=(225,225,225),thick=1):
    cv2.putText(im,s,pos,cv2.FONT_HERSHEY_SIMPLEX,scale,color,thick,cv2.LINE_AA)
def render(subject, replace_existing=False):
    if subject == 'subject3':
        base=ROOT/'results/ubfc_gt_review'
        timing={'crop_xywh':json.loads((ROOT/'configs/ubfc_subject3_protocol.json').read_text())['crop_xywh'], 'dropped_exact_duplicate_gt_indices':[]}
        source=ROOT/'data/ubfc_subject3/input_30hz.avi'
        target=base/'video_with_gt.mp4';metadata_path=base/'video_metadata.json'
        subtitle='Original subject3 analysis | fixed first 30-second window'
        footer='Dataset: UBFC-rPPG | Subject 3'
    else:
        base=OUT/subject;timing=json.loads((base/'timing_audit.json').read_text())
        source=ROOT/f'data/ubfc_{subject}/input_30hz_replication_v1.avi'
        target=base/'video_with_reference.mp4';metadata_path=base/'video_review_metadata.json'
        subtitle='Supplemental exact-duplicate GT cleanup | fixed first 30-second window'
        footer='Original strict GT check failed on duplicate time; this supplemental branch is reported separately.'
    if target.exists() and not replace_existing:raise FileExistsError('Existing video: use --replace-existing to archive and refresh only the presentation')
    caption_bottom=373+cv2.getTextSize('Time (s) | full common-clip z-score; display clipped at +/-3',cv2.FONT_HERSHEY_SIMPLEX,.44,1)[1]
    title_top=430-cv2.getTextSize('BigSmall | full 30s estimate',cv2.FONT_HERSHEY_SIMPLEX,.65,2)[0][1]
    assert title_top-caption_bottom>=24, 'Insufficient spacing between chart panels'
    items=[]
    for model,title,color in [('mtts','MTTS-CAN',(220,130,35)),('bigsmall','BigSmall',(30,130,230))]:
        arrays=dict(np.load(base/f'{model}_display_arrays.npz'))
        evaluation_path=(ROOT/f'results/{model}_ubfc_evaluation/evaluation.json') if subject=='subject3' else (base/(model+'_evaluation')/'evaluation.json')
        ev=json.loads(evaluation_path.read_text())['signals']['pulse']['windows'][0]
        items.append((title,color,arrays,ev))
    cap=cv2.VideoCapture(str(source))
    temporary=base/'video_layout_v3_pending.mp4'
    preview_temp=base/'preview_layout_v3_pending.jpg'
    proc=subprocess.Popen(['ffmpeg','-v','error','-n','-f','rawvideo','-pix_fmt','bgr24','-s','1320x760','-r','30','-i','-','-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(temporary)],stdin=subprocess.PIPE)
    for k in range(900):
        ok,frame=cap.read();assert ok
        now=k/30;canvas=np.full((760,1320,3),(24,20,17),dtype=np.uint8)
        label(canvas,'UBFC '+subject+' | PRETRAINED INFERENCE + CONTACT PPG',(24,36),.77,(255,255,255),2)
        label(canvas,subtitle,(24,69),.62)
        x,y,w,h=timing['crop_xywh'];cv2.rectangle(frame,(x,y),(x+w,y+h),(90,240,130),2);canvas[125:605,0:640]=frame
        label(canvas,f'Video time {now:5.2f} s | Green box: fixed inference ROI',(24,634),.59,(90,240,130))
        label(canvas,'Contact PPG: green | Respiration has no ground truth',(24,670),.55,(90,240,130))
        start=max(0,min(now-5,20));end=start+10
        for i,(title,color,a,ev) in enumerate(items):
            px,py,pw,ph=690,190+i*300,600,140
            label(canvas,title+' | full 30s estimate',(px,py-60),.65,color,2)
            label(canvas,f'HR pred {ev["predicted_per_min"]:.1f} | PPG ref {ev["reference_waveform_derived_per_min"]:.1f} bpm',(px,py-32),.54)
            cv2.rectangle(canvas,(px,py),(px+pw,py+ph),(90,90,90),1)
            for tick in np.arange(start,end+.1,2):
                xx=px+round((tick-start)/10*pw);cv2.line(canvas,(xx,py),(xx,py+ph),(55,50,45),1);label(canvas,f'{tick:.1f}',(xx-10,py+ph+22),.43)
            mask=(a['time_s']>=start)&(a['time_s']<=end)
            for field,col in [('contact_ppg_zscore',(90,210,100)),('prediction_zscore',color)]:
                pts=np.column_stack([px+(a['time_s'][mask]-start)/10*pw,py+ph/2-np.clip(a[field][mask],-3,3)*ph/6]).astype(np.int32)
                cv2.polylines(canvas,[pts],False,col,1,cv2.LINE_AA)
            xx=px+round((now-start)/10*pw);cv2.line(canvas,(xx,py),(xx,py+ph),(255,255,255),2)
            label(canvas,'Time (s) | full common-clip z-score; display clipped at +/-3',(px,py+ph+43),.44)
        label(canvas,'Offline: full-clip filtering and window rates use future frames. No fitted lag or sign flip.',(24,711),.54)
        label(canvas,footer,(24,743),.51)
        if k==450:cv2.imwrite(str(preview_temp),canvas)
        proc.stdin.write(canvas.tobytes())
    cap.release();proc.stdin.close();assert proc.wait()==0
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height,nb_frames,duration,avg_frame_rate','-of','json',str(temporary)]))
    stream=probe['streams'][0];assert int(stream['nb_frames'])==900 and abs(float(stream['duration'])-30)<1e-6
    archive=ROOT/'results/video_layout_archive'/subject/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    archive.mkdir(parents=True,exist_ok=True)
    for old in [target,base/'preview.jpg',metadata_path]:
        if old.exists():
            backup=archive/old.name
            if backup.exists():raise FileExistsError('Archive already exists; refusing to overwrite '+str(backup))
            shutil.copy2(old,backup)
    temporary.replace(target);preview_temp.replace(base/'preview.jpg')
    (metadata_path).write_text(json.dumps({'subject':subject,'stream':stream,'waveforms':'unchanged saved model and contact PPG display arrays; fixed original processing','normalization':'each full common clip z-scored independently, display only; visual amplitude clipped +/-3','no_lag_fit':True,'no_sign_flip':True,'GT_removed_indices':timing['dropped_exact_duplicate_gt_indices'],'layout_version':3,'chart_bounds_xywh':[[690,190,600,140],[690,490,600,140]],'caption_baseline_to_next_title_baseline_px':57,'old_presentation_archive':str(archive.relative_to(ROOT))},indent=2))
    print('Rendered '+subject,flush=True)
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--subjects',nargs='+',choices=['subject1','subject3','subject4','subject5'],default=['subject1','subject4','subject5'])
    parser.add_argument('--replace-existing',action='store_true',help='Archive prior videos/previews and replace only presentation files')
    args=parser.parse_args()
    for subject in args.subjects:render(subject,args.replace_existing)
