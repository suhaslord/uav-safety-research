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
