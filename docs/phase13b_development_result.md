# Phase 13B development result — Thirteen Paired Degradation Audit

## Verdict

**FAIL — the Phase 13B lineage closes at development.**

This is a valid scientific failure, not an execution failure.

The development workflow completed all pre-evidence invariants, recovered and verified the exact frozen Phase 12 Iteration 3 candidate, generated the fresh Phase 13B development evidence exactly once, verified the result boundary, and uploaded the permanent artifact.

No Phase 13B transfer, protected, or final evidence is authorized after this result.

## Canonical evidence identity

- workflow run: `34009257268`
- artifact: `9981955020`
- artifact digest: `sha256:c3b0ff89f6efa852ec4b8bdb11f2b8a0ab02ce778c60eeb07ff705c4b2f6facb`
- development scientific Git SHA: `aeee9a44732b45536954d50547c7825b19a2f916`
- development seed: `1313131`
- families: `1297–1320`
- result JSON SHA-256: `6dc4decba2c5f4e22cb829e56abffc161cf6837454a6f7efa5f32b42641a4b93`
- frozen Phase 12 candidate SHA-256: `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`

The earlier run `34009210942` did not recover the candidate or generate evidence. Its 56 tests passed, then a self-referential workflow grep failed before evidence exposure. Seed `1313131` was not generated or scored in that run, so the canonical exposure remained the single successful evidence generation in run `34009257268`.

## Phase 13B gates

| Gate | Result | Key value |
|---|---|---|
| G13B.1 paired construction integrity | **PASS** | 13 / 13 domains |
| G13B.2 no catastrophic shifted domain | **PASS** | 13 / 13 domains above 80% on both axes |
| G13B.3 bounded paired coverage degradation | **FAIL** | 12 / 13 domains |
| G13B.4 rescue honesty floor | **PASS** | lateral 86.10%, altitude 91.39% |
| G13B.5 reliability mechanism survives | **PASS** | Spearman `0.3534324544` |
| G13B.6 compound domain stands alone | **FAIL** | paired degradation failure |
| G13B.7 zero adaptation | **PASS** | no candidate/stress/calibration/threshold change |

`phase13b_pass = false`

## Main finding

The paired design successfully removed the ambiguity that limited Phase 13A.

For every domain, the no-shift control and shifted copy had:

- identical row counts;
- identical truth-visible counts;
- identical useful availability;
- identical lateral truth;
- identical altitude truth.

Therefore the Phase 13B coverage deltas can be attributed to the frozen stress overlay within each paired base event.

Twelve of the thirteen domains stayed within the locked maximum paired coverage loss of eight percentage points.

The single exception was again the thirteenth domain:

`latency_wind_calibration_compound`

### Domain 13 matched result

| Metric | Control | Shifted | Change |
|---|---:|---:|---:|
| lateral 95% coverage | `0.9487554905` | `0.8323572474` | **`-0.1163982430`** |
| altitude 95% coverage | `0.9502196193` | `0.9099560761` | `-0.0402635432` |
| lateral p95 error | `0.2155084611 m` | `0.3044707643 m` | **`1.4128019049x`** |
| altitude p95 error | `0.4175414048 m` | `0.4684944347 m` | `1.1220310831x` |
| useful availability | `0.9486111111` | `0.9486111111` | unchanged |

The lateral shifted coverage remained above the inherited catastrophic floor (`0.80`) but exceeded the preregistered paired-loss allowance (`-0.08`).

This is a local compound-interaction failure, not an aggregate collapse.

## All thirteen lateral paired effects

Ordered from largest loss to largest improvement:

| Domain | Control coverage | Shifted coverage | Delta | p95 error inflation |
|---|---:|---:|---:|---:|
| latency_wind_calibration_compound | 94.88% | 83.24% | **-11.64 pp** | **1.413x** |
| fixed_latency_2f | 99.72% | 96.79% | -2.93 pp | 1.417x |
| dynamics_gain_mismatch | 96.56% | 95.43% | -1.12 pp | 1.300x |
| jittered_latency_0_4f | 97.01% | 95.96% | -1.04 pp | 1.177x |
| burst_staleness_5f | 98.26% | 97.63% | -0.63 pp | 1.133x |
| lateral_wind_drift | 98.19% | 97.77% | -0.42 pp | 0.984x |
| camera_scale_miscalibration | 97.35% | 97.21% | -0.14 pp | 1.120x |
| lateral_sensor_bias | 98.25% | 98.25% | 0.00 pp | 1.053x |
| correlated_measurement_noise | 98.68% | 98.81% | +0.14 pp | 1.104x |
| heavy_tail_measurement_noise | 98.39% | 98.53% | +0.14 pp | 1.006x |
| oscillatory_drift | 97.91% | 98.33% | +0.42 pp | 1.019x |
| reacquisition_shock | 98.04% | 98.53% | +0.49 pp | 1.011x |
| vertical_gust | 96.86% | 97.56% | +0.70 pp | 1.000x |

The next-largest lateral coverage loss after the compound domain was only `-2.93 pp`. This strongly motivates a fresh interaction-attribution study rather than modifying the frozen uncertainty model.

## Reliability and rescue findings

The Phase 12 innovation mechanism remained directionally informative under Phase 13B:

- continuity normalized-anchor-innovation / lateral-error Spearman: `0.3534324544`
- locked floor: `0.20`
- verdict: **PASS**

Aggregate shifted rescue rows also stayed above the inherited catastrophic honesty floor:

- rescue rows: `2763`
- lateral 95% coverage: `0.8610206298`
- altitude 95% coverage: `0.9138617445`
- verdict: **PASS**

This means the Phase 13B failure should not be summarized as a broad collapse of every uncertainty mechanism. It is concentrated in one difficult compound condition.

## Evidence boundary

The following Phase 13B evidence remains unexposed and is now prohibited for this lineage:

- transfer seed `1313132`
- protected seed `1313133`
- final seed `1313134`

No model, stress magnitude, interval multiplier, calibration rule, or threshold will be changed to make Phase 13B pass.

Any follow-up must have a new scientific identity and fresh evidence.

## Next scientific question

Phase 13B establishes that the thirteenth compound overlay causes a reproducible paired lateral-coverage degradation larger than any isolated Phase 13B domain effect on its own base distribution.

The next question is therefore attribution, not remediation:

> Which constituent mechanisms of the frozen thirteenth compound overlay create the interaction that drives the lateral coverage loss on the same hard base domain?

A separate Phase 13C should decompose the compound overlay using fresh evidence and preregistered component contrasts before any result is generated.

## Claim boundary

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`

Supported claim:

> In the preregistered Phase 13B synthetic paired-degradation study, twelve of thirteen domains stayed within the locked paired coverage-loss bound, while the thirteenth compound domain produced an 11.64 percentage-point lateral coverage loss relative to its matched control; the result remained simulation-only and did not establish physical UAV safety.
