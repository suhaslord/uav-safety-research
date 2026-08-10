# Phase 6 — Temporal Image Perception + Calibration + Abstention

## Research question

Can the Aegis V3 safety architecture retain its simulated landing-safety advantage when the primary perception stream comes from degraded pixel sequences rather than directly corrupted state variables?

## Why this phase exists

Phase 5 found that the first standalone synthetic image estimator was too willing to return a valid estimate. Under severe mixed degradation, some estimates were wrong by more than one meter while every frame was still marked valid.

Phase 6 therefore changes the perception interface before touching the frozen V3 algorithm.

## Architecture

```text
synthetic camera frame
        ↓
structured pad estimator
        ↓
raw x / z / confidence
        ↓
empirical confidence calibration
        ↓
temporal consistency check
        ↓
ACCEPT or ABSTAIN
        ↓
image-derived Observation
        ↓
Aegis V3 redundant fusion + supervisor
        ↓
landing controller
```

## 1. Pixel measurement

`Phase6PadEstimator` identifies the largest bright connected component rather than averaging all thresholded pixels. It estimates:

- lateral offset from the component centroid,
- altitude from apparent pad size,
- a raw confidence score from contrast, support, and shape quality.

This estimator is still deliberately interpretable and simulation-only.

## 2. Confidence calibration

`EmpiricalConfidenceCalibrator` is fit on a deterministic development dataset that is separate from evaluation episode seeds.

The calibration target is the empirical probability that a frame estimate is simultaneously within:

- 0.30 m lateral error, and
- 0.85 m altitude error.

Calibration labels use synthetic ground truth only during offline fitting. Runtime landing episodes receive pixels only.

## 3. Temporal perception

`CalibratedTemporalImagePipeline` tracks accepted observations across time.

For each new frame it:

1. estimates x and z from pixels,
2. converts raw confidence into calibrated confidence,
3. predicts the next observation from the previous image-derived state,
4. computes a normalized temporal innovation,
5. accepts the frame or abstains.

Accepted frame sequences provide image-derived lateral/vertical velocity estimates through finite differences and temporal smoothing.

## 4. Explicit abstention

The image front end abstains when:

- no reliable landing-pad component is found,
- calibrated confidence is too low, or
- the frame is inconsistent with the existing temporal track.

An abstention is represented as a dropped `Observation`. The pipeline propagates the previous accepted state, lowers confidence, and grows uncertainty. It does not present a new fabricated visual measurement as trustworthy.

## 5. Direct Aegis integration

`run_image_episode` removes the abstract `PerceptionModel` from the Phase 6 primary perception path.

A paired episode uses isolated RNG streams for:

- initial state and simulated wind,
- synthetic image rendering,
- independent reference estimation.

Two architectures are compared:

- `image_temporal`: calibrated temporal image perception directly drives the landing controller;
- `image_aegis_v3`: the exact same image-derived observation is fused with the intentionally imperfect independent reference estimate and assessed by the existing V3 supervisor.

The frozen historical V3 simulator and its published Phase 3–5 results are not modified.

## Evaluation outputs

`scripts/run_phase6_image_landing.py` records:

- success / unsafe touchdown / abort / timeout rates,
- image abstention rate,
- mean calibrated confidence,
- accepted-frame lateral error,
- Aegis intervention count,
- paired rescue and regression counts,
- a held-out calibration reliability table,
- deterministic run metadata and the fitted calibration table.

## Reproducibility split

Default seeds are intentionally separate:

- calibration development seed: `616161`
- episode evaluation seed: `626262`

The evaluation script rejects identical calibration/evaluation seeds.

## Safety scope

This remains a synthetic, planar simulation study. It is not a camera calibration system, autopilot, or real-aircraft safety claim.
