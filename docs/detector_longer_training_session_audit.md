# AegisLand detector — longer training and session-stratified development audit

**Existing detector only; no new research phase.** This research experiment
does not modify the frozen Phase 23 detector, historical protected split, or
production website. It does not authorize aircraft control.

## Motivation

The earlier conservative 12-epoch YOLO11n candidate (15% train-only
photometric substitutions) showed **substantial seed sensitivity**. In seed
20261014, clean development mAP50 increased 0.620 → 0.834 and mixed stress
increased 0.122 → 0.542, but the independent repeat seed 20261013 showed
much smaller/negative condition-specific deltas. Neither is independent
camera generalization.

## New, fixed comparison (before new training results)

Run two separately initialized **YOLO11n** models from the same original
pretrained weights, one on 252 untouched development training images and one
on exactly 252 images with 15% in-place train-only substitutions (blur,
low-light and sensor noise, not target occlusion). Keep all labels and
image names fixed. For both models:

- seed **20261015**, 20 epochs, 384-pixel inputs, batch size 16, SGD;
- identical step count, model, settings, development-validation frames;
- report 64 original development-validation images and all five matched,
  deterministic derived stress conditions with no protected-test inference;
- apply the unchanged existing conservative development screen (clean mAP50
  and precision, blur and mixed mAP50 no-regression plus average gain);
- **add video-sequence diagnostic reporting**: split every development
  validation condition by original source-video ID (`land_pad` and
  `land_pad2`), then report precision, recall, mAP50 and mAP50–95 within
  each sequence for each model. These are two correlated source videos,
  **not** independent camera sites, and are not a new model-selection gate.

Different seeds, epoch counts, and input resolutions mean this new comparison
must not be compared as a controlled causal effect against the older
12-epoch results. Only its own equal-budget baseline and candidate are
paired. Both checkpoints and full configuration/hashes are archived as
research artifacts; **the published/frozen detector will not be replaced**.

## Gate for external evidence

The previous data-screen still has no accepted independent real-camera
dataset, compatible physical target annotations, or verified no-pad negative
frames. Neither training on more epochs nor duplicating frames can address
that limitation. Prospective testing on independent sessions must obey
the pre-existing frozen dataset admission and test-seal requirements.

If the new candidate has no consistent measurable clean and stress advantage
across both original development source videos, record the negative result.
Even if it passes the development screen, it remains **research-only** until
eligible independent validation. No claims of 100% accuracy, universal
dataset performance or real flight safety are justified.
