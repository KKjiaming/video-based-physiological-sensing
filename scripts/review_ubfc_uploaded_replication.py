"""Report all fixed windows, preserving strict failures and separating supplemental analyses."""
from pathlib import Path
import csv,json,hashlib
import numpy as np
from scipy import signal
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from signal_utils import ROOT,detrend
OUT=ROOT/'results/ubfc_replication_uploaded_v1'
SUBJECTS=['subject1','subject4','subject5']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write_csv(path,rows):
    keys=list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w') as f:
        w=csv.DictWriter(f,keys);w.writeheader();w.writerows(rows)
def main():
    primary=[];strict=[];sensitivity=[];models={m:[] for m in ['mtts','bigsmall']}
    fig,axes=plt.subplots(1,3,figsize=(16,5),sharey=True)
    wf,waxes=plt.subplots(3,2,figsize=(15,10),sharex=True,sharey=True)
    for si,s in enumerate(SUBJECTS):
        base=OUT/s;timing=json.loads((base/'timing_audit.json').read_text())
        gt=np.genfromtxt(base/'ground_truth_exact_duplicates_only.csv',delimiter=',',names=True)
        original=np.loadtxt(ROOT/f'data/ubfc_{s}/ground_truth.txt')
        for start,stop in [(0,30),(30,60)]:
            for model in models:
                strict.append({'subject':s,'model':model,'start_s':start,'end_exclusive_s':stop,'status':'failed_original_strict_timestamp_requirement','additional_limitation':'incomplete_second_window' if start else ''})
        for mi,(model,title,color) in enumerate([('mtts','MTTS-CAN','#2166ac'),('bigsmall','BigSmall','#e08214')]):
            ev=json.loads((base/(model+'_evaluation')/'evaluation.json').read_text())['signals']['pulse']
            assert ev['valid_windows']==1 and len(ev['windows'])==1
            arrays=dict(np.load(base/model/'signals.npz'));meta=json.loads((base/model/'summary.json').read_text());fs=meta['config']['fps']
            t=arrays['time_s'];valid=(t>=gt['time_s'][0])&(t<=gt['time_s'][-1]);t=t[valid]
            ref=np.interp(t,gt['time_s'],gt['pulse']);b,a=signal.butter(1,[.75,2.5],btype='bandpass',fs=fs)
            filtered_gt=signal.filtfilt(b,a,detrend(ref,100));pred=signal.filtfilt(b,a,detrend(arrays['pulse_integrated'][valid],100))
            cumsum_error=float(abs(np.cumsum(arrays['pulse_raw_difference'],dtype=np.float64)-arrays['pulse_integrated']).max());assert cumsum_error==0
            row={'subject':s,'model':model,'branch':'supplemental_exact_duplicate_cleanup',**ev['windows'][0]}
            ids=(original[2]>=0)&(original[2]<30)
            row.update(device_hr_median_bpm=float(np.median(original[1,ids])),device_hr_mean_bpm=float(original[1,ids].mean()),device_stats_source='original released samples in [0,30)',fs_hz=fs,samples=int(30*fs),gt_exact_duplicate_removed_index=timing['dropped_exact_duplicate_gt_indices'][0])
            f,pg=signal.periodogram(filtered_gt[:int(30*fs)],fs=fs,window='hann',nfft=int(30*fs));_,pp=signal.periodogram(pred[:int(30*fs)],fs=fs,window='hann',nfft=int(30*fs))
            mask=(f>=.75)&(f<=2.5);kg=np.flatnonzero(mask)[np.argmax(pg[mask])];kp=np.flatnonzero(mask)[np.argmax(pp[mask])]
            assert np.isclose(f[kg]*60,row['reference_waveform_derived_per_min']) and np.isclose(f[kp]*60,row['predicted_per_min'])
            row['reference_peak_hz']=float(f[kg]);row['prediction_peak_hz']=float(f[kp])
            row['recomputed_pearson']=float(np.corrcoef(pred[:int(30*fs)],filtered_gt[:int(30*fs)])[0,1]);assert np.isclose(row['recomputed_pearson'],row['waveform_pearson_no_lag'])
            w=signal.windows.hann(int(30*fs),sym=False);xp=np.fft.rfft((pred[:len(w)]-pred[:len(w)].mean())*w);xg=np.fft.rfft((filtered_gt[:len(w)]-filtered_gt[:len(w)].mean())*w)
            row['phase_at_reference_peak_deg']=float(np.angle(xp[kg]*np.conj(xg[kg]))*180/np.pi)
            row['positive_cumsum_max_abs_error']=cumsum_error
            primary.append(row);models[model].append(row)
            primary.append({'subject':s,'model':model,'branch':'supplemental_exact_duplicate_cleanup','start_s':30,'end_exclusive_s':60,'status':'unavailable_incomplete_30s_window'})
            np.savetxt(base/f'{model}_window1_spectrum.csv',np.column_stack([f,pg,pp]),delimiter=',',header='frequency_hz,reference_psd,prediction_psd',comments='',fmt='%.17g')
            pz=(pred-pred.mean())/pred.std();gz=(filtered_gt-filtered_gt.mean())/filtered_gt.std()
            np.savez_compressed(base/f'{model}_display_arrays.npz',time_s=t,prediction_zscore=pz,contact_ppg_zscore=gz)
            ax=waxes[si,mi];short=t<10;ax.plot(t[short],gz[short],color='#2e995d',lw=1.5,label='Contact PPG');ax.plot(t[short],pz[short],color=color,lw=1,alpha=.8,label=title)
            ax.set(title=f'{s} | {title} | signed r = {row["waveform_pearson_no_lag"]:.3f}',xlabel='Time (s)',ylabel='Full-clip z-score',ylim=(-4,4));ax.legend(fontsize=8);ax.grid(alpha=.2)
        # Predetermined raw-reference sensitivity, kept separate from the model evaluation above.
        grid=np.arange(900)/30;raw=np.interp(grid,gt['time_s'],gt['pulse']);curves={}
        for window in ['hann','boxcar']:
            f,p=signal.periodogram(raw,fs=30,window=window,detrend='constant',nfft=900);curves[window]=p
        mask=(f>=.75)&(f<=2.5);indices=np.flatnonzero(mask)
        local=signal.find_peaks(curves['hann'])[0];local=local[mask[local]];ordered=sorted(local,key=lambda k:curves['hann'][k],reverse=True)
        ratio=float(curves['hann'][ordered[1]]/curves['hann'][ordered[0]]) if len(ordered)>1 else None
        sep=float(abs(f[ordered[1]]-f[ordered[0]])*60) if len(ordered)>1 else None
        rates={name:float(f[indices[np.argmax(p[mask])]]*60) for name,p in curves.items()}
        sensitivity.append({'subject':s,'start_s':0,'end_exclusive_s':30,'status':'supplemental_sensitivity_only','hann_bpm':rates['hann'],'boxcar_bpm':rates['boxcar'],'top_local_peak_bpm':float(f[ordered[0]]*60),'second_local_peak_bpm':float(f[ordered[1]]*60) if len(ordered)>1 else None,'second_to_first_power_ratio':ratio,'peak_separation_bpm':sep,'competing_peak_flag':bool(ratio is not None and ratio>=.5 and sep>=6-1e-8),'window_function_switch_flag':bool(abs(rates['hann']-rates['boxcar'])>=4-1e-8),'device_hr_median_bpm':float(np.median(original[1,(original[2]>=0)&(original[2]<30)]))})
        sensitivity.append({'subject':s,'start_s':30,'end_exclusive_s':60,'status':'unavailable_incomplete_30s_window'})
        np.savetxt(base/'reference_window1_sensitivity.csv',np.column_stack([f,curves['hann'],curves['boxcar']]),delimiter=',',header='frequency_hz,raw_reference_hann_psd,raw_reference_boxcar_psd',comments='',fmt='%.17g')
        peaks=[{'frequency_hz':float(f[k]),'bpm':float(f[k]*60),'hann_psd':float(curves['hann'][k])} for k in ordered]
        (base/'reference_local_peaks.json').write_text(json.dumps(peaks,indent=2))
        ax=axes[si]
        for name,color in [('hann','#2166ac'),('boxcar','#e08214')]:ax.plot(f*60,curves[name]/curves[name][mask].max(),color=color,label=f'{name}: {rates[name]:.0f} bpm',lw=1.7)
        ax.axvline(sensitivity[-2]['device_hr_median_bpm'],ls=':',color='gray',label=f'Device median: {sensitivity[-2]["device_hr_median_bpm"]:.0f}')
        ax.set(xlim=(45,150),ylim=(0,1.15),title=f'{s}: fixed 0-30 s',xlabel='Rate (bpm)',ylabel='Power / each curve peak');ax.legend(fontsize=8);ax.grid(alpha=.2)
    fig.suptitle('Three fixed new recordings | Reference PPG sensitivity only | Exact-duplicate cleanup branch',fontsize=13)
    fig.text(.5,.025,'Hann evaluation retained. Curves normalized separately; not absolute-power or model comparison. Missing second windows are not replaced.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.06,1,.93));fig.savefig(OUT/'new_subject_reference_spectra.png',dpi=180);fig.savefig(OUT/'new_subject_reference_spectra.pdf');plt.close(fig)
    wf.suptitle('Supplemental branch: fixed first 10 s for display | full 30 s for correlation | no lag fitting or sign flip')
    wf.tight_layout(rect=(0,0,1,.95));wf.savefig(OUT/'new_subject_waveforms.png',dpi=160);plt.close(wf)
    summary={'kind':'supplemental_exact_duplicate_cleanup','new_subjects':['subject1','subject4','subject5'],'planned_windows':6,'available_windows':3,'missing_windows':3,'strict_original_evaluable_windows':0,'models':{},'sensitivity':{'available_windows':3,'competing_peak_count':sum(r.get('competing_peak_flag',False) for r in sensitivity),'window_function_switch_count':sum(r.get('window_function_switch_flag',False) for r in sensitivity)},'polarity':'unchanged positive integration; signed zero-lag correlations; no delay optimization','interpretation':'Single window per subject, exploratory small sample, no dataset-wide/model-ranking claim'}
    for model,rows in models.items():
        errors=np.array([r['error_per_min'] for r in rows]);summary['models'][model]={'windows':rows,'mae_bpm':float(abs(errors).mean()),'rmse_bpm':float(np.sqrt((errors**2).mean())),'bias_bpm':float(errors.mean())}
    write_csv(OUT/'original_strict_status.csv',strict);write_csv(OUT/'supplemental_exact_windows.csv',primary);write_csv(OUT/'supplemental_sensitivity.csv',sensitivity)
    (OUT/'comparison.json').write_text(json.dumps(summary,indent=2,allow_nan=False))
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
