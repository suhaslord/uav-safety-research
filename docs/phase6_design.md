# Phase 6 — Temporal Image Perception + Calibration + Abstention

## Research question

Can the Aegis V3 safety architecture retain its simulated landing-safety advantage when the primary perception stream comes from degraded pixel sequences rather than directly corrupted state variables?

## Why this phase exists

Phase 5 found that the first standalone synthetic image estimator was too willing to return a valid estimate. Under severe mixed degradation, some estimates were wrong by more than one meter while every frame was still marked valid.

Phase 6 therefore changes the perception interface without rewriting the frozen historical V3 supervisor.

## Architecture

```text
synthetic camera frame
        ↓
structured pad estimator
        ↓
raw x / z / image-quality features
        ↓
empirical confidence calibration
        ↓
temporal tracker + reacquisition
        ↓
ACCEPT or ABSTAIN
        ↓
robust lateral-velocity estimator
        ↓
image-derived Observation
        ↓
Phase 6 redundant-fusion adapter
        ↓
frozen V3 safety supervisor
        ↓
landing controller
```

## 1. Phase-6-only perspective renderer

Phase 6 uses `Phase6LandingPadRenderer` instead of changing the Phase 5 image renderer.

The earlier renderer intentionally clipped apparent marker size. That was acceptable for a standalone image benchmark, but it made altitude increasingly unobservable close to simulated touchdown. The Phase 6 renderer therefore adds:

- a wider synthetic camera field of view,
- an outline/cross landing marker whose bounding box remains measurable near the ground,
- a perspective scale that remains informative closer to touchdown,
- the same synthetic blur, low-light, occlusion, and mixed degradation families.

Historical Phase 5 results and renderer behavior remain unchanged.

## 2. Pixel measurement

`Phase6PadEstimator` identifies the largest bright connected component and estimates:

- lateral offset from the component centroid,
- altitude from apparent marker size,
- raw confidence from contrast, support, and geometry,
- a geometry score used by the runtime quality gate.

Low-information frames are explicitly rejected before thresholding so blank or nearly uniform images cannot masquerade as a valid landing marker.

## 3. Confidence calibration

`EmpiricalConfidenceCalibrator` is fit on a deterministic development dataset separate from evaluation episode seeds.

The calibration target is the empirical probability that a frame estimate is simultaneously within:

- 0.30 m lateral error, and
- 0.85 m altitude error.

Calibration labels use synthetic ground truth only during offline fitting. Runtime landing episodes receive pixels only.

The fitted mapping is forced to be monotone: increasing raw confidence cannot reduce calibrated probability, and expected error cannot increase with confidence.

## 4. Temporal perception

`CalibratedTemporalImagePipeline` tracks accepted observations across time.

For each new frame it:

1. estimates x and z from pixels,
2. converts raw confidence into calibrated confidence,
3. evaluates image quality and marker geometry,
4. predicts the next observation from the current temporal track,
5. computes a normalized temporal innovation,
6. accepts, abstains, or begins a reacquisition sequence.

Accepted measurements are stored in a short history window rather than treated as unrelated frames.

### Reacquisition

An early Phase 6 prototype could enter an innovation lockout: one large measurement jump was rejected, leaving a stale track that caused every subsequent good frame to be rejected too.

The current tracker fixes this by allowing a new track after multiple mutually consistent, high-quality measurements. One surprising frame can still be rejected, while a persistent coherent sequence can recover the tracker.

## 5. Explicit abstention

The image front end abstains when:

- no reliable marker component is found,
- raw image quality is too low,
- calibrated confidence is too low,
- post-acquisition marker geometry is implausible, or
- a measurement is temporarily inconsistent with the existing track.

An abstention is represented as a dropped `Observation`. The previous image-derived state is propagated, confidence falls, and uncertainty grows. The system does not manufacture a new trustworthy camera measurement.

## 6. Robust lateral velocity

The first 30-episode-per-condition Phase 6 development study found a specific failure that was not obvious from position error alone. Under `mixed`, accepted lateral position estimates averaged roughly 0.14 m error, yet most unsafe touchdowns violated the simulated horizontal-speed limit. For `image_aegis_v3`, 18 of 19 mixed unsafe touchdowns violated horizontal speed while none violated vertical speed.

That showed that differentiating noisy image positions was the dominant remaining development problem.

`RobustImageVelocityFilter` therefore treats lateral velocity as a separate perception quantity:

- accepted lateral positions are stored in a longer short-term history,
- all sufficiently time-separated pairwise position slopes are computed,
- the median slope supplies an outlier-resistant velocity target,
- median absolute deviation of the slope set measures derivative consistency,
- inconsistent slope sets update the velocity state more conservatively,
- dropped frames do not generate artificial finite-difference spikes,
- confidence and uncertainty are adjusted mildly when velocity evidence is weak.

The same stabilized image observation is used by both `image_temporal` and `image_aegis_v3`, so the Aegis comparison remains paired at the perception-interface level.

## 7. Direct Aegis integration

`run_image_episode` removes the abstract `PerceptionModel` from the Phase 6 primary perception path.

A paired episode uses isolated RNG streams for:

- initial state and simulated wind,
- synthetic image rendering,
- independent reference estimation.

Two architectures are compared:

- `image_temporal`: calibrated temporal image perception plus robust image-derived lateral velocity directly drives the landing controller;
- `image_aegis_v3`: the exact same image-derived observation is paired with the intentionally imperfect independent reference estimate and assessed by frozen V3 safety logic.

## 8. Phase 6 redundant-fusion adapter

The first direct integration exposed a useful interface mismatch. Historical V3 fusion always gave a usable reference estimate some direct control weight. That was appropriate for the abstract V3 perception stream, but the Phase 6 temporal image track can already be accurate in ordinary frames. Directly blending a noisy reference could therefore make a good image estimate worse even when the safety supervisor never intervened.

`Phase6RedundantFusionAdapter` keeps the original V3 bias estimator and disagreement calculations but changes how redundant evidence is allowed to influence control:

- when an image frame is accepted, image-derived altitude and velocities remain primary;
- persistent cross-estimator evidence can gradually activate lateral bias correction;
- direct reference weight remains small while the image track is healthy;
- when the image pipeline abstains, the independent reference receives substantially more temporary weight;
- frozen `RedundantSafetySupervisorV3` is not modified.

This separates a **perception-interface adaptation** from the historical V3 result rather than silently retuning V3 after seeing Phase 6 data.

## 9. Evaluation outputs

`scripts/run_phase6_image_landing.py` records:

- success / unsafe touchdown / abort / timeout rates,
- 95% Wilson intervals for the outcome rates,
- image abstention rate,
- mean calibrated confidence,
- accepted-frame lateral error,
- Aegis intervention count,
- paired rescue and regression counts,
- calibration reliability and expected calibration error,
- deterministic run metadata and the fitted calibration table.

`scripts/analyze_phase6_failures.py` decomposes unsafe touchdowns into failures of simulated:

- lateral-position tolerance,
- horizontal touchdown-speed tolerance,
- vertical touchdown-speed tolerance.

The categories are not mutually exclusive.

`scripts/run_phase6_selective_perception.py` separately evaluates whether abstention is selective: it measures rejection of truly bad frame estimates and unnecessary rejection of frame estimates that remain inside the calibration tolerances.

## 10. Reproducibility split

Current development defaults are intentionally separate:

- calibration development seed: `616161`
- landing development seed: `626262`
- selective-perception development seed: `636363`

The landing evaluation script rejects identical calibration/evaluation seeds.

A later frozen Phase 6 evaluation must use a new held-out seed that has not guided design, and that result must not be retuned after inspection.

## Safety scope

This remains a synthetic, planar simulation study. It is not a camera calibration system, autopilot, or real-aircraft safety claim.
