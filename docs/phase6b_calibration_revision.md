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

## Phase 6B component confidence

Phase 6B separates image reliability into two calibrated components:

- `p_x_good`: probability that lateral error is within 0.30 m;
- `p_z_good`: probability that altitude error is within 0.85 m.

The image estimator exposes a blur-sensitive sharpness statistic. Sharpness is used only as a confidence feature; it does not directly change the x/z measurement.

The component models use runtime image-derived features only. Synthetic ground truth is used during offline calibration fitting and evaluation labels, not during a landing episode.

## Full-domain calibration correction

A pre-freeze high-altitude audit found that the first Phase 6B calibration dataset underrepresented the simulator's 5.8–8.0 m initial altitude region. The calibration dataset was therefore revised **before held-out Phase 6B evaluation** to use condition-balanced samples stratified across four altitude bands:

- 0.25–2.0 m;
- 2.0–4.0 m;
- 4.0–6.0 m;
- 6.0–8.0 m.

The runtime feature set still receives no ground-truth altitude band or degradation-condition label.

Full-domain training alone did not solve the high-altitude problem. Clean and occlusion frames could look sharp and geometrically valid while apparent marker scale was too coarse to resolve the 0.85 m altitude tolerance.

## Analytic scale observability

The Phase 6 renderer quantizes apparent marker half-size using approximately:

`half = int(35 / (z + 0.60))`

while the estimator approximately inverts scale using:

`z_hat = 35 / apparent_half - 0.60`.

At small apparent sizes, one adjacent integer scale bin can span more than the altitude-accuracy target. For an inferred half-size `h`, Phase 6B therefore computes the synthetic scale-bin width:

`delta_z_bin = 35/h - 35/(h+1)`.

This quantity is added as an interpretable confidence feature. Final altitude confidence is additionally capped by:

`p_z_good <= min(1, 0.85 / delta_z_bin)`.

The cap does not change the altitude measurement. It prevents a confidence model from claiming greater reliability than the synthetic pixel geometry can resolve. This is deliberately simulation-specific and is not a real-camera uncertainty formula.

## Development-only component benchmark

The calibration-development benchmark uses:

- benchmark seed: `656565`
- calibration seed: `616161`
- 2,000 frames per image condition
- fixed risk/coverage thresholds: 0.40, 0.50, 0.60, 0.70, 0.80, 0.90

The 0.80 lateral and altitude gates were selected from that predeclared grid **before any Phase 6B landing outcome was run** and were not changed by later audits.

With the full-domain, scale-observability revision, the fixed 0.80 operating point produced:

- clean: 100% lateral and altitude coverage with 0% selected bad estimates in the normal sequence benchmark;
- blur: 100% lateral coverage with 0% lateral failures; 18.7% altitude coverage with 0% selected bad altitude estimates and 100% bad-altitude rejection recall;
- low light: 100% lateral coverage; 30.25% altitude coverage, 0.165% selected bad altitude rate, and 99.42% bad-altitude rejection recall;
- mixed: 94.75% lateral coverage with 5.33% selected lateral bad rate; 0.90% altitude coverage with 0% selected bad altitude estimates and 100% bad-altitude rejection recall;
- occlusion: 100% lateral and altitude coverage, 0.65% selected lateral bad rate, and 0% selected altitude bad rate in the normal sequence benchmark.

Calibration is not perfect. Report calibration error and risk/coverage together rather than presenting the probabilities as exact guarantees.

## High-altitude stress audit

A separate development-only audit uses seed `666666` and restricts synthetic frames to 5.8–8.0 m.

Before the analytic observability correction, bad-altitude rejection recall was 0% for both clean and occlusion high-altitude frames. After the scale-observability revision, at the same fixed 0.80 gate:

- clean: 25.75% altitude coverage, 11.65% selected bad altitude rate, 86.52% bad-altitude rejection recall;
- occlusion: 31.0% altitude coverage, 12.10% selected bad altitude rate, 81.71% bad-altitude rejection recall;
- blur, low light, and mixed: 0% high-altitude altitude coverage and 100% bad-altitude rejection recall in this audit;
- lateral coverage remains approximately 100% across all five conditions, with zero selected lateral failures in this high-altitude audit.

The residual ~12% selected bad-altitude rate for clean/occlusion high-altitude frames is a documented limitation rather than something hidden by further threshold tuning.

## Aegis integration rule

`Phase6BComponentFusionAdapter` composes the existing Phase 6 adapter rather than rewriting frozen V3 logic.

When a component is above its fixed confidence threshold, the established Phase 6 control estimate remains unchanged. When one component falls below threshold:

- only that component is marked unreliable;
- an available independent reference estimate may temporarily carry that component;
- the other accepted image component remains image-derived;
- if no usable reference exists, confidence is reduced and uncertainty is increased instead of inventing a trusted value.

The frozen V3 safety supervisor remains unchanged.

## Development landing history

The first 30-episode-per-cell Phase 6B development run preceded the full-domain scale-observability correction. It reached 96.7% success in both mixed and occlusion conditions, but introduced one mixed regression relative to the established Phase 6 Aegis path and one low-light non-success. That run remains development evidence and is not the Phase 6B frozen result.

The corrected full-domain scale-observability revision was then rerun on the same development seed `626262`, with 30 paired episodes per condition and architecture. The fixed `0.80 / 0.80` component gates were unchanged.

Corrected Phase 6B development outcomes were:

- clean: **100% success, 0% unsafe touchdown**;
- blur: **100% success, 0% unsafe touchdown**;
- low light: **96.7% success, 0% unsafe touchdown**, with one timeout;
- mixed: **96.7% success, 3.3% unsafe touchdown**;
- occlusion: **96.7% success, 3.3% unsafe touchdown**.

Against image-only temporal perception, Phase 6B improved mixed success by 40 percentage points and reduced mixed unsafe touchdowns by 40 percentage points; it improved occlusion success by 16.7 points and reduced unsafe touchdowns by 16.7 points.

Against the established Phase 6 Aegis path on this small development set, Phase 6B matched blur, clean, and occlusion outcome rates, while showing one low-light timeout and one mixed unsafe regression. The mixed failure was a vertical touchdown-speed miss of about `0.815 m/s` against the frozen `0.80 m/s` limit; lateral position and horizontal speed were within limits. This result is preserved rather than tuned away.

The component layer also behaved as an actual abstaining perception system. For example, in mixed degradation the mean altitude-component abstention rate was about 70.9%, with the independent reference taking over the rejected altitude component on most of those frames. In blur the altitude-component abstention rate was about 56.8%. The established Phase 6 scalar confidence layer did not provide comparable selective behavior.

These development results are considered technically stable enough to freeze because the component calibration now exposes the intended uncertainty behavior, the architecture remains strong relative to image-only perception, all tests pass, and no further landing-outcome-driven tuning is justified before the preregistered held-out evaluation.

## Seed ledger

The following seeds are now considered **seen** and must not be used as final Phase 6B validation seeds:

- `616161` — calibration development
- `626262` — Phase 6 / Phase 6B landing development
- `636363` — Phase 6 selective smoke/development use
- `646464` — failed contextual-confidence ablation
- `656565` — Phase 6B component calibration benchmark
- `666666` — Phase 6B high-altitude audit
- `747474` — historical frozen Phase 6 landing
- `757575` — historical frozen Phase 6 selective-perception audit

Already preregistered and still unused for Phase 6B final validation:

- `868686` — held-out landing seed
- `878787` — held-out selective-perception seed

Any future Phase 6B algorithm change after those held-out seeds are run must become a new named revision with new held-out seeds.

## Safety scope

All results in Phase 6 and Phase 6B are from a synthetic planar simulation with a synthetic image renderer. They are research diagnostics for perception uncertainty and supervisory logic, not validation for a physical aircraft, camera system, or autopilot.
