# Phase 6B Held-Out Evaluation Protocol

## Status

**Completed exactly once.** This protocol was written and amended during development before either Phase 6B held-out seed was exposed. The final held-out evaluation subsequently ran without changing the frozen `0.80 / 0.80` component gates or the Phase 6B algorithm.

Final result: [`phase6b_results.md`](phase6b_results.md)

Frozen executable commit: `b4e9838555e935a5ec42690495315473629b58f6`

Frozen GitHub Actions run: `31355377934`

## Purpose

Phase 6B is a post-frozen revision motivated by the original Phase 6 selective-confidence audit. Its purpose is to test whether separate lateral/altitude confidence and component-wise redundant substitution improve degraded synthetic image landing without retroactively modifying the historical Phase 6 result.

## Frozen operating choices

The following choices were fixed before held-out evaluation:

- lateral component confidence threshold: `0.80`
- altitude component confidence threshold: `0.80`
- temporal calibration seed: `616161`
- component calibration seed: `616161`
- temporal calibration samples per condition: `180`
- component calibration samples per condition: `280`
- synthetic image severity: `1.0`
- frozen V3 safety supervisor: unchanged
- paired episode seeds within each condition: yes
- Phase 6 renderer, temporal tracker, robust velocity filter, controller, dynamics, wind process, and independent surrogate reference estimator: unchanged except for the explicitly documented Phase 6B confidence/fusion layer

The `0.80 / 0.80` gates were chosen from a predeclared development risk/coverage grid rather than from final landing outcomes.

## Pre-freeze development amendment

Before any Phase 6B held-out run, high-altitude development auditing found that the first component-calibration dataset underrepresented the simulator's `5.8–8.0 m` initial-altitude region. Calibration was corrected to cover four altitude bands spanning `0.25–8.0 m`.

Full-domain calibration then exposed a second issue: the synthetic renderer quantizes apparent landing-marker size to integer pixels. At high altitude, one adjacent marker-size bin can represent more altitude difference than the `0.85 m` altitude-accuracy target.

Before held-out evaluation, Phase 6B therefore added a simulation-specific scale-observability ceiling:

`delta_z_bin = 35/h - 35/(h+1)`

`p_z_good <= min(1, 0.85 / delta_z_bin)`

This correction does not alter the measured altitude. It only limits reported altitude confidence when the synthetic pixel scale cannot support the target precision. The `0.80 / 0.80` operating gates were not changed.

## Development-only seeds

The following seeds were used during development and were excluded from final validation:

- `616161` — calibration development
- `626262` — paired landing development
- `636363` — selective smoke/development
- `646464` — failed contextual-confidence ablation
- `656565` — component confidence benchmark
- `666666` — high-altitude calibration/observability audit
- `747474` — historical frozen Phase 6 landing
- `757575` — historical frozen Phase 6 selective audit

## Preregistered held-out landing study

Held-out landing seed: `868686`

For each condition:

- clean
- blur
- low_light
- occlusion
- mixed

run 100 paired episodes for each architecture:

1. `image_temporal`
2. `image_aegis_v3`
3. `image_aegis_phase6b`

Total: **1,500 simulated landing episodes**.

Primary outcomes:

- success rate
- unsafe touchdown rate
- safe abort rate
- timeout rate
- 95% Wilson intervals

Paired outcomes include rescue/regression counts between architectures. Touchdown failures are decomposed into lateral position, horizontal speed, and vertical speed violations. Phase 6B component abstention and reference-takeover behavior are also recorded.

## Preregistered held-out selective-perception audit

Held-out selective seed: `878787`

Generate 20 sequences × 100 frames for each of the five image conditions: **10,000 synthetic frames total**.

At the fixed `0.80 / 0.80` component gates, report separately for lateral and altitude:

- coverage
- selected bad-estimate rate
- bad-estimate rejection recall
- calibration ECE

The full predeclared threshold grid remains diagnostic only; the primary `0.80 / 0.80` operating point cannot be changed after viewing held-out results.

## Interpretation commitment

The held-out result was allowed to be positive, neutral, or negative. A negative result was not grounds to select a new seed or retune the same revision.

Any later algorithm change must become a new named revision with new unseen seeds.

## Execution record

The frozen workflow first ran a preflight test suite and recorded the exact source SHA. **53 tests passed** before the held-out jobs began.

The two preregistered seeds were then exposed once:

- `868686` — landing study completed successfully
- `878787` — selective-perception audit completed successfully

No Phase 6B parameter or algorithm change was made after these results were observed.

Frozen artifacts:

- landing artifact ID `9051147608`, SHA-256 `ca175ae7906e84fdf2dffe95d2e56ebc6fb5e2334ed94d8c7bbc479276d321bf`
- selective artifact ID `9050458293`, SHA-256 `679a75e0d139c8cdb462d61c3bd8cf936d8234a45e10aa690ba301ae414e852c`

The artifacts are permanently archived under:

- [`../results/phase6b_frozen_landing/`](../results/phase6b_frozen_landing/)
- [`../results/phase6b_frozen_selective/`](../results/phase6b_frozen_selective/)

## Safety scope

All Phase 6B experiments are synthetic planar simulation studies. The independent reference is a surrogate simulated secondary sensor, not a physically implemented navigation system. This protocol does not validate a real camera, physical UAV, autopilot, or operational flight-safety system.
