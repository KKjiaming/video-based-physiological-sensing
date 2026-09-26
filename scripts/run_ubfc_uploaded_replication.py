"""Frozen supplemental exact-duplicate branch; original subject3/strict results untouched."""
from pathlib import Path
import hashlib,json,subprocess,sys
import cv2,numpy as np
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/ubfc_replication_uploaded_v1'
PYTHON=ROOT/'.venv/bin/python'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def prepare(item):
    s=item['subject'];out=OUT/s;out.mkdir(exist_ok=True)
    video=ROOT/item['video'];assert sha(video)==item['video_sha256']
    raw=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_frames','-show_entries','frame=best_effort_timestamp_time','-of','json',str(video)]))
    pts=np.array([float(f['best_effort_timestamp_time']) for f in raw['frames']]);pts-=pts[0]
    gt=np.loadtxt(ROOT/item['source_gt']);assert gt.shape==(3,len(pts)) and np.isfinite(gt).all() and np.all(np.diff(pts)>0)
    drops=[]
    for i in range(1,gt.shape[1]):
        assert gt[2,i]>=gt[2,i-1],'Reversed GT clock'
        if gt[2,i]==gt[2,i-1]:
            assert np.array_equal(gt[:,i],gt[:,i-1]),'Duplicate time with different labels'
            drops.append(i)
    kept=np.delete(np.arange(gt.shape[1]),drops);clean=gt[:,kept];assert np.all(np.diff(clean[2])>0) and np.max(np.diff(clean[2]))<=.25
    gtpath=out/'ground_truth_exact_duplicates_only.csv'
    np.savetxt(gtpath,np.column_stack([clean[2],clean[0],clean[1]]),delimiter=',',header='time_s,pulse,device_hr_bpm',comments='')
    np.savetxt(out/'gt_source_index_mapping.csv',np.column_stack([np.arange(len(kept)),kept,clean[2]]),delimiter=',',header='clean_index,original_gt_index,time_s',comments='',fmt='%.17g')
    target=np.arange(int(np.floor(pts[-1]*30))+1)/30
    right=np.searchsorted(pts,target).clip(0,len(pts)-1);left=np.maximum(right-1,0)
    idx=np.where(abs(pts[right]-target)<abs(pts[left]-target),right,left)
    dest=ROOT/f'data/ubfc_{s}/input_30hz_replication_v1.avi'
    assert not dest.exists(),'Refuse to overwrite prepared input'
    cap=cv2.VideoCapture(str(video));width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT));fps=cap.get(cv2.CAP_PROP_FPS)
    writer=subprocess.Popen(['ffmpeg','-v','error','-n','-f','rawvideo','-pix_fmt','bgr24','-s',f'{width}x{height}','-r','30','-i','-','-an','-c:v','ffv1','-pix_fmt','bgr0',str(dest)],stdin=subprocess.PIPE)
    j=0;sampled={};tiles=[];checks=[k for k in [0,450,900,1350] if k<len(target)]
    for i in range(len(pts)):
        ok,frame=cap.read();assert ok
        while j<len(idx) and idx[j]==i:
            writer.stdin.write(frame.tobytes())
            if j in checks:
                sampled[j]=frame.copy();im=frame.copy();x,y,w,h=item['crop_xywh'];cv2.rectangle(im,(x,y),(x+w,y+h),(0,255,0),2);cv2.putText(im,f'{s} {j/30:.0f}s',(5,28),cv2.FONT_HERSHEY_SIMPLEX,.7,(0,255,0),2);tiles.append(cv2.resize(im,(320,240)))
            j+=1
    assert j==len(target) and not cap.read()[0];cap.release();writer.stdin.close();assert writer.wait()==0
    cap=cv2.VideoCapture(str(dest))
    for k,expected in sampled.items():
        cap.set(cv2.CAP_PROP_POS_FRAMES,k);ok,im=cap.read();assert ok and np.array_equal(im,expected)
    cap.release();cv2.imwrite(str(out/'crop_contact_sheet.jpg'),cv2.hconcat(tiles))
    np.savetxt(out/'resampling.csv',np.column_stack([target,idx,pts[idx]]),delimiter=',',header='target_time_s,source_frame_index,source_pts_s',comments='')
    np.savetxt(out/'source_timing.csv',np.column_stack([np.arange(len(pts)),pts,gt[2]]),delimiter=',',header='index,container_pts_s,original_gt_timestamp_s',comments='')
    record={'subject':s,'branch':'supplemental_exact_duplicate_cleanup','original_strict_quality':'failed_non_strictly_increasing_GT','original_frames':len(pts),'original_gt_samples':gt.shape[1],'gt_kept_samples':len(kept),'dropped_exact_duplicate_gt_indices':drops,'video_frames_removed_for_GT_cleanup':0,'container_fps':fps,'video_last_pts_s':float(pts[-1]),'gt_last_s':float(gt[2,-1]),'clean_GT_average_fs_hz':float((len(kept)-1)/(clean[2,-1]-clean[2,0])),'max_clean_gt_gap_s':float(np.diff(clean[2]).max()),'same_index_GT_minus_PTS_min_median_max_s':[float((gt[2]-pts).min()),float(np.median(gt[2]-pts)),float((gt[2]-pts).max())],'max_resampling_error_s':float(abs(pts[idx]-target).max()),'target_frames':len(target),'lossless_pixel_checks':checks,'second_window_status':'incomplete_reference_and_video_duration' if min(pts[-1],gt[2,-1])<60 else 'pending','crop_xywh':item['crop_xywh'],'files':{str(p.relative_to(ROOT)):sha(p) for p in [video,ROOT/item['source_gt'],dest,gtpath]}}
    (out/'timing_audit.json').write_text(json.dumps(record,indent=2))
    confdir=ROOT/'configs/ubfc_replication_uploaded_v1';confdir.mkdir(exist_ok=True)
    configs={}
    for model in ['mtts','bigsmall']:
        cfg=json.loads((ROOT/f'configs/{model}_ubfc_subject3.json').read_text())
        cfg.update(experiment=f'{model}_ubfc_uploaded_{s}',video=str(dest.relative_to(ROOT)),output_dir=str((out/model).relative_to(ROOT)),crop_xywh=item['crop_xywh'],ground_truth=str(gtpath.relative_to(ROOT)),display_name=f'UBFC {s} supplemental exact-duplicate branch')
        conf=confdir/f'{model}_{s}.json';assert not conf.exists();conf.write_text(json.dumps(cfg,indent=2));configs[model]=conf
    print('PREPARED '+s+' '+json.dumps(record),flush=True)
    return out,gtpath,configs

def run_logged(args,log):
    with log.open('w') as f:subprocess.run([str(x) for x in args],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)

def main():
    lock=json.loads((OUT/'protocol_lock.json').read_text());assert sha(ROOT/lock['file'])==lock['sha256']
    cfg=json.loads((ROOT/lock['file']).read_text());assert sha(ROOT/cfg['parent_protocol'])==cfg['parent_sha256']
    for item in cfg['subjects']:
        s=item['subject'];out,gtpath,configs=prepare(item)
        for model in ['mtts','bigsmall']:
            print('INFERENCE '+s+' '+model,flush=True)
            run_logged([PYTHON,ROOT/f'scripts/infer_{model}.py','--config',configs[model]],out/f'{model}_inference.log')
            print('EVALUATION supplemental '+s+' '+model,flush=True)
            run_logged([PYTHON,ROOT/'scripts/evaluate_signals.py','--prediction-dir',out/model,'--ground-truth',gtpath,'--gt-offset-s','0','--sync-note','Supplemental exact-identical GT duplicate removal with original index mapping; source video PTS and original GT seconds, fixed zero offset; hardware synchrony unverified; no fitted delay or sign correction.','--pulse-band-hz','.75','2.5','--max-gt-gap-s','.25','--output',out/(model+'_evaluation')],out/f'{model}_evaluation.log')
        print('COMPLETED '+s,flush=True)
    print('ALL THREE SUBJECTS COMPLETED',flush=True)
if __name__=='__main__':main()
