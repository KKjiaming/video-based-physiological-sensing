"""Validate author sample pairing and prepare a fixed opening clip, without consulting predictions."""
from pathlib import Path
import json,hashlib,subprocess
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def main():
    cfg=json.loads((ROOT/'configs/mpu_sample_protocol.json').read_text())
    meta=json.loads((ROOT/'results/gt_search/mpu_metadata.json').read_text())
    for id,path in [(cfg['video_file_id'],cfg['source_video']),(cfg['ppg_file_id'],cfg['source_csv'])]:
        f=next(f for f in meta['files'] if f['id']==id);p=ROOT/path
        assert p.stat().st_size==f['size'] and hashlib.md5(p.read_bytes()).hexdigest()==f['computed_md5']
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_frames','-show_entries','frame=best_effort_timestamp_time','-of','json',str(ROOT/cfg['source_video'])]))
    pts=np.array([float(f['best_effort_timestamp_time']) for f in probe['frames']])
    gt=np.genfromtxt(ROOT/cfg['source_csv'],delimiter=',',names=True)
    assert len(gt)==len(pts)==cfg['source_frames'] and np.array_equal(gt['Count'],np.arange(len(pts)))
    assert np.max(abs(pts-gt['Count']/60))<1e-5
    np.savetxt(ROOT/'data/mpu_sample/ground_truth.csv',np.column_stack([gt['Count']/60,gt['PPG'],gt['HR']]),delimiter=',',header='time_s,pulse,device_hr_bpm',comments='')
    # Lossless RGB storage at 30 Hz; source frames 0,2,4,..., no synthetic interpolation.
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(ROOT/cfg['source_video']),'-vf',"select='not(mod(n,2))',setpts=N/(30*TB)",'-frames:v',str(cfg['clip_duration_s']*30),'-an','-c:v','ffv1','-pix_fmt','bgr0','-r','30',str(ROOT/'data/mpu_sample/first121_30hz.avi')],check=True)
    pts_path=ROOT/'results/gt_search/mpu_source_pts.csv';np.savetxt(pts_path,pts,delimiter=',',header='source_pts_s',comments='')
    record={'kind':'source_sample_and_timing_validation','source_frames':len(pts),'gt_rows':len(gt),'csv_count_contiguous':True,'max_abs_count_time_vs_video_pts_s':float(np.max(abs(pts-gt['Count']/60))),'alignment_basis':cfg['gt_timing'],'alignment_limit':cfg['gt_sync_uncertainty'],'input_transform':'first121s, every second 60Hz frame, 30Hz FFV1 bgr0; no temporal warp; verify pixels before inference','files':{path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in [cfg['source_video'],cfg['source_csv'],'data/mpu_sample/first121_30hz.avi','data/mpu_sample/ground_truth.csv']}}
    (ROOT/'results/gt_search/mpu_timing_check.json').write_text(json.dumps(record,indent=2))
    for name,base in [('mtts','mit_face.json'),('bigsmall','bigsmall_mit_face.json')]:
        conf=json.loads((ROOT/'configs'/base).read_text());conf.update(experiment=f'{name}_mpu_sample',video='data/mpu_sample/first121_30hz.avi',output_dir=f'results/{name}_mpu_sample',crop_xywh=cfg['crop_xywh'],ground_truth='data/mpu_sample/ground_truth.csv',display_name='MPU-rPPG public sample, opening 121 seconds')
        (ROOT/f'configs/{name}_mpu_sample.json').write_text(json.dumps(conf,indent=2))
    print(json.dumps(record,indent=2))
if __name__=='__main__':main()
