# Phase 6B — Calibration Revision After Frozen Phase 6

## Status

Phase 6B is a **post-frozen revision** created after the original Phase 6 held-out audit exposed a weakness in scalar confidence/abstention. It does not replace or retroactively modify the original Phase 6 result.

The historical Phase 6 algorithm was frozen at commit `9cddd41b76302ecc04492ef89fa56de0ea70bc21`. Phase 6B was later frozen and evaluated at executable commit:

`b4e9838555e935a5ec42690495315473629b58f6`

The complete frozen Phase 6B outcome is documented in [`phase6b_results.md`](phase6b_results.md).

## Why Phase 6B was needed

The original frozen Phase 6 landing result was strong at the system level, but its separate selective-perception audit showed that the scalar confidence score rarely rejected bad frame estimates. In particular, blur and mixed degradation could produce inaccurate estimates while the scalar gate continued to accept nearly everything.

The root problem was not simply one bad threshold. Two structural issues were identified:

1. the empirical scalar calibrator could inflate poorly populated confidence bins;
2. one global confidence target forced lateral-position reliability and altitude/scale reliability into the same decision even though those components fail differently.

A first contextual logistic-confidence ablation was tested and retained as a negative result. It still failed to identify many blur altitude errors and over-abstained under mixed degradation, so it was never promoted into the landing architecture.

## Component-specific confidence

Phase 6B separates reliability into:

- `p_x_good`: probability that lateral error is within `0.30 m`;
- `p_z_good`: probability that altitude error is within `0.85 m`.

The image estimator exposes a blur-sensitive sharpness statistic. Sharpness affects confidence only; it does not directly change the measured x/z state.

Synthetic ground truth is used only for offline calibration labels and evaluation. Runtime confidence uses image-derived features.

## Full-domain calibration correction

A pre-freeze high-altitude audit found that the first component-calibration dataset underrepresented the simulator's `5.8–8.0 m` initial-altitude region. Before any Phase 6B held-out landing run, calibration was revised to sample four altitude bands:

- `0.25–2.0 m`
- `2.0–4.0 m`
- `4.0–6.0 m`
- `6.0–8.0 m`

The runtime model is not given the ground-truth altitude band or degradation-condition label.

## Analytic scale observability

Full-domain retraining revealed a more fundamental limit. At high altitude the synthetic landing marker can occupy only a small number of pixels, so two nearby real altitudes can map to adjacent integer marker sizes even when the image looks sharp.

The renderer uses approximately:

`half = int(35 / (z + 0.60))`

and the estimator approximately inverts that scale with:

`z_hat = 35 / apparent_half - 0.60`.

For an inferred half-size `h`, Phase 6B therefore computes the adjacent-bin altitude width:

`delta_z_bin = 35/h - 35/(h+1)`.

Final altitude confidence is capped by:

`p_z_good <= min(1, 0.85 / delta_z_bin)`.

This does **not** change the altitude measurement. It only stops the confidence layer from claiming more precision than the synthetic pixel geometry can resolve. It is deliberately renderer-specific and is not a real-camera uncertainty formula.

## Frozen operating point

The component development benchmark used thresholds:

`0.40, 0.50, 0.60, 0.70, 0.80, 0.90`

The `0.80 / 0.80` lateral/altitude gates were selected from that predeclared risk/coverage grid before Phase 6B landing outcomes were used for evaluation. They were not retuned after development or held-out results.

A separate high-altitude development audit showed that the observability correction materially improved bad-altitude rejection, but residual selected bad-altitude error remained under high-altitude clean/occlusion cases. That limitation was documented rather than tuned away.

## Component-selective fusion

`Phase6BComponentFusionAdapter` composes the existing Phase 6 adapter instead of rewriting frozen V3 safety logic.

When one image component falls below its confidence gate:

- only that component is treated as unreliable;
- an available imperfect reference estimate may temporarily carry that component;
- the other accepted image component remains image-derived;
- if no usable reference exists, confidence is reduced and uncertainty is increased instead of inventing a trusted value.

The frozen V3 supervisor remains unchanged.

## Development history

The first Phase 6B landing development run preceded the full-domain scale-observability correction. It was promising but introduced a mixed regression and a low-light non-success.

After the calibration-domain and observability corrections, the same development seed `626262` was rerun with 30 paired episodes per condition and architecture. Phase 6B achieved:

- clean: 100% success, 0% unsafe;
- blur: 100% success, 0% unsafe;
- low light: 96.7% success, 0% unsafe, one timeout;
- mixed: 96.7% success, 3.3% unsafe;
- occlusion: 96.7% success, 3.3% unsafe.

No landing-outcome-driven retuning followed. The remaining mixed development failure was retained rather than optimized away.

## Frozen held-out outcome

The preregistered held-out seeds were then exposed exactly once:

- landing seed: `868686`
- selective-perception seed: `878787`

The frozen landing study used 100 paired episodes for each of five conditions and three architectures, for **1,500 landing episodes** total.

Phase 6B held-out outcomes were:

- clean: **100% success, 0% unsafe**;
- blur: **100% success, 0% unsafe**;
- low light: **97% success, 0% unsafe, 3% timeout**;
- mixed: **99% success, 1% unsafe**;
- occlusion: **96% success, 4% unsafe**.

On the same paired held-out episodes, mixed degradation improved from `57% success / 43% unsafe` for image-only temporal perception and `94% / 6%` for the established Phase 6 Aegis path to **`99% / 1%` for Phase 6B**.

Occlusion improved from `86% success / 14% unsafe` for image-only and `93% / 7%` for Phase 6 to **`96% / 4%` for Phase 6B**.

The low-light timeout cost is retained as part of the result rather than removed through post-hoc tuning.

## Held-out selective-perception result

The held-out selective audit contained **10,000 synthetic frames**. At the frozen `0.80` altitude gate:

- blur: 20.95% altitude coverage, 0% selected bad-altitude rate, 100% bad-altitude rejection recall;
- low light: 30.55% altitude coverage, 0.16% selected bad-altitude rate, 99.35% bad-altitude rejection recall;
- mixed: 0.85% altitude coverage, 0% selected bad-altitude rate, 100% bad-altitude rejection recall;
- clean and occlusion: full altitude coverage with no bad altitude estimates in those held-out sets.

The main remaining confidence weakness is lateral reliability under mixed degradation. The lateral estimate was usually accurate, but the fixed gate rejected only about 10.5% of bad lateral estimates and retained a selected bad-lateral rate of about 4.0%.

Therefore Phase 6B is **not** presented as a perfect bad-frame detector.

## Seed ledger

All of the following seeds are now considered seen and must not be reused as future held-out evidence:

- `616161` — calibration development
- `626262` — landing development
- `636363` — selective smoke/development
- `646464` — failed contextual-confidence ablation
- `656565` — component calibration benchmark
- `666666` — high-altitude audit
- `747474` — historical frozen Phase 6 landing
- `757575` — historical frozen Phase 6 selective audit
- `868686` — frozen Phase 6B held-out landing
- `878787` — frozen Phase 6B held-out selective-perception audit

Any later algorithm revision must receive a new name and new unseen seeds. Existing future Phase 6C/6D experimental scaffolding has been separated to the `phase6-future-experiments` branch so it cannot be confused with the frozen Phase 6B result.

## Safety scope

All Phase 6 and Phase 6B experiments are synthetic planar simulations. The reference estimate is an imperfect **surrogate simulated secondary sensor**, not a physically implemented navigation system. Nothing here validates a real camera, UAV, autopilot, or flight-safety system.
