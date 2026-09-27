# Reproduction

Run commands from the project directory. The setup script creates a local environment and fetches fixed official code, checkpoints, and the small demonstration input. It stops rather than overwriting a mismatched third-party checkout.

```bash
bash scripts/setup_cpu.sh
.venv/bin/python scripts/check_saved_graph.py
.venv/bin/python scripts/check_signal_math.py
.venv/bin/python scripts/check_evaluation.py
.venv/bin/python scripts/infer_mtts.py --config configs/mit_face.json
```

`requirements-lock.txt` records the working TensorFlow environment. The Keras import adaptation passed per-layer weight checks and forward comparison with the model graph saved in the HDF5 file; this does not imply bitwise equivalence to every original TensorFlow version. See the [environment record](environment.md).

BigSmall uses a separate PyTorch environment. The following **host-specific** offline clone was verified on the current machine; replace `/path/to/compatible-pytorch-environment` with a compatible existing environment. It is unnecessary if `.venv-bigsmall` is already present:

```bash
conda create --offline --yes --prefix "$PWD/.venv-bigsmall" --clone /path/to/compatible-pytorch-environment
.venv-bigsmall/bin/python scripts/run_bigsmall_model.py
.venv/bin/python scripts/infer_bigsmall.py
.venv/bin/python scripts/verify_delivery.py
```

The verified runtime uses Python 3.11.10, PyTorch 2.0.1+cu117, torchvision 0.15.2 and NumPy 1.26.0, with inference forced to CPU. `requirements-bigsmall-lock.txt` and `results/bigsmall_conda_packages.json` are local-only environment snapshots, excluded from this repository; they are not a verified portable installation recipe. The cloned snapshot includes unrelated packages and historical local build paths; the project does not invoke them.

For existing subject3 outputs, regenerate the English presentation figure without rerunning inference:

```bash
.venv/bin/python scripts/plot_ubfc_peak_comparison.py
```

Full data-specific commands are in the [UBFC report](ubfc_report.md) and [MPU report](gt_followup.md). Raw differences, integrated and filtered waveforms, timestamps, spectra, and configurations are retained in each run's `signals.npz`, `signals.csv`, and `summary.json`.

For a new recording with an independently synchronized reference, the evaluation interface is:

```bash
.venv/bin/python scripts/evaluate_signals.py \
  --prediction-dir results/YOUR_RUN \
  --ground-truth data/YOUR_SYNCED_SENSOR.csv \
  --gt-offset-s 0 \
  --sync-note 'Document acquisition-based synchronization; do not fit a delay' \
  --output results/YOUR_EVALUATION
```

The reference CSV requires `time_s` and `pulse` and/or `resp` waveform columns. Device HR/RR scalars are not substitutes for waveform columns. A recording-specific protocol must fix timing, bands, and quality rules before evaluation; the command above is an interface example.


See [methods](methods.md), [publication scope](publication.md), and [source attribution](../ATTRIBUTION.md).

## README animation

The inline GIF is a presentation-only conversion of the complete subject3 MP4: 30 seconds at original speed, 880 pixels wide, 5 fps, looping. The MP4 remains available at full quality. No inference or evaluation is rerun. From the repository root:

```bash
ffmpeg -hide_banner -loglevel error -nostdin -n -threads 2 \
  -i results/ubfc_gt_review/video_with_gt.mp4 \
  -filter_complex_threads 1 \
  -filter_complex '[0:v]fps=5,scale=880:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle' \
  -loop 0 results/ubfc_gt_review/demo.gif
```

The command refuses to overwrite an existing GIF.
