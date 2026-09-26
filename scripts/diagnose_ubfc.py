"""Read-only clock, window, spectrum and polarity audit of the existing UBFC run."""
from pathlib import Path
import json,csv,hashlib
import numpy as np
from scipy import signal
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from signal_utils import ROOT,detrend,postprocess
OUT=ROOT/'results/ubfc_diagnostics'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def psd(x,fs):return signal.periodogram(x,fs=fs,window='hann',detrend='constant',nfft=len(x))
def peak(f,p,lo=.75,hi=2.5):
    ii=np.flatnonzero((f>=lo)&(f<=hi));k=ii[np.argmax(p[ii])];return int(k),float(f[k]),float(60*f[k])
def weighted_mean_hold(t,x,start,stop):
    knots=np.r_[start,t[(t>start)&(t<stop)],stop];idx=np.searchsorted(t,knots[:-1],side='right')-1
    return float(np.dot(x[idx],np.diff(knots))/(stop-start))
def main():
    OUT.mkdir(exist_ok=True)
    protected=[]
    for rel in ['results/mtts_ubfc_subject3','results/bigsmall_ubfc_subject3','results/mtts_ubfc_evaluation','results/bigsmall_ubfc_evaluation','results/ubfc_gt_review','results/ubfc_audit','configs/mtts_ubfc_subject3.json','configs/bigsmall_ubfc_subject3.json','configs/ubfc_subject3_protocol.json','data/ubfc_subject3/ground_truth.txt','data/ubfc_subject3/ground_truth.csv']:
        p=ROOT/rel;protected.extend([p] if p.is_file() else [q for q in p.rglob('*') if q.is_file()])
    before={str(p.relative_to(ROOT)):sha(p) for p in protected}
    gt=np.loadtxt(ROOT/'data/ubfc_subject3/ground_truth.txt');ppg,device,tg=gt
    converted=np.genfromtxt(ROOT/'data/ubfc_subject3/ground_truth.csv',delimiter=',',names=True)
    assert np.array_equal(converted['pulse'],ppg) and np.array_equal(converted['time_s'],tg) and np.array_equal(converted['device_hr_bpm'],device)
    timing=np.genfromtxt(ROOT/'results/ubfc_audit/source_timing.csv',delimiter=',',names=True);tv=timing['container_pts_s'];dt=np.diff(tg)
    fps=29548271/1000000
    fs_avg=(len(tg)-1)/(tg[-1]-tg[0]);offset=tg-tv
    changes=np.flatnonzero(np.diff(device)!=0)+1
    report={'kind':'diagnostic_not_replacement_evaluation','clock':{'source_frames':len(tv),'gt_samples':len(tg),'video_container_fps':fps,'video_last_pts_s':float(tv[-1]),'video_duration_with_last_frame_s':len(tv)/fps,'gt_first_time_s':float(tg[0]),'gt_last_time_s':float(tg[-1]),'gt_average_sample_rate_hz':float(fs_avg),'inverse_median_gt_dt_hz':float(1/np.median(dt)),'gt_min_median_max_dt_s':[float(dt.min()),float(np.median(dt)),float(dt.max())],'gt_nonmonotonic_count':int(np.sum(dt<=0)),'same_index_gt_minus_pts_min_median_max_s':[float(offset.min()),float(np.median(offset)),float(offset.max())],'nominal30_vs_actual_fps_relative_error':float(30/fps-1),'gt_timestamp_units':'seconds per official readme; not milliseconds'},'device_field':{'source':'ground_truth.txt row2: device reported HR, not a waveform or independent raw pulse event list','values_are_integers':bool(np.all(device==np.round(device))),'value_changes_in_file':len(changes),'algorithm_averaging_latency_and_firmware':'not documented in released readme/processor; cannot infer from repeated integer values alone','official_evaluation':'author states compare contact-PPG-derived rates, not device HR row'},'windows':[],'methods':{},'counterfactuals':[]}
    np.savetxt(OUT/'device_hr_changes.csv',np.column_stack([changes,tg[changes],device[changes-1],device[changes]]),delimiter=',',header='gt_index,timestamp_s,old_device_hr_bpm,new_device_hr_bpm',comments='',fmt='%.12g')
    map30=np.genfromtxt(ROOT/'results/ubfc_audit/resampling.csv',delimiter=',',names=True)
    spec_arrays={};fig,axes=plt.subplots(2,2,figsize=(14,9))
    for key,fs in [('mtts',30.),('bigsmall',25.)]:
        arrays=dict(np.load(ROOT/f'results/{key}_ubfc_subject3/signals.npz'));t=arrays['time_s'];g=np.interp(t,tg,ppg)
        b,a=signal.butter(1,[.75,2.5],btype='bandpass',fs=fs);gd=detrend(g,100);gf=signal.filtfilt(b,a,gd);pf=signal.filtfilt(b,a,detrend(arrays['pulse_integrated'],100))
        evaluation=json.loads((ROOT/f'results/{key}_ubfc_evaluation/evaluation.json').read_text())
        integ=np.cumsum(arrays['pulse_raw_difference'],dtype=np.float64);polarity={'cumsum_vs_stored_integrated_max_abs':float(np.max(abs(integ-arrays['pulse_integrated']))),'raw_difference_to_integrated_sign':'positive cumulative sum; no negation','windows':[]}
        if key=='bigsmall':
            raw=np.load(ROOT/'results/bigsmall_ubfc_subject3/raw_outputs.npz');polarity['raw_head_vs_signals_max_abs']=float(np.max(abs(raw['pulse_raw_difference']-arrays['pulse_raw_difference'])))
            cfg=json.loads((ROOT/'configs/bigsmall_ubfc_subject3.json').read_text());_,_,native=postprocess(arrays['pulse_raw_difference'],fs,cfg['pulse_band_hz'],100,1);polarity['native_filter_recompute_max_abs']=float(np.max(abs(native-arrays['pulse_filtered'])))
        for j,(start,stop) in enumerate([(0,30),(30,60)]):
            ia=int(start*fs);ib=int(stop*fs);sl=slice(ia,ib);n=ib-ia
            f,pg=psd(gf[sl],fs);_,pp=psd(pf[sl],fs);kg,fg,hrg=peak(f,pg);kp,fp,hrp=peak(f,pp)
            assert hrp==evaluation['signals']['pulse']['windows'][j]['predicted_per_min'] and hrg==evaluation['signals']['pulse']['windows'][j]['reference_waveform_derived_per_min']
            ids=np.flatnonzero((tg>=start)&(tg<stop));duration=float(tg[ids[-1]]-tg[ids[0]])
            src30=np.arange(ia,ib) if key=='mtts' else arrays['resample_source_index'][sl].astype(int)
            actualsrc=map30['source_frame_index'][src30].astype(int);actualpts=map30['source_pts_s'][src30]
            right=np.searchsorted(tg,t[sl],side='right').clip(1,len(tg)-1);left=right-1
            np.savetxt(OUT/f'{key}_window{j+1}_mapping.csv',np.column_stack([np.arange(ia,ib),t[sl],src30,actualsrc,actualpts,left,right,tg[left],tg[right]]),delimiter=',',header='prediction_index,target_time_s,intermediate30_frame,original_video_frame,original_video_pts_s,gt_left_index,gt_right_index,gt_left_time_s,gt_right_time_s',comments='',fmt='%.12g')
            row={'model':key,'window_index':j+1,'start_s':start,'end_exclusive_s':stop,'prediction_index_start':ia,'prediction_index_stop_exclusive':ib,'samples':n,'fs_hz':fs,'first_sample_s':float(t[ia]),'last_sample_s':float(t[ib-1]),'original_video_frame_min':int(actualsrc.min()),'original_video_frame_max':int(actualsrc.max()),'max_original_frame_time_error_s':float(np.max(abs(actualpts-t[sl]))),'native_gt_index_start':int(ids[0]),'native_gt_index_stop_exclusive':int(ids[-1]+1),'native_gt_count':len(ids),'native_gt_first_s':float(tg[ids[0]]),'native_gt_last_s':float(tg[ids[-1]]),'native_gt_effective_fs_hz':float((len(ids)-1)/duration),'fft_bin_width_hz':fs/n,'fft_bin_width_bpm':60*fs/n,'gt_peak_bin':kg,'gt_peak_hz':fg,'gt_peak_bpm':hrg,'prediction_peak_bin':kp,'prediction_peak_hz':fp,'prediction_peak_bpm':hrp,'device_hr_min':float(device[ids].min()),'device_hr_mean':float(device[ids].mean()),'device_hr_median':float(np.median(device[ids])),'device_hr_time_weighted_mean_zoh':weighted_mean_hold(tg,device,start,stop),'device_hr_max':float(device[ids].max()),'device_median_minus_gt_spectrum_bpm':float(np.median(device[ids])-hrg),'device_median_div_gt_rate':float(np.median(device[ids])/hrg),'required_window_duration_to_map_gt_to_device_s':float(30*hrg/np.median(device[ids])),'waveform_pearson_zero_lag':float(np.corrcoef(pf[sl],gf[sl])[0,1])}
            w=signal.windows.hann(n,sym=False);xp=np.fft.rfft((pf[sl]-pf[sl].mean())*w);xg=np.fft.rfft((gf[sl]-gf[sl].mean())*w);phase=float(np.angle(xp[kg]*np.conj(xg[kg]))*180/np.pi)
            polarity['windows'].append({'window_index':j+1,'gt_frequency_hz':fg,'prediction_minus_gt_phase_deg_at_gt_bin':phase,'zero_lag_pearson':row['waveform_pearson_zero_lag'],'warning':'single-bin phase diagnostic, not a fitted delay or proof of a global sign inversion'})
            primary={};data=[f,pp,pg]
            for name,x in [('raw_interpolated',g),('detrended',gd)]:
                ff,power=psd(x[sl],fs);_,_,rate=peak(ff,power);primary[name+'_peak_bpm']=rate;data.append(power)
            row.update(primary);report['windows'].append(row)
            np.savetxt(OUT/f'{key}_window{j+1}_spectrum.csv',np.column_stack(data),delimiter=',',header='frequency_hz,prediction_psd,reference_filtered_psd,reference_raw_psd,reference_detrended_psd',comments='',fmt='%.17g')
            spec_arrays[f'{key}_w{j+1}_frequency_hz']=f;spec_arrays[f'{key}_w{j+1}_reference_psd']=pg
            if key=='mtts':
                ax=axes[j,0]
                for name,power in [('Raw interpolated',data[3]),('Detrended',data[4]),('Existing filtered',pg)]:
                    mask=(f>=.5)&(f<=3.5);ax.plot(f[mask]*60,power[mask]/power[mask].max(),label=name)
                ax.axvline(hrg,color='green',ls='--',label=f'PPG bin {hrg:.12g} bpm');ax.axvline(row['device_hr_median'],color='red',ls=':',label=f'Device median {row["device_hr_median"]:.12g}')
                ax.set(xlabel='Rate (beats/min)',ylabel='PSD / displayed-band maximum',title=f'Window {start}-{stop}s: primary 30Hz grid, no zero padding');ax.legend(fontsize=8);ax.grid(alpha=.2)
                freq=np.arange(.5,4.0001,.001);native=ppg[ids];ls=signal.lombscargle(tg[ids]-start,native-native.mean(),2*np.pi*freq,normalize=True)
                _,fl,rl=peak(freq,ls);row['native_unfiltered_lomb_peak_hz']=fl;row['native_unfiltered_lomb_peak_bpm']=rl
                np.savetxt(OUT/f'window{j+1}_native_lomb.csv',np.column_stack([freq,ls]),delimiter=',',header='frequency_hz,normalized_lomb_power',comments='',fmt='%.17g')
                ax=axes[j,1];ax.plot(freq*60,ls,label='Native timestamp PPG, no bandpass');ax.axvline(row['device_hr_median'],color='red',ls=':',label='Device median');ax.axvline(rl,color='green',ls='--',label=f'Grid peak {rl:.2f} bpm')
                ax.set(xlabel='Rate (beats/min)',ylabel='Normalized Lomb power',title=f'Window {start}-{stop}s: uneven-time cross-check, 0.06bpm grid');ax.legend(fontsize=8);ax.grid(alpha=.2)
                for clock,tt in [('same_index_container_pts',tv),('nominal30_index_only',np.arange(len(ppg))/30)]:
                    grid=np.arange(start,stop,1/30);gx=np.interp(grid,tt,ppg);ff,power=psd(gx,30);_,_,rate=peak(ff,power)
                    report['counterfactuals'].append({'window_index':j+1,'clock':clock,'raw_ppg_hann_peak_bpm':rate,'purpose':'one-off time interpretation sensitivity, not a replacement GT or optimized protocol'})
        report['methods'][key]=polarity
    fig.suptitle('UBFC subject3 reference spectra | diagnostic only; existing outputs unchanged');fig.tight_layout();fig.savefig(OUT/'reference_spectra.png',dpi=160);plt.close(fig)
    np.savez_compressed(OUT/'spectra.npz',**spec_arrays)
    # One row per method/window with all values at full binary-float precision in JSON/CSV.
    fields=list(dict.fromkeys(k for r in report['windows'] for k in r))
    with (OUT/'exact_windows.csv').open('w') as f:
        w=csv.DictWriter(f,fields);w.writeheader();w.writerows(report['windows'])
    fig,axes=plt.subplots(3,1,figsize=(12,8))
    axes[0].plot(tg,device,label='Released device HR');axes[0].set(ylabel='Device HR (bpm)');axes[0].legend()
    axes[1].plot(tv,offset);axes[1].set(ylabel='GT time - container PTS (s)')
    axes[2].plot(tg[1:],dt*1000);axes[2].set(ylabel='GT interval (ms)',xlabel='Time (s)')
    for ax in axes:
        for boundary in [0,30,60]:ax.axvline(boundary,color='gray',ls=':',alpha=.6)
        ax.grid(alpha=.2)
    fig.suptitle('Original clocks and device field; no corrections applied');fig.tight_layout();fig.savefig(OUT/'timing_and_device_hr.png',dpi=150);plt.close(fig)
    after={str(p.relative_to(ROOT)):sha(p) for p in protected};assert before==after
    (OUT/'preserved_artifacts.json').write_text(json.dumps({'unchanged':True,'files':before},indent=2))
    report['old_artifacts_unchanged']=True;report['script_sha256']=sha(Path(__file__))
    (OUT/'audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
