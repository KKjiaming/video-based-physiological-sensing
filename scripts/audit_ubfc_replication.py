"""Inventory the frozen sample and separate primary results from sensitivity analyses."""
from pathlib import Path
import csv, hashlib, json
import numpy as np
from scipy.signal import find_peaks
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/ubfc_replication'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write_csv(name,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with (OUT/name).open('w') as f:
        w=csv.DictWriter(f,keys);w.writeheader();w.writerows(rows)
def main():
    lock=json.loads((OUT/'protocol_lock.json').read_text());assert sha(ROOT/lock['file'])==lock['sha256']
    cfg=json.loads((ROOT/lock['file']).read_text());inventory=[];primary=[];sensitivity=[]
    # Exploratory anchor is copied as-is and never included as a new replication subject.
    for model in ['mtts','bigsmall']:
        ev=json.loads((ROOT/f'results/{model}_ubfc_evaluation/evaluation.json').read_text())
        for r in ev['signals']['pulse']['windows']:
            primary.append({'subject':'subject3','cohort':'exploratory_anchor','model':model,**r})
    for j in [1,2]:
        a=np.genfromtxt(ROOT/f'results/ubfc_diagnostics/window{j}_window_function_spectra.csv',delimiter=',',names=True)
        f=a['frequency_hz'];p=a['raw_ppg_hann_psd'];b=a['raw_ppg_boxcar_psd'];mask=(f>=.75)&(f<=2.5)
        local=find_peaks(p)[0];local=local[mask[local]];ii=sorted(local,key=lambda k:p[k],reverse=True)
        ratio=float(p[ii[1]]/p[ii[0]]);sep=float(abs(f[ii[1]]-f[ii[0]])*60)
        kh=np.flatnonzero(mask)[np.argmax(p[mask])];kb=np.flatnonzero(mask)[np.argmax(b[mask])]
        sensitivity.append({'subject':'subject3','cohort':'exploratory_anchor','start_s':30*(j-1),'end_exclusive_s':30*j,'status':'existing_sensitivity_only','hann_peak_bpm':float(f[kh]*60),'boxcar_peak_bpm':float(f[kb]*60),'second_local_peak_bpm':float(f[ii[1]]*60),'second_to_first_power_ratio':ratio,'peak_separation_bpm':sep,'competing_peak_flag':ratio>=.5 and sep>=6-1e-8,'window_function_switch_flag':abs(f[kh]-f[kb])*60>=4-1e-8})
    downloads=json.loads((OUT/'download_status.json').read_text())
    for item in cfg['subjects']:
        s=item['id'];d=ROOT/item['local_directory'];g=d/'ground_truth.txt';record={'subject':s,'video_present':(d/'vid.avi').exists(),'gt_present':g.exists(),'roi_selected':False,'new_spectra_inspected':False,'inference_run':False,'gt_checks':None}
        if g.exists():
            a=np.loadtxt(g);dt=np.diff(a[2]);bad=np.flatnonzero(dt<=0)
            record['gt_checks']={'shape':list(a.shape),'sha256':sha(g),'finite':bool(np.isfinite(a).all()),'first_s':float(a[2,0]),'last_s':float(a[2,-1]),'max_gap_s':float(dt.max()),'strictly_increasing':len(bad)==0,'nonincreasing_pairs':[{'left_index':int(k),'right_index':int(k+1),'timestamps_s':a[2,k:k+2].tolist(),'all_three_rows_identical':bool(np.array_equal(a[:,k],a[:,k+1]))} for k in bad]}
            record['primary_gt_quality_passed']=bool(a.shape[0]==3 and np.isfinite(a).all() and len(bad)==0 and dt.max()<=cfg['max_gt_gap_s'])
        else:record['primary_gt_quality_passed']=False
        record['video_download']=next(r for r in downloads if r['subject']==s and r['name']=='vid.avi')
        err=OUT/f'{s}_vid.avi_error.html'
        if err.exists() and 'quota exceeded' in err.read_text().lower():record['video_download']['reason']='Google Drive quota exceeded'
        inventory.append(record)
        for start,stop in cfg['windows_s']:
            issues=[]
            if not record['video_present']:issues.append('video_missing_download_quota')
            if not record['primary_gt_quality_passed']:issues.append('GT_fails_frozen_strict_timestamp_rule')
            # This is an input coverage screen; model grids must also cover a window before scoring.
            if record['gt_checks'] and record['gt_checks']['last_s']<stop-1/30:issues.append('GT_does_not_cover_full_window')
            status=';'.join(issues) or 'pending_ROI_and_inference'
            for m in ['mtts','bigsmall']:
                primary.append({'subject':s,'cohort':'prospective_new','model':m,'start_s':start,'end_exclusive_s':stop,'status':status})
            sensitivity.append({'subject':s,'cohort':'prospective_new','start_s':start,'end_exclusive_s':stop,'status':status+';new_spectra_not_inspected_before_ROI'})
    write_csv('primary_results.csv',primary);write_csv('sensitivity_results.csv',sensitivity)
    report={'protocol_sha256':lock['sha256'],'new_subjects_planned':3,'new_subjects_with_video':sum(r['video_present'] for r in inventory),'new_subjects_passing_GT_quality':sum(r['primary_gt_quality_passed'] for r in inventory),'new_windows_planned':6,'new_windows_evaluated':0,'replication_claim':'not evaluated; missing videos and timestamp quality failures; no substitute subjects or altered preprocessing','subjects':inventory}
    (OUT/'sample_inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    baseline=json.loads((OUT/'preservation_baseline.json').read_text());changed=[p for p,h in baseline.items() if sha(ROOT/p)!=h];assert not changed,changed
    (OUT/'verification.json').write_text(json.dumps({'original_files_checked':len(baseline),'changed':changed,'frozen_protocol_unchanged':True,'original_evaluation_values_copied_without_recalculation':True,'no_new_inference_or_GT_spectral_analysis':True},indent=2))
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
