# Phase 22 input representation follow-up

This new paired diagnostic preserves the original experiment's reported stop:
**INCONCLUSIVE — CLEAN CONTROL GATE FAILED — NO TREATMENT INFERENCE RUN.**
It does not amend that preregistration. The original protocol and execution
artifacts were not present in the fetched repository; their status is recorded
from the supplied assignment, not presented as a newly authenticated result.

The committed `results/phase22_input_representation/protocol.json` freezes the
new question before inference. Its SHA is
`bd653fe22f90b2bf941909c5f96ceeeb9aab7f75dda0e58bbc9d7d785b4122bf`.
The population is 86 protected source frames (66 from `land_pad`, 20 from
`land_pad2`), each represented as original JPEG bytes, historical RGB/JPEG Q95,
Q90, Q100, and lossless PNG. Variants are paired transformations of sources.

The checkpoint, protected manifest, archive, labels, historical clean image
inventory, implementation, and runtime are checked before inference. Q95 must
match the existing historical inventory hash exactly, independently of the
aggregate metric gate. The manifest records every derived byte hash and image
difference. Missing matched confidence remains missing; its paired comparison
uses only frames that pass in both representations. The unconditional
best-prediction confidence comparison explicitly assigns zero to no-prediction
frames.

Per-frame boxes are exported from the **same official validation pass** that
produces the aggregate metrics, with the historical settings unchanged. Frame
success means all annotation boxes have confidence-ranked, one-to-one,
same-class matches at IoU >= 0.5 using the fixed 0.001 confidence floor. Extra
false positives do not change that success flag. Official aggregate precision
and recall use Ultralytics' F1 operating point; these differ conceptually from
the counts at the low prediction floor. Neither threshold is tuned here.

The primary paired comparison is RAW_SOURCE versus HISTORICAL_Q95. Exact
McNemar/binomial testing and paired source-frame percentile bootstrap intervals
are exploratory, conditional on the two source videos. Temporal dependence
limits their interpretation: these intervals do not estimate uncertainty across
independent flight sessions. Pixel differences and their prediction associations
are descriptive; no learned compression mechanism is established.

## Reproduce

Download and SHA-verify the `phase22-baseline-recovery` release bundle from
https://github.com/suhaslord/uav-safety-research/releases/tag/phase22-baseline-recovery.
Its bundle SHA is
`8d6eda7f8775ad899be7a8b6fbf9e6dea30678c1e28c0b687a88184ac592288b`.
Extract `best.pt`; its SHA must be
`3a1801b192d624f8dcdda4bc5d9a9157309000df67a4c30d62368c37901feddd`.
Use the checksum-verified KIOS archive and the repository's unchanged
`scripts/prepare_kios_real_yolo_split.py` to reconstruct the split. The expected
archive SHA is
`9d27a3e9616c188fb72a727633705735da5df168ce47efeed389dcb3455fdbdb`.

Use the runtime and JPEG library versions recorded in the committed protocol.
CPU Torch/Torchvision versions include the `+cpu` build suffix. Install those
explicitly together with Ultralytics to prevent dependency resolution from
replacing the CPU build. Python and Pillow codec behavior are part of the freeze.

For a fresh output directory:

```bash
python scripts/run_phase22_representation_study.py prepare \
  --archive /path/to/airisim_dataset2.7z \
  --source /path/to/kios_real_yolo \
  --weights /path/to/best.pt \
  --work /path/to/representation-images \
  --out /path/to/new-study
```

Inspect and commit the resulting protocol and manifest **before inference**.
Pass the printed SHA explicitly:

```bash
python scripts/run_phase22_representation_study.py run \
  --archive /path/to/airisim_dataset2.7z \
  --source /path/to/kios_real_yolo \
  --weights /path/to/best.pt \
  --work /path/to/representation-images \
  --out /path/to/new-study \
  --protocol-sha SHA_PRINTED_BY_PREPARE
```

For exact replay, compare the prepared representation manifest against the
committed manifest and the runtime against the committed protocol. The runtime
platform string deliberately rejects an unrecorded environment for an existing
freeze; a cross-platform investigation must create a separate follow-up freeze.
No existing result directory is overwritten. Derived images can be reconstructed
from the protected sources; all their hashes are retained in the manifest.

## Stage B prerequisite

A passing Stage A does **not** supply the original sweep's dose levels or mask
geometry. Before creating or executing v2, recover the original frozen protocol
and failed clean-gate artifacts, record their hashes and provenance, and read
the exact doses and centered-mask geometry from those files. Do not reconstruct
them from the 516-case count or from the older six-condition robustness suite.
Only then freeze a separate v2 protocol, generate inputs, pass a new zero-dose
Q95 gate, and run treatments. No v2 protocol, zero-dose run, treatment predictions,
or occlusion threshold conclusion is claimed by the representation diagnostic.
