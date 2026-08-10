# Phase 6 — Synthetic Image-Based Perception Front End

## Why this phase exists

Aegis V1-V3 use state-level perception stress models. Those models are useful for isolating safety logic, but they do not test whether uncertainty can be estimated from pixels.

Phase 6 begins replacing that abstraction with a controlled image benchmark.

This first image experiment is intentionally simple and simulation-only. It does **not** claim calibrated camera physics or real-aircraft validation.

## Current implementation

`src/uav_safety/image_perception.py` contains:

- a synthetic grayscale landing-pad renderer
- controlled image degradation
- an interpretable threshold/centroid estimator
- a confidence score derived from visible contrast and support

The renderer supports:

- `clean`
- `blur`
- `low_light`
- `occlusion`
- `mixed`

The image estimator currently predicts **lateral landing-pad offset only**. It is not yet connected to the simulated landing controller.

That separation is intentional: first measure the perception front end by itself, then integrate it only after its failure behavior is understood.

## First benchmark

```bash
python scripts/run_image_perception_benchmark.py --samples 300 --seed 606060
```

Outputs:

```text
results/image_perception/
├── samples.csv
├── summary.csv
├── summary.md
├── run_metadata.json
├── mae_by_condition.png
├── valid_rate.png
└── example_conditions.png
```

Primary metrics:

- valid-estimate rate
- mean absolute lateral error
- 95th-percentile lateral error
- mean confidence
- correlation between confidence and absolute error

## What we want to learn

The goal is not merely low average error.

A useful safety-facing perception model should also show that:

1. confidence falls when the image becomes harder to interpret;
2. large errors are more likely to have low confidence;
3. occlusion and low-light failures are visible in the metrics rather than hidden;
4. the estimator can explicitly return an invalid estimate when evidence is insufficient.

## Planned progression

### 6A — standalone synthetic image benchmark

Current stage.

### 6B — confidence calibration

Add:

- reliability curves
- error bins by confidence
- expected calibration-style metrics for geometric error
- failure galleries

### 6C — temporal image sequences

Render short frame sequences so the image estimator can be tested under:

- repeated occlusion
- changing lateral offset
- confidence recovery
- stale observations

### 6D — connect pixels to Aegis

Convert the image estimator output into the same observation interface used by the existing simulator, then compare:

- abstract state-level perception
- synthetic pixel perception

without changing the safety supervisor.

### 6E — stronger perception model

Only after the simple estimator's behavior is measured, consider a learned model or more realistic synthetic imagery.

## Research-integrity rule

The current V3 frozen result remains a state-level simulation result.

Future pixel-based results must be reported separately. Image-based experiments should not be described as if they were part of the original 10,000-episode frozen evaluation.
