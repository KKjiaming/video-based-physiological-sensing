"""Check preservation, exact-duplicate equivalence, model weights and per-window mappings."""
import hashlib,json
from pathlib import Path
import numpy as np
from signal_utils import ROOT
OUT=ROOT/'results/ubfc_replication_uploaded_v1'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def main():
    lock=json.loads((OUT/'protocol_lock.json').read_text());assert sha(ROOT/lock['file'])==lock['sha256']
    cfg=json.loads((ROOT/lock['file']).read_text());assert sha(ROOT/cfg['parent_protocol'])==cfg['parent_sha256']
    before=json.loads((OUT/'preservation_baseline.json').read_text());changed=[p for p,h in before.items() if sha(ROOT/p)!=h];assert not changed,changed
    checks=[]
    for item in cfg['subjects']:
        s=item['subject'];base=OUT/s;orig=np.loadtxt(ROOT/item['source_gt']);clean=np.genfromtxt(base/'ground_truth_exact_duplicates_only.csv',delimiter=',',names=True)
        index=np.genfromtxt(base/'gt_source_index_mapping.csv',delimiter=',',names=True)['original_gt_index'].astype(int)
        assert np.array_equal(orig[2,index],clean['time_s']) and np.array_equal(orig[0,index],clean['pulse']) and np.array_equal(orig[1,index],clean['device_hr_bpm'])
        gt_t=clean['time_s'];map30=np.genfromtxt(base/'resampling.csv',delimiter=',',names=True)
        r={'subject':s,'GT_values_and_timestamps_unchanged_for_kept_indices':True,'model_checks':{}}
        for m in ['mtts','bigsmall']:
            a=dict(np.load(base/m/'signals.npz'));old=json.loads((ROOT/f'results/{m}_ubfc_subject3/summary.json').read_text());new=json.loads((base/m/'summary.json').read_text())
            fs=new['config']['fps'];assert fs==old['config']['fps']
            for k in ['fps','frame_depth','batch_size','detrend_lambda','filter_order','pulse_band_hz','resp_band_hz','spectrum_window']:
                assert new['config'][k]==old['config'][k],(s,m,k)
            if m=='bigsmall':
                wh=new['runtime']['weight_sha256'];assert wh==old['runtime']['weight_sha256']
            else:
                # Both inference runs use the same checkpoint path; also verify its original recorded hash below.
                assert new['config']['weights']==old['config']['weights'];wh=sha(ROOT/new['config']['weights'])
                assert wh=='74d53d039bb7adc08309a1b389537a0c79fddc479b064dd660ef7007fb47d022'
            n=int(30*fs);t=a['time_s'][:n];src30=np.arange(n) if m=='mtts' else a['resample_source_index'][:n].astype(int)
            vi=map30['source_frame_index'][src30].astype(int);vp=map30['source_pts_s'][src30]
            right=np.searchsorted(gt_t,t,side='right').clip(1,len(gt_t)-1);left=right-1
            np.savetxt(base/f'{m}_window1_mapping.csv',np.column_stack([np.arange(n),t,src30,vi,vp,index[left],index[right],gt_t[left],gt_t[right]]),delimiter=',',header='prediction_index,target_time_s,intermediate30_index,original_video_frame,original_video_pts_s,original_gt_left_index,original_gt_right_index,gt_left_time_s,gt_right_time_s',comments='',fmt='%.17g')
            interp_error=float(abs(np.interp(t,orig[2],orig[0])-np.interp(t,gt_t,clean['pulse'])).max());assert interp_error==0
            assert all(np.isfinite(v).all() for v in a.values())
            r['model_checks'][m]={'unchanged_model_processing':True,'weight_sha256':wh,'window1_max_original_frame_time_error_s':float(abs(vp-t).max()),'exact_dedup_interpolation_max_abs_difference':interp_error,'signed_integration_max_abs_error':float(abs(np.cumsum(a['pulse_raw_difference'],dtype=np.float64)-a['pulse_integrated']).max())}
        checks.append(r)
    # The exploratory anchor must also remain the uploaded video originally audited.
    anchor=sha(ROOT/'data/ubfc_subject3/vid.avi');assert anchor=='f94656f6b49710a03a9d3d79fb06f2d9389adb40720a331314e9818f90618787'
    report={'frozen_supplemental_protocol_unchanged':True,'frozen_parent_protocol_unchanged':True,'prior_files_checked':len(before),'prior_files_changed':changed,'subject3_video_sha256':anchor,'subjects':checks}
    (OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
