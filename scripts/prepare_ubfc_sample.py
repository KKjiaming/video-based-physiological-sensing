"""Validate uploaded UBFC subject3 and resample using original container PTS, without fitting GT."""
from pathlib import Path
import json,hashlib,subprocess
import cv2,numpy as np
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def main():
    cfg=json.loads((ROOT/'configs/ubfc_subject3_protocol.json').read_text());out=ROOT/'results/ubfc_audit';out.mkdir(exist_ok=True)
    video=ROOT/cfg['source_video'];assert video.stat().st_size==cfg['expected_video_bytes']
    raw=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_frames','-show_entries','frame=best_effort_timestamp_time','-of','json',str(video)]))
    pts=np.array([float(f['best_effort_timestamp_time']) for f in raw['frames']]);pts-=pts[0]
    gt=np.loadtxt(ROOT/cfg['source_gt']);assert gt.shape==(3,len(pts)) and len(pts)==cfg['expected_frames'];assert np.isfinite(gt).all()
    dt=np.diff(gt[2]);assert np.all(dt>0) and dt.max()<=cfg['max_gt_gap_s']
    target=np.arange(int(np.floor(pts[-1]*30))+1)/30
    right=np.searchsorted(pts,target).clip(0,len(pts)-1);left=np.maximum(right-1,0)
    idx=np.where(abs(pts[right]-target)<abs(pts[left]-target),right,left)
    dest=ROOT/'data/ubfc_subject3/input_30hz.avi'
    writer=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s','640x480','-r','30','-i','-','-an','-c:v','ffv1','-pix_fmt','bgr0',str(dest)],stdin=subprocess.PIPE)
    cap=cv2.VideoCapture(str(video));j=0;tiles=[];sampled={}
    for i in range(len(pts)):
        ok,frame=cap.read();assert ok
        while j<len(idx) and idx[j]==i:
            writer.stdin.write(frame.tobytes())
            if j in [0,450,900,1350,1800]:
                sampled[j]=frame.copy();im=frame.copy();x,y,w,h=cfg['crop_xywh'];cv2.rectangle(im,(x,y),(x+w,y+h),(0,255,0),2);im=cv2.resize(im,(320,240));cv2.putText(im,f'{j/30:.0f}s',(5,25),cv2.FONT_HERSHEY_SIMPLEX,.6,(0,255,0),1);tiles.append(im)
            j+=1
    assert j==len(target);assert not cap.read()[0];cap.release();writer.stdin.close();assert writer.wait()==0
    cap=cv2.VideoCapture(str(dest));pixel_checks=[]
    for k,expected in sampled.items():
        cap.set(cv2.CAP_PROP_POS_FRAMES,k);ok,im=cap.read();assert ok and np.array_equal(im,expected);pixel_checks.append({'target_frame':k,'source_frame':int(idx[k]),'max_pixel_error':0})
    cap.release();cv2.imwrite(str(ROOT/'data/ubfc_subject3/crop_check.jpg'),np.concatenate(tiles,axis=1))
    np.savetxt(ROOT/'data/ubfc_subject3/ground_truth.csv',np.column_stack([gt[2],gt[0],gt[1]]),delimiter=',',header='time_s,pulse,device_hr_bpm',comments='')
    np.savetxt(out/'resampling.csv',np.column_stack([target,idx,pts[idx]]),delimiter=',',header='target_time_s,source_frame_index,source_pts_s',comments='')
    np.savetxt(out/'source_timing.csv',np.column_stack([np.arange(len(pts)),pts,gt[2]]),delimiter=',',header='index,container_pts_s,gt_timestamp_s',comments='')
    gaps=[{'after_index':int(i),'start_s':float(gt[2,i]),'duration_s':float(dt[i])} for i in np.flatnonzero(dt>.1)]
    record={'kind':'uploaded_sample_and_timing_audit','frames':len(pts),'target_frames':len(target),'gt_shape':gt.shape,'container_duration_to_last_frame_s':float(pts[-1]),'gt_duration_to_last_sample_s':float(gt[2,-1]),'max_abs_same_index_clock_difference_s':float(np.max(abs(gt[2]-pts))),'max_resampling_error_s':float(np.max(abs(pts[idx]-target))),'gt_gaps_over100ms':gaps,'gt_gap_interpolation_limit_s':cfg['max_gt_gap_s'],'gt_alignment':cfg['gt_timing'],'limitations':cfg['gt_limit'],'lossless_pixel_checks':pixel_checks,'files':{p:sha(ROOT/p) for p in [cfg['source_video'],cfg['source_gt'],'data/ubfc_subject3/input_30hz.avi','data/ubfc_subject3/ground_truth.csv']}}
    (out/'timing_check.json').write_text(json.dumps(record,indent=2))
    for key,base in [('mtts','mit_face.json'),('bigsmall','bigsmall_mit_face.json')]:
        conf=json.loads((ROOT/'configs'/base).read_text());conf.update(experiment=f'{key}_ubfc_subject3',video='data/ubfc_subject3/input_30hz.avi',output_dir=f'results/{key}_ubfc_subject3',crop_xywh=cfg['crop_xywh'],ground_truth='data/ubfc_subject3/ground_truth.csv',display_name='UBFC-rPPG subject3')
        (ROOT/f'configs/{key}_ubfc_subject3.json').write_text(json.dumps(conf,indent=2))
    print(json.dumps(record,indent=2))
if __name__=='__main__':main()
