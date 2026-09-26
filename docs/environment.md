# Runtime and compatibility

Inference was verified on Linux x86_64 using separate TensorFlow and PyTorch environments, with model execution on CPU. System CUDA or GPU configuration is not a requirement for the demonstrated execution path. No training or fine-tuning was performed.

| Component | Verified runtime |
|---|---|
| MTTS-CAN | Python 3.11; TensorFlow CPU 2.15.1; NumPy 1.26.4 |
| BigSmall model subprocess | Python 3.11.10; PyTorch 2.0.1+cu117; NumPy 1.26.0 |
| BigSmall preprocessing/evaluation | Project TensorFlow-side environment; model tensors passed to the separate PyTorch process through local NPZ files |
| Video tools | System `ffmpeg` and `ffprobe` |
| CPU threads | MTTS-CAN: 4 intra-op / 2 inter-op; BigSmall: 4 / 2 |

The direct Python requirements are in [requirements.txt](../requirements.txt); [requirements-lock.txt](../requirements-lock.txt) records the full tested TensorFlow-side environment. The local BigSmall environment was cloned from an existing environment. Its large package snapshot includes unrelated packages and local build paths and is intentionally excluded from the public repository. It is not a portable installation recipe. A clean installation on another machine has not been verified by this project.

## MTTS-CAN compatibility check

The upstream README targeted TensorFlow 2.2–2.4. Under the tested newer runtime, loading through private `tensorflow.python.keras` imports produced incorrectly assigned same-shaped weights in two convolutional layer pairs, and `predict()` encountered an internal API error. That execution is not used for the reported results.

The compatibility adapter substitutes public `tensorflow.keras` imports in memory and runs sequential eager batches with `training=False`. All 14 weighted layers were checked against their named HDF5 tensors; reconstructing the saved HDF5 model graph produced a maximum forward-output difference of zero on the software-check input. No layers were skipped or retrained, and the network architecture was not changed.

[Saved-graph verification](../results/mtts_serialized_graph_check.json). This is a software check, not physiological accuracy evidence or a claim of bitwise equivalence across all historical TensorFlow versions. Full loading traces remain local and can be regenerated with the audit scripts.

## BigSmall execution

The original BigSmall and Toolbox checkpoints each passed strict loading into their corresponding model implementation. The reported real-video experiments use the Toolbox Fold1 checkpoint pinned in [sources.json](../configs/sources.json), not an interchangeable mixture of the two checkpoints.

[BigSmall loading verification](../results/bigsmall_audit.json). Inference is forced to CPU. The model exposes AU, pulse and respiration outputs; AU logits are not interpreted, and respiration has no corresponding reference in the current recordings.

## Public and local records

Host inventories, installation logs, cloned environment snapshots, and absolute host paths are not part of the public release. Model versions, checkpoint hashes, reproducible scripts, and concise verification records are retained. See [publication scope](publication.md).
