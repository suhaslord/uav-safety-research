# Phase 6B — Calibration Revision After the Frozen Phase 6 Audit

## Status

Phase 6B is a **post-frozen revision**. It does not replace or retroactively modify the original Phase 6 held-out result.

The historical Phase 6 algorithm was frozen at commit `9cddd41b76302ecc04492ef89fa56de0ea70bc21` and evaluated before the Phase 6B calibration work began.

## Historical frozen Phase 6 result

The original frozen landing evaluation used:

- landing seed: `747474`
- selective-perception seed: `757575`
- calibration seed: `616161`
- 100 landing episodes per condition/architecture cell

Its Aegis landing result was strong under the hardest synthetic image conditions:

- mixed: 92% success, 7% unsafe touchdown, 1% safe abort;
- occlusion: 96% success, 4% unsafe touchdown.

However, the separately frozen selective-perception audit revealed that the scalar confidence/abstention system was not actually rejecting many bad frame estimates:

- blur raw bad-frame rate: 48.05%, bad-frame abstention recall: 0%;
- mixed raw bad-frame rate: 71.80%, bad-frame abstention recall: about 2.16%.

Therefore the landing result remains valid for the frozen architecture, but it is not evidence that the original scalar confidence estimator was a strong selective predictor.

## Root cause

The original empirical scalar calibrator discretized raw confidence into fixed bins. Empty bins were filled with the global success probability and the final probability table was forced to be monotone. In this dataset, that inflated low-confidence bins enough that the runtime confidence threshold almost never triggered.

A second limitation was more fundamental: a single confidence score forced lateral-position reliability and altitude/scale reliability into the same target. Frame-level analysis showed that blur frequently preserved an accurate landing-pad centroid while corrupting apparent scale enough to make altitude inaccurate.

## Failed intermediate ablation

A first multifeature contextual logistic calibrator was tested before Phase 6B. It is retained as an ablation rather than hidden or overwritten.

That model:

- still failed to identify many blur altitude errors;
- over-abstained on mixed degradation, reaching 100% frame abstention in the development ablation.

It was rejected and was never promoted into the Aegis landing architecture.

## Phase 6B change

Phase 6B separates image reliability into two calibrated components:

- `p_x_good`: probability that lateral error is within 0.30 m;
- `p_z_good`: probability that altitude error is within 0.85 m.

The image estimator also exposes a blur-sensitive sharpness statistic. Sharpness is used only as an observable confidence feature; it does not directly change the x/z measurement.

The component models use runtime image-derived features only. Synthetic ground truth is used during offline calibration fitting and evaluation labels, not during a landing episode.

## Development-only component benchmark

The Phase 6B calibration-development benchmark used:

- benchmark seed: `656565`
- calibration seed: `616161`
- 2,000 frames per image condition
- fixed risk/coverage thresholds: 0.40, 0.50, 0.60, 0.70, 0.80, 0.90

The 0.80 lateral and altitude gates were selected from that predeclared grid **before any Phase 6B landing outcome was run**.

At threshold 0.80 in the development benchmark:

- clean: 100% lateral and altitude coverage with no selected bad estimates;
- blur: 100% lateral coverage with no lateral failures; altitude retained 18.7% coverage and rejected 100% of bad altitude estimates;
- low light: 100% lateral coverage; altitude coverage 69.55%, with 52.02% bad-altitude rejection recall;
- mixed: lateral coverage 87.85%; altitude coverage 10.30%, with 97.34% bad-altitude rejection recall;
- occlusion: 100% lateral and altitude coverage, with 0.65% selected lateral bad rate and zero altitude failures in this benchmark.

Calibration is not perfect. Altitude ECE remained larger under blur and mixed degradation, so Phase 6B reporting must include calibration error and risk/coverage rather than presenting probabilities as perfectly calibrated.

## Aegis integration rule

`Phase6BComponentFusionAdapter` composes the existing Phase 6 adapter rather than rewriting frozen V3 logic.

When a component is above its fixed confidence threshold, the established Phase 6 control estimate remains unchanged. When one component falls below threshold:

- only that component is marked unreliable;
- an available independent reference estimate may temporarily carry that component;
- the other accepted image component remains image-derived;
- if no usable reference exists, confidence is reduced and uncertainty is increased instead of inventing a trusted value.

The frozen V3 safety supervisor remains unchanged.

## Seed ledger

The following seeds are now considered **seen** and must not be used as final Phase 6B validation seeds:

- `616161` — calibration development
- `626262` — Phase 6 / Phase 6B landing development
- `636363` — Phase 6 selective smoke/development use
- `646464` — failed contextual-confidence ablation
- `656565` — Phase 6B component calibration benchmark
- `747474` — historical frozen Phase 6 landing
- `757575` — historical frozen Phase 6 selective-perception audit

A future Phase 6B frozen evaluation must declare new landing and selective-calibration audit seeds before running and must not tune the architecture after observing those results.

## Safety scope

All results in Phase 6 and Phase 6B are from a synthetic planar simulation with a synthetic image renderer. They are research diagnostics for perception uncertainty and supervisory logic, not validation for a physical aircraft, camera system, or autopilot.
