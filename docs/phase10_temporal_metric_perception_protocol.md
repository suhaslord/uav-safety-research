# Phase 10 — Temporal Metric Perception Protocol

Status: preregistered development protocol

Branch: `phase10-temporal-metric-perception`

Parent branch head at Phase 10 start: `8455c140da5de6696a8736293c3afe3d208bc245`

Protected Phase 9 evidence head: `33c5c73768757b508f5c613b2fba73f94e3fd5a6`

## Scope and claim boundary

Phase 10 is a simulation-only research phase. It does not authorize physical flight, does not constitute a safety acceptance, and does not change the frozen Phase 6B or Phase 8 results. The Phase 9 result remains an audited baseline and must not be rewritten or retuned.

The objective is to improve metric perception and uncertainty calibration from raw camera sequences while preserving honest abstention and provenance.

## Why Phase 10 exists

Phase 9 showed strong detection availability on one seen Gazebo trace but weak metric geometry and uncertainty calibration:

- truth-visible frames: 25
- observed truth-visible frames: 25
- false positives: 0
- lateral MAE: 0.998 m
- lateral p95 absolute error: 5.087 m
- altitude MAE: 1.520 m
- altitude p95 absolute error: 6.597 m
- median |lateral residual| / sigma: 8.11
- median |altitude residual| / sigma: 5.89

Phase 10 therefore does not optimize for detection rate first. It targets the geometry and calibration failure mode directly.

## Primary hypothesis

A temporal metric estimator that combines multi-frame pose hypotheses, temporal consistency, robust state estimation, and development-only uncertainty calibration can materially reduce metric error versus the unchanged Phase 9 single-frame PnP baseline without sacrificing observation integrity.

## Model concept

Working name: **AegisT10**.

AegisT10 is a hybrid temporal estimator, not an end-to-end controller.

### Stage 1 — unchanged observation front-end

Preserve the Phase 9 raw-frame ingestion, frame hashes, camera intrinsics, ArUco detection, and fixed quad fallback as a comparable front-end.

For every observed frame retain:

- ordered four-corner coordinates
- detector kind and marker identity when available
- detected area and side lengths
- reprojection diagnostics
- timestamp
- raw image hash

No Phase 9 truth visibility field may be used as an inference input.

### Stage 2 — multiple pose hypotheses

Replace the single accepted PnP solution with an explicit candidate set when the geometry permits it. Candidate scoring may use only inference-time image measurements and temporal state, never simulator truth.

Candidate features should include:

- positive depth validity
- reprojection RMS
- corner geometry / quadrilateral consistency
- marker footprint
- detector type
- continuity relative to the prior temporal state

### Stage 3 — temporal state estimator

Maintain a state over a short causal history rather than treating every frame independently.

Initial state proposal:

`[lateral_position, altitude, lateral_velocity, vertical_velocity]`

The first implementation should use a deterministic robust filter so the gain from temporal reasoning can be isolated before adding a learned residual model.

Required behavior:

- causal only; no future-frame leakage in the primary online metric
- explicit prediction step between observations
- innovation gating
- robust weighting for large residuals
- track loss and reacquisition state
- abstention when geometry is insufficient
- no silent carry-forward marked as a fresh observation

### Stage 4 — calibrated uncertainty

The Phase 9 reprojection-derived sigma was strongly under-dispersed. Phase 10 must calibrate uncertainty using development data only.

Candidate calibration features:

- reprojection RMS
- marker footprint / side length
- detector kind
- temporal innovation magnitude
- time since last accepted observation
- track age
- pose-hypothesis disagreement

The first calibration model should remain interpretable (binned empirical or low-capacity regression). A learned heteroscedastic head may be tested later as an ablation, but the held-out set must remain untouched.

### Stage 5 — optional learned residual corrector

Only after the deterministic temporal estimator is stable, test a small residual model that predicts a correction to the deterministic estimate rather than replacing geometry wholesale.

Rules:

- train only on declared development sequences
- inputs must be inference-available quantities
- no simulator truth pose as an input
- truth may appear only as the training target
- frozen holdout remains inaccessible until model and calibration are frozen
- report deterministic and learned variants separately

## Data split and anti-leakage rules

Phase 10 must not treat the existing Phase 9 seen trace as an unseen test set. It is already inspected and is therefore development/reference evidence only.

Create three evidence roles:

1. `phase10_development_seen`
   - inspected during implementation
   - may be used for debugging, calibration, and ablations

2. `phase10_validation_seen`
   - may be inspected for model selection but not final claims

3. `phase10_holdout_unseen`
   - generated from predeclared simulator seeds / trajectories after architecture and thresholds are frozen
   - must not be opened manually before the final evaluation workflow

Whenever feasible, holdout differences should include trajectory, range/altitude profile, target position or orientation, lighting/exposure conditions, and image degradation parameters rather than only a new random seed on the same scene.

## Baselines

Every Phase 10 result must run on paired inputs against:

1. **Phase 9 single-frame PnP baseline** — unchanged algorithm
2. **Temporal smoothing baseline** — simple causal smoothing of Phase 9 estimates
3. **AegisT10 deterministic temporal estimator**
4. **AegisT10 + calibrated uncertainty**
5. optional **AegisT10 + learned residual correction**

This prevents a complex model from receiving credit for gains obtainable by trivial smoothing.

## Predeclared success criteria

The final decision uses paired holdout traces and the unchanged Phase 9 estimator rerun on those same frames.

### Minimum substantial-win gate

AegisT10 must satisfy all of the following on the frozen holdout aggregate:

- lateral MAE reduced by at least **50%** relative to Phase 9 baseline
- altitude MAE reduced by at least **50%** relative to Phase 9 baseline
- lateral p95 absolute error reduced by at least **35%**
- altitude p95 absolute error reduced by at least **35%**
- observation availability on truth-visible frames no worse than Phase 9 by more than **2 percentage points**
- no material false-positive regression
- median normalized absolute residual (`|residual| / sigma`) for each metric below **2.0**
- uncertainty coverage diagnostics reported, not hidden

### Stretch gate

The Phase 10 stretch target is:

- at least **65%** reduction in both lateral and altitude MAE
- at least **50%** reduction in both p95 errors
- median `|residual| / sigma` between **0.7 and 1.5** for both axes
- no observation-availability loss relative to the paired Phase 9 baseline

These are targets, not guaranteed outcomes. Failure to reach them remains a valid scientific result.

## Secondary metrics

Report at minimum:

- MAE, median absolute error, RMSE, p90, p95, maximum absolute error
- signed bias
- error versus apparent marker area / range proxy
- error versus detector kind
- track loss count and duration
- reacquisition latency
- observation availability
- false positives / false negatives under the existing truth definition
- sigma distribution
- median and p95 normalized residual
- empirical 1-sigma and 2-sigma coverage
- temporal lag / autocorrelation of residuals
- compute time per frame

## Required ablations

Before any final Phase 10 claim, compare:

- single-frame Phase 9 PnP
- PnP + simple exponential smoothing
- multiple-hypothesis PnP without temporal state
- temporal estimator without calibrated uncertainty
- temporal estimator with calibrated uncertainty
- optional learned residual corrector
- ArUco-only versus quad-fallback-inclusive subsets

## Files planned for implementation

New files should be isolated from the frozen Phase 9 analyzer where possible:

- `src/uav_safety/phase10_metric.py` — temporal metric state, candidate scoring, uncertainty interface
- `src/uav_safety/phase10_calibration.py` — development-only uncertainty calibration
- `scripts/run_phase10_metric_benchmark.py` — paired baseline/model evaluation
- `scripts/generate_phase10_fixture.py` — deterministic non-authoritative fixture for CI
- `tests/test_phase10_metric.py`
- `tests/test_phase10_calibration.py`
- `.github/workflows/phase10-development.yml`
- `.github/workflows/phase10-frozen-evaluation.yml` only after the architecture is frozen

The Phase 9 analyzer remains a preserved baseline rather than being edited into Phase 10.

## Freeze sequence

1. implement deterministic fixture pipeline
2. establish paired Phase 9 baseline output
3. implement temporal candidate/state estimator
4. run development ablations
5. fit uncertainty calibration on development data only
6. choose final architecture and thresholds
7. write freeze manifest with exact code SHA and configuration
8. generate holdout simulator evidence only after freeze
9. run one exact-head frozen evaluation workflow
10. archive raw evidence, manifests, model parameters, and hashes

## Research integrity rules

- no post-hoc holdout threshold tuning
- no deletion of failed Phase 10 runs
- no overwriting Phase 9 evidence
- no simulator ground-truth camera pose as an inference feature
- no future-frame information in the primary causal model
- calibration is fit on development data only
- all baseline/model comparisons are paired on identical frames
- missing observations remain missing
- physical flight remains out of scope
- `safety_acceptance = false` unless a future, separately defined validation program justifies a different claim

## First implementation milestone

Phase 10 milestone A is complete only when:

- the new branch passes legacy CI
- a non-authoritative deterministic Phase 10 fixture exists
- Phase 9 baseline and AegisT10 run on identical fixture frames
- temporal state and reacquisition unit tests pass
- output contains paired per-frame errors and uncertainty diagnostics
- result manifest records exact input/output hashes

No claim of improvement is made at milestone A. It exists only to validate the pipeline before development experiments begin.
