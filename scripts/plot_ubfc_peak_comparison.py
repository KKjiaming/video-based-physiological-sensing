"""English reference-PPG sensitivity figure; original numerical results remain unchanged."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/ubfc_replication'
STEM = 'subject3_reference_sensitivity_en'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                     'axes.spines.top': False, 'axes.spines.right': False, 'pdf.fonttype': 42})

def main():
    OUT.mkdir(exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(15, 7), sharex=True, sharey=True)
    metadata = {'kind': 'reference_PPG_sensitivity_only_not_model_comparison',
                'source': 'Existing raw-reference PSD CSVs; primary evaluation unchanged',
                'normalization': 'Each curve divided by its own maximum PSD within 45-150 bpm',
                'scope': 'Two windows from one recording, UBFC subject3; not a dataset-wide result',
                'comparison_limit': 'Peak locations and relative within-curve shape; absolute PSD not comparable',
                'peaks': []}
    for j, ax in enumerate(axes):
        source = ROOT / f'results/ubfc_diagnostics/window{j+1}_window_function_spectra.csv'
        d = np.genfromtxt(source, delimiter=',', names=True)
        bpm = d['frequency_hz'] * 60
        h, b = d['raw_ppg_hann_psd'], d['raw_ppg_boxcar_psd']
        band = (bpm >= 45) & (bpm <= 150)
        hs, bs = float(h[band].max()), float(b[band].max())
        hn, bn = h / hs, b / bs
        assert np.isclose(hn[band].max(), 1) and np.isclose(bn[band].max(), 1)
        ax.plot(bpm, hn, color='#2166ac', lw=2.5, marker='o', ms=3, label='Hann window')
        ax.plot(bpm, bn, color='#e08214', lw=2.1, marker='s', ms=2.5, label='Rectangular window (sensitivity)')
        median = [101, 105][j]
        ax.axvline(median, color='#777777', ls=':', lw=1.7, label=f'Device HR median: {median} bpm')
        ax.set(xlim=(65, 125), ylim=(0, 1.38), xlabel='Frequency expressed as heart rate (bpm)',
               xticks=np.arange(70, 121, 10), yticks=[0, .25, .5, .75, 1])
        ax.grid(alpha=.16)
        arrow = {'arrowstyle': '->', 'color': '#333333', 'lw': 1.3}
        box = {'facecolor': 'white', 'edgecolor': '#dddddd', 'boxstyle': 'round,pad=.4'}
        if j == 0:
            ax.set_title('Window 1: 0-30 s\nCompeting peaks at 88 and 102 bpm', fontsize=14, pad=12)
            for rate, pos in [(88, (77, 1.22)), (102, (111, 1.22))]:
                k = np.argmin(abs(bpm-rate))
                ax.annotate(f'{rate} bpm\ncandidate peak', xy=(rate, max(hn[k], bn[k])), xytext=pos,
                            ha='center', fontsize=12, fontweight='bold', arrowprops=arrow)
            ax.text(.025, .73, 'Hann selects 88\nRectangular selects 102', transform=ax.transAxes,
                    fontsize=10, bbox=box)
        else:
            ax.set_title('Window 2: 30-60 s\nBoth window functions select 92 bpm', fontsize=14, pad=12)
            k = np.argmin(abs(bpm-92))
            ax.annotate('92 bpm\nshared dominant peak', xy=(92, max(hn[k], bn[k])), xytext=(82, 1.22),
                        ha='center', fontsize=12, fontweight='bold', arrowprops=arrow)
            ax.text(.70, .73, 'Device median: 105\nDiscrepancy remains', transform=ax.transAxes,
                    ha='center', fontsize=10, bbox=box)
        kh = np.flatnonzero(band)[np.argmax(h[band])]
        kb = np.flatnonzero(band)[np.argmax(b[band])]
        metadata['peaks'].append({'window_s': [30*j, 30*(j+1)], 'hann_bpm': float(bpm[kh]),
                                 'boxcar_bpm': float(bpm[kb]), 'hann_psd_divisor': hs, 'boxcar_psd_divisor': bs,
                                 'source_csv': str(source.relative_to(ROOT))})
    handles, _ = axes[0].get_legend_handles_labels()
    fig.legend(handles, ['Hann window', 'Rectangular window (sensitivity)', 'Device HR median: 101 / 105 bpm (window 1 / 2)'],
               loc='center', bbox_to_anchor=(.5, .175), ncol=3, fontsize=10, frameon=False)
    axes[0].set_ylabel('Power / each curve\'s own peak power')
    fig.suptitle('Reference PPG spectral sensitivity: a single-recording case study', fontsize=18, y=.98)
    fig.text(.5, .918, 'UBFC subject3 | Contact PPG reference analysis, not a comparison of model performance',
             ha='center', fontsize=11, color='#444444')
    notes = [
        'Each curve is normalized by its own peak within 45-150 bpm: compare peak locations and relative shapes, not absolute power.',
        'Identical 30 Hz interpolated PPG; no bandpass or zero padding; 2 bpm frequency bins. Original evaluation retained; no device-guided selection.',
        'Two windows from one recording cannot establish the true heart rate or represent the full UBFC dataset.'
    ]
    for y, note in zip([.105, .068, .028], notes):
        fig.text(.5, y, note, ha='center', fontsize=10, color='#333333')
    fig.subplots_adjust(top=.76, bottom=.27, wspace=.13, left=.07, right=.985)
    for ext in ['png', 'pdf', 'svg']:
        fig.savefig(OUT / f'{STEM}.{ext}', dpi=180)
    plt.close(fig)
    (OUT / f'{STEM}_metadata.json').write_text(json.dumps(metadata, indent=2))
    print(json.dumps(metadata, indent=2))

if __name__ == '__main__':
    main()
