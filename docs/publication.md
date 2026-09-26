# Public repository contents

The repository presents video-based human physiological sensing through pretrained inference, reference-signal evaluation, and documented limitations. The public selection includes implementation and evidence needed to inspect the conclusions; full datasets and local execution archives are kept separately.

| Include in Git | Purpose |
|---|---|
| `README.md`, `ATTRIBUTION.md` | Research direction, observations, limits, and authorship |
| `scripts/*.py`, `scripts/*.sh` | Authored loading checks, inference, evaluation, diagnostics, and visualization |
| `configs/**/*.json` | Fixed sample lists, processing protocols, model sources, commits and checkpoint hashes |
| Public `docs/*.md` | Methods and experiment records, including negative findings and missing windows |
| `requirements.txt`, `requirements-lock.txt` | Direct requirements and the tested TensorFlow environment versions |
| `licenses/*-LICENSE.txt` | Exact upstream license notices; third-party code and weights are fetched separately |
| Explicitly named `results/` files in `.gitignore` | Selected plots, per-window derived metrics, spectral summaries, software checks, and four named rendered UBFC demos with matching thumbnails |

The original strict analysis and the supplemental exact-duplicate-cleanup analysis remain distinct. Publishing results does not turn the observed zero error on selected FFT bins into proof of physiological accuracy. No failed windows or negative waveform correlations are removed from the selected summaries.

| Keep local | Reason for exclusion |
|---|---|
| `data/` | Source videos, contact sensor recordings, model input arrays and prepared media |
| `.venv*`, `third_party/`, checkpoints | Large environments and separately sourced upstream code/weights |
| Unlisted `results/` files | Complete waveforms, raw AU outputs, per-frame mappings, intermediate arrays and run archives |
| Unlisted face previews, source frames, contact sheets and videos | Only the four named 30-second rendered demos and their matching thumbnails are selected; all raw source media remain local |
| Downloaded HTML, HTTP responses, agreement spreadsheets, download logs | Acquisition records rather than project implementation; some include transient download-form fields |
| Host inventories and `requirements-bigsmall-lock.txt` | Host-specific paths, unrelated cloned packages and nonportable build references |
| `docs/progress.md`, `docs/completion_audit.md` | Historical host-operation and delivery journals rather than the current research narrative |
| Credentials, caches, bytecode, temporary files | Not project source or evaluation evidence |

The `.gitignore` uses a root allowlist and an explicit results allowlist. New result files are not automatically published. A later figure must be reviewed and named in the allowlist deliberately. These rules do not delete local files or change the original experiments.

## Selected video demonstrations

The README leads with the existing subject3 video and preview. The user also selected preserving the current video demonstrations in the public project; the related subjects 1, 4 and 5 are linked alongside it. `configs/publication_media.json` records the exact files; `.gitignore` permits only these named videos after the general media exclusion rule.

| Demo | Branch | Length |
|---|---|---|
| [Subject 3](../results/ubfc_gt_review/video_with_gt.mp4) | Original subject3 evaluation | 30 s |
| [Subject 1](../results/ubfc_replication_uploaded_v1/subject1/video_with_reference.mp4) | Supplemental exact-duplicate GT cleanup | 30 s |
| [Subject 4](../results/ubfc_replication_uploaded_v1/subject4/video_with_reference.mp4) | Supplemental exact-duplicate GT cleanup | 30 s |
| [Subject 5](../results/ubfc_replication_uploaded_v1/subject5/video_with_reference.mp4) | Supplemental exact-duplicate GT cleanup | 30 s |

The videos contain actual facial images, the fixed ROI, model outputs and contact PPG. They explicitly describe offline analysis; they do not demonstrate validated respiratory measurement. UBFC source attribution is retained in [ATTRIBUTION.md](../ATTRIBUTION.md). Raw dataset videos, complete sensor traces, model weights and environments remain excluded.

## Reading local artifact references

The reports retain references to complete local evidence using plain `local artifact` paths when the artifact is excluded from Git. Those are not downloadable repository links. Public figures, metrics and the four selected video demos remain clickable. The four 30-second videos use refreshed chart spacing rendered from unchanged saved display arrays and evaluation values. Inference, signal polarity, timing and numerical results were not recomputed. Original videos, previews and presentation metadata are archived locally in `results/video_layout_archive/`. The rendering scripts can recreate the demonstrations after acquiring the original data and running the prerequisite inference and evaluation.

This repository is not a bundled dataset or a one-command reproduction of every historical host operation. Some acquisition and integrity scripts rely on local audit records. The frozen configurations and scripts record what was done, while the public summaries and plots allow inspection without shipping the data or the entire server environment.

## Check the intended upload

```bash
python3 scripts/check_publication.py
# Read-only preview: does not stage, commit or push.
git add --dry-run .
```

The check lists unexpected tracked/ignored files, sensitive filename classes, known credential patterns, oversized files and broken public Markdown links. It also verifies that the selected numerical files and figures match their local audit copies. Pattern checks are a focused aid, not proof that arbitrary future content is safe to publish.

No local files are deleted, no staging or commit is performed, and no push is part of preparing the ignore rules. The project does not currently contain a top-level license for its own work; upstream notices are preserved separately rather than treating all code as having one common license.
