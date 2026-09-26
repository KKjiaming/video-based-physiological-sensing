#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python scripts/prepare_ubfc_sample.py
.venv/bin/python scripts/infer_mtts.py --config configs/mtts_ubfc_subject3.json
.venv/bin/python scripts/infer_bigsmall.py --config configs/bigsmall_ubfc_subject3.json
for method in mtts bigsmall; do
  .venv/bin/python scripts/evaluate_signals.py \
    --prediction-dir "results/${method}_ubfc_subject3" \
    --ground-truth data/ubfc_subject3/ground_truth.csv --gt-offset-s 0 \
    --sync-note 'UBFC subject3 original GT timestamps and video container PTS; fixed zero-start offset; no fitted lag; same-index differences up to0.373s; gaps up to239ms interpolated under fixed250ms cap.' \
    --pulse-band-hz 0.75 2.5 --max-gt-gap-s 0.25 \
    --output "results/${method}_ubfc_evaluation"
done
.venv/bin/python scripts/review_ubfc_results.py
