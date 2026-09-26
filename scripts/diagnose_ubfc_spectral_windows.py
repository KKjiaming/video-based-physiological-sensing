"""Follow-up sensitivity diagnosis, not a replacement evaluation or parameter search."""
from pathlib import Path
import json, csv
import numpy as np
from scipy import signal
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/ubfc_diagnostics'

def spectrum(x, window):
    return signal.periodogram(x, fs=30, window=window, detrend='constant', nfft=len(x))

def peaks(f, p):
    band = (f >= .75) & (f <= 2.5)
    local, _ = signal.find_peaks(p)
    candidates = local[band[local]]
    candidates = sorted(candidates, key=lambda k: p[k], reverse=True)
    return [{'bpm': float(60*f[k]), 'frequency_hz': float(f[k]), 'psd': float(p[k])} for k in candidates[:6]]

def main():
    ppg, device, t = np.loadtxt(ROOT / 'data/ubfc_subject3/ground_truth.txt')
    # Same time grid for every comparison; no filtering, polarity change or fitted delay.
    grid = np.arange(1800) / 30
    x = np.interp(grid, t, ppg)
    report = {'purpose': 'Post hoc diagnostic prompted by first-window multiple peaks. Not preregistered and not used to replace original evaluation.',
              'processing': 'Original PPG timestamps, linear interpolation to 30 Hz; mean removed by periodogram; no bandpass; no zero padding.',
              'search_band_hz': [.75, 2.5], 'windows': [], 'fixed_10s_cross_checks': []}
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))
    for j, start in enumerate([0, 30]):
        row = {'start_s': start, 'end_exclusive_s': start+30, 'frequency_bin_bpm': 2., 'spectra': {}}
        cols = []
        ids = (t >= start) & (t < start+30)
        median = float(np.median(device[ids]))
        for name in ['hann', 'boxcar']:
            f, p = spectrum(x[start*30:(start+30)*30], name)
            top = peaks(f, p)
            row['spectra'][name] = {'top_local_peaks': top}
            cols.append(p)
            mask = (f*60 >= 60) & (f*60 <= 140)
            axes[j].plot(f[mask]*60, p[mask], marker='.', label=f'{name}: peak {top[0]["bpm"]:.0f} bpm')
        np.savetxt(OUT / f'window{j+1}_window_function_spectra.csv', np.column_stack([f, *cols]), delimiter=',',
                   header='frequency_hz,raw_ppg_hann_psd,raw_ppg_boxcar_psd', comments='', fmt='%.17g')
        axes[j].axvline(median, color='red', ls=':', label=f'Device median: {median:.0f} bpm')
        axes[j].set(title=f'{start}-{start+30}s: identical PPG samples, only spectral weighting differs', xlabel='Rate (bpm)', ylabel='PSD')
        axes[j].legend(); axes[j].grid(alpha=.25)
        report['windows'].append(row)
    fig.suptitle('Diagnostic sensitivity only | original Hann evaluation unchanged')
    fig.tight_layout(); fig.savefig(OUT / 'window_sensitivity.png', dpi=150); plt.close(fig)
    for start in range(0, 60, 10):
        f, p = spectrum(x[start*30:(start+10)*30], 'hann')
        ids = (t >= start) & (t < start+10)
        report['fixed_10s_cross_checks'].append({'start_s': start, 'end_exclusive_s': start+10,
            'ppg_hann_peak_bpm': peaks(f,p)[0]['bpm'], 'device_median_bpm': float(np.median(device[ids])), 'bin_width_bpm': 6.})
    # Fixed 10-second windows, one-second hop. This only visualizes nonstationarity.
    f, tt, s = signal.spectrogram(x, fs=30, window='hann', nperseg=300, noverlap=270, nfft=300, detrend='constant', mode='psd')
    band = (f >= .75) & (f <= 2.5)
    power = s[band]
    relative_db = 10*np.log10(np.maximum(power / power.max(axis=0, keepdims=True), 1e-6))
    fig, ax = plt.subplots(figsize=(12, 4.5))
    im = ax.pcolormesh(tt, f[band]*60, relative_db, shading='nearest', vmin=-25, vmax=0, cmap='viridis')
    ax.plot(t, device, color='white', lw=1.5, label='Released device HR')
    ax.axvline(30, color='white', ls=':', alpha=.8)
    ax.set(xlim=(0,60), ylim=(45,150), xlabel='Window center time (s)', ylabel='Rate (bpm)',
           title='Raw reference PPG: fixed 10s Hann windows, 1s hop, 6bpm bins (diagnostic only)')
    ax.legend(loc='upper left'); fig.colorbar(im, ax=ax, label='dB relative to each window maximum')
    fig.tight_layout(); fig.savefig(OUT / 'reference_time_frequency.png', dpi=150); plt.close(fig)
    np.savez_compressed(OUT / 'reference_time_frequency.npz', frequency_hz=f, window_center_s=tt, psd=s)
    (OUT / 'window_sensitivity.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
