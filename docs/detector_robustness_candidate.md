# Detector robustness: train-only camera robustness candidate

**State: candidate implementation, not a verified better model.** This is an optional training experiment within the existing detector work, not a new numbered research phase. Historical Phase 22/23 checkpoints, Phase 25 protected results, and the frozen independent validation plan are unchanged.

The existing Phase 23 detector struggles under severe occlusion and mixed distortions. This exploratory intervention adds limited blur, low light, noise, and partial masking **only to development training images**. The occluder width and height span 22–40% of one annotated target, so at most ~16% of that target is hidden; original labels stay fixed. Moderate versions of these distortions are intended to preserve enough target structure, but improvement is not guaranteed.

## Leakage guard and reproducibility

- Require the historical KIOS **422-frame** split manifest SHA-256 `32623634069c4f3082b79a6a42bca408c636f4b626e5f7691276257999544905`, and verify the same 86 protected test filenames and their recorded hashes.
- Read development `images/train` and `images/val` only. Do **not** read, transform, or copy test or embargo frames. Reject unlisted/missing development inputs.
- Copy original validation images and labels **unchanged**. Put generated variants only into `images/train`.
- Derive random seeds from a fixed seed + original filename + variant number. Record image SHA-256, label SHA-256, and transformation names in the receipt. Reject overwrites.
- Generate `data.yaml` containing only `train` and `val`; never add `test`.

This is **development within the same two KIOS source sequences**, not independent evidence. Phase 26 is still `NO_DATASET_ADMITTED`, and no real-world landing safety claims follow from improving a dev metric.

## Matched-budget detector comparison

The earlier two-epoch pilot had a serious confound: the augmented arm saw 756
images per epoch versus 252 in the baseline, so it received about triple
the optimizer steps. **Do not interpret that pilot's positive mAP50 delta as
the effect of augmentation.** The existing documented result is preserved.

We now run the same detector training code with **252 images per arm per epoch**.
For the augmented arm, exactly half of the 252 original training images are
replaced in-place by deterministic moderate camera-stress versions; the other
half remain bit-identical originals. The same files and labels are used in both
arms and the 64 original development-validation images are untouched. Both arms
have the same initialization, batch size, epochs, optimizer and seed, so they
receive equal optimizer-step budgets.

After fitting, the exact same saved checkpoints are evaluated on clean
validation frames and five deterministic *development validation* stress
conditions. These are correlated transformations of the same KIOS videos; they
do not supply new capture sessions, negative-target examples or independent
generalization evidence. No existing protected test or frozen protocol is
changed or reused for model selection.

Reconstruct the verified historical source split and run:

```bash
python -m scripts.prepare_detector_robustness_augmentation \
  --split-root data/derived/kios_real_yolo \
  --out data/derived/detector_robustness_matched \
  --seed 20261013 --mode matched --variants 1 --replace-fraction 0.5

python -m scripts.train_detector_robustness_candidate \
  --source-root data/derived/kios_real_yolo \
  --candidate-root data/derived/detector_robustness_matched \
  --out results/detector_robustness_matched_comparison \
  --initialization yolo11n.pt --epochs 4 --imgsz 320 \
  --batch 16 --seed 20261013 --device cpu
```

The GitHub Actions workflow `detector-robustness-pilot.yml` performs this
matched-budget four-epoch CPU experiment, runs the unit-test guards and saves
both model weights and a machine-readable `comparison.json`. It reports
per-condition development precision, recall, mAP50 and mAP50–95 without a
selected deployment threshold or safety claims. If this comparison shows
regressions, retain the existing model; do not promote the candidate.

## What counts as progress

A working training run and signed source receipts are implementation progress. **A model improvement is demonstrated only if we actually train it, compare both variants on separate development validation data, and obtain favorable reproducible metrics.** That is still weaker than independent Phase 26 testing, which requires new eligible real-camera sessions and verified negative frames.


## Conservative photometric-only follow-up (2026-10-13; frozen before run)

The equal-budget 50%-replacement candidate lost clean, blur, and mixed-stress
mAP50, even though noise and partial occlusion sometimes improved. It is
**not promoted** (see `detector_robustness_matched_budget_results_20261013.md`).
Do not change the original model or reinterpret that negative result.

This limited follow-up holds model, data split, training hyperparameters and
total optimizer budget fixed but makes the training intervention substantially
milder: replace only **15% of the 252 development training images**, equally
distributed among **blur, low-light and noise**. Leave all other train images
byte-identical to originals. No target obstruction or mixed corruption is used
for training, though **all six** existing development-validation conditions
are evaluated unchanged. Reconstructing the original clean training baseline
remains part of the paired training workflow. The frozen test frames remain
sealed and are never used to train, choose a candidate, or set thresholds.

Both arms use **12 epochs, 320 px, batch 16, SGD, seed 20261013**, equal
training-image counts and equal optimization-step budgets. Only
development-validation metrics may be compared; there is just one seed and
two temporally dependent KIOS camera sequences.

The development screen, implemented before this run in
`scripts/train_detector_robustness_candidate.py`, requires **all five**:

- Clean mAP50 drop no worse than 0.005.
- Clean precision drop no worse than 0.05.
- Blur mAP50 drop no worse than 0.02.
- Mixed mAP50 drop no worse than 0.02.
- Equal-weight six-condition average mAP50 gain of at least 0.01.

These guardrails are exploratory development checks, **not** proof of
independent generalization. A passing screen will **not automatically promote
model weights**. A failing screen means keep the original detector. The
previous historical Phase 23 weights, held-out reports, and any frozen
external-data admission criteria remain unchanged. No fresh independent
camera-domain test is claimed.

Run the existing workflow via a PR, or reproduce with:

```bash
python -m scripts.prepare_detector_robustness_augmentation \
  --split-root data/derived/kios_real_yolo \
  --out data/derived/detector_robustness_photometric_15pct \
  --seed 20261013 --mode matched --variants 1 \
  --replace-fraction 0.15 --train-condition-set photometric

python -m scripts.train_detector_robustness_candidate \
  --source-root data/derived/kios_real_yolo \
  --candidate-root data/derived/detector_robustness_photometric_15pct \
  --out results/detector_robustness_photometric_15pct \
  --initialization yolo11n.pt --epochs 12 --imgsz 320 \
  --batch 16 --seed 20261013 --device cpu
```

No real-flight execution or controller changes are included.
