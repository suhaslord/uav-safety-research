# Phase 27: train-only camera robustness candidate

**State: candidate implementation, not a verified better model.** This is a separate experiment; Phase 22/23 checkpoints, Phase 25 protected results, and the frozen Phase 26 independent validation plan are unchanged.

The existing Phase 23 detector struggles under severe occlusion and mixed distortions. This exploratory intervention adds limited blur, low light, noise, and partial masking **only to development training images**. The occluder width and height span 22–40% of one annotated target, so at most ~16% of that target is hidden; original labels stay fixed. Moderate versions of these distortions are intended to preserve enough target structure, but improvement is not guaranteed.

## Leakage guard and reproducibility

- Require the historical KIOS **422-frame** split manifest SHA-256 `32623634069c4f3082b79a6a42bca408c636f4b626e5f7691276257999544905`, and verify the same 86 protected test filenames and their recorded hashes.
- Read development `images/train` and `images/val` only. Do **not** read, transform, or copy test or embargo frames. Reject unlisted/missing development inputs.
- Copy original validation images and labels **unchanged**. Put generated variants only into `images/train`.
- Derive random seeds from a fixed seed + original filename + variant number. Record image SHA-256, label SHA-256, and transformation names in the receipt. Reject overwrites.
- Generate `data.yaml` containing only `train` and `val`; never add `test`.

This is **development within the same two KIOS source sequences**, not independent evidence. Phase 26 is still `NO_DATASET_ADMITTED`, and no real-world landing safety claims follow from improving a dev metric.

## Data preparation

First use the verified KIOS source archive and existing `scripts/prepare_kios_real_yolo_split.py` to reconstruct `data/derived/kios_real_yolo`. Then:

```bash
python -m scripts.prepare_phase27_dev_augmentation \
  --split-root data/derived/kios_real_yolo \
  --out data/derived/phase27_train_candidate \
  --seed 20261013 --variants 2
```

This generates candidate training images, copied validation, `data.yaml`, and a detailed `receipt.json`. It does not train weights or assess any holdout.

## Train and evaluate the actual detector

With Ultralytics installed and pretrained `yolo11n.pt` available:

```bash
python -m scripts.train_phase27_dev_candidate \
  --source-root data/derived/kios_real_yolo \
  --candidate-root data/derived/phase27_train_candidate \
  --out results/phase27_dev_comparison \
  --initialization yolo11n.pt --epochs 12 --imgsz 320 \
  --batch 16 --seed 20261013 --device cpu
```

This trains two **fresh independent instances of the same initialization** with fixed augmentation/training settings, varying only the training images. Both are validated on identical, byte-verified *development* `val` images. The comparison emits hashes of each `best.pt` checkpoint and development-only precision, recall, mAP50 and mAP50–95 differences in `comparison.json`. Candidate checkpoints are not automatically substituted for frozen Phase 23 weights.

The GitHub Actions training workflow also runs a short CPU proof-of-execution and uploads the resulting development comparison and candidate weights. Its short run is a **smoke experiment**, not an accuracy/robustness conclusion. A fuller comparison on clean and varied independent sessions is a subsequent preregistered study; we must not pick a threshold based on the old 86 protected views.

## What counts as progress

A working training run and signed source receipts are implementation progress. **A model improvement is demonstrated only if we actually train it, compare both variants on separate development validation data, and obtain favorable reproducible metrics.** That is still weaker than independent Phase 26 testing, which requires new eligible real-camera sessions and verified negative frames.
