# Phase 6 Algorithm Freeze

## Freeze status

The Phase 6 image-to-Aegis algorithm is now frozen for confirmatory evaluation.

**Algorithm freeze commit:** `9cddd41b76302ecc04492ef89fa56de0ea70bc21`

Commits after that point may add validation, metadata, workflow, and reporting infrastructure, but they must not change the Phase 6 perception, robust-velocity, fusion, supervisor, controller, or simulator behavior used by the held-out run.

## What is frozen

The frozen Phase 6 system includes:

1. `Phase6LandingPadRenderer`
   - wider synthetic field of view,
   - perspective marker scale that remains informative closer to touchdown,
   - synthetic clean / blur / low-light / occlusion / mixed degradation.

2. `Phase6PadEstimator`
   - structured connected-component landing-marker measurement,
   - lateral-position and altitude estimates,
   - raw image-quality and geometry features,
   - explicit rejection of low-information frames.

3. `EmpiricalConfidenceCalibrator`
   - deterministic offline calibration using seed `616161`,
   - monotone confidence mapping,
   - development-only synthetic ground-truth labels.

4. `CalibratedTemporalImagePipeline`
   - temporal state tracking,
   - confidence and geometry gates,
   - explicit abstention,
   - uncertainty growth during abstention,
   - multi-frame track reacquisition.

5. `RobustImageVelocityFilter`
   - median-of-pairwise-slopes lateral-velocity estimate,
   - slope-MAD consistency score,
   - conservative update under inconsistent derivatives,
   - no finite-difference spike from dropped frames.

6. `Phase6RedundantFusionAdapter`
   - accepted image tracks remain primary in normal operation,
   - persistent lateral-bias evidence can gradually correct image position,
   - independent reference receives more weight during image abstention,
   - near-ground cross-estimator integrity fallback for smoothly wrong image tracks.

7. Frozen historical `RedundantSafetySupervisorV3`
   - Phase 6 does not rewrite the historical V3 supervisor used in the earlier frozen result.

## Development data already used

The following seeds have influenced design and therefore cannot be called held out:

- `616161` — confidence-calibration development
- `626262` — landing-system development
- `636363` — selective-perception development

Historical Phase 3–5 evaluation seeds and seed families also remain excluded from Phase 6 confirmatory evaluation.

## Development evidence that motivated the freeze

The final 30-episode-per-condition development study used paired seeds for `image_temporal` and `image_aegis_v3`.

The final development sample produced:

| Condition | Image temporal success | Image + Aegis success |
|---|---:|---:|
| clean | 100.0% | 100.0% |
| blur | 100.0% | 100.0% |
| low light | 100.0% | 100.0% |
| occlusion | 80.0% | 96.7% |
| mixed | 56.7% | 100.0% |

In the mixed development sample, 13 image-only unsafe touchdowns became Aegis successes and no image-only successes became Aegis unsafe touchdowns.

These values are **development evidence only** and are not the confirmatory Phase 6 result.

## Important limitation frozen with the system

The standalone abstention mechanism is not being tuned further before confirmatory evaluation.

A separate 10,000-frame development benchmark showed that explicit image abstention remained weakly selective under the hardest synthetic degradation. For `mixed`, raw frame estimates were outside the calibration error tolerances frequently, while only a small fraction were explicitly rejected.

This means the final Phase 6 system-level benefit should not be attributed to abstention alone. The architecture combines:

- calibration,
- temporal filtering and reacquisition,
- robust velocity estimation,
- explicit abstention,
- independent redundant evidence,
- near-ground cross-estimator integrity checking,
- frozen V3 safety supervision.

The selective-abstention weakness must remain visible in the final write-up even if the system-level held-out result is strong.

## Predeclared held-out seeds

Before inspecting any confirmatory results, the following unused seeds are declared:

- **Landing-system held-out seed:** `747474`
- **Selective-perception held-out seed:** `757575`
- **Calibration seed remains:** `616161`

Repository search before this declaration found no existing use of `747474` or `757575`.

## Confirmatory evaluation plan

### Landing-system evaluation

- 5 image conditions
- 2 architectures
- 100 paired episodes per condition/architecture cell
- **1,000 simulated landing episodes total**
- evaluation seed `747474`
- calibration seed `616161`
- severity `1.0`

Primary system-level comparisons:

- `mixed` unsafe-touchdown rate: image temporal vs image+Aegis
- `mixed` success rate: image temporal vs image+Aegis
- `occlusion` unsafe-touchdown rate: image temporal vs image+Aegis
- preservation of clean / blur / low-light performance

Secondary metrics include:

- Wilson confidence intervals,
- paired rescue/regression counts,
- abort and timeout rates,
- image abstention rate,
- calibration reliability,
- touchdown failure decomposition.

### Selective-perception evaluation

- 20 sequences per image condition
- 100 frames per sequence
- 10,000 frames total
- sequence seed `757575`
- calibration seed `616161`

This benchmark measures the abstention mechanism itself and is not interchangeable with the landing-system result.

## No-retuning rule

The held-out results are run once against the frozen algorithm.

If they expose a weakness, that weakness is reported. Any later change becomes a new Phase 6.1 / future version and receives a new development/freeze/evaluation cycle. The held-out seed is never reused as though it remained unseen after inspection.

## Scope

All results remain synthetic-image, planar-simulation results. They are not evidence that the system is safe for a physical UAV and are not flight-control instructions.
