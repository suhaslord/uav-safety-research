# Phase 20 final report — Five-Factor Context Attenuation Shapley Decomposition

## Final status

**PASS — development, transfer, protected validation, and final holdout each passed all 10 preregistered Phase 20 gates.**

Phase 20 is scientifically closed. No rerun, refit, factor-set change, threshold change, context deletion, or controller/interval change is authorized.

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`

## Scientific question

Phase 20 asked whether the reproducible simple→hard loss of the frozen simple-context latency coefficient's distribution-wide residual advantage could be exactly attributed across the five predefined synthetic modifiers separating those contexts:

1. `edge`
2. `oblique`
3. `dim`
4. `blur_noise`
5. `low_contrast`

The study evaluated the complete `2^5 = 32` context power set at every evidence role and computed exact Shapley attenuation on both RMSE and MAE. No factor winner was preregistered.

q90 remained descriptive only and never entered a Phase 20 gate.

## Frozen predecessor identities

- Phase 12 candidate: `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`
- Phase 14 bridge: `0443d4e45a1966c77544c5c9965de8caec6e622c79ef8c2ce47aee82a3c95981`
- Phase 17 fit candidate: `2ca52a418f5616e0e83ef84d0c9238ee429260cd4de7a553356b0c1bba44d8e0`
- Phase 19 final result: `8c23b9b9c8c9fb2f9146bf739e52074f8709d2fe9a81c794e64fb43f360acebf`

The Phase 19 object itself preserved the immutable Phase 18 protected-validation failure and the descriptive-only q90 boundary.

## Sequential evidence identity

| Role | Seed | Families | Run | Artifact | Result SHA-256 | Verdict |
|---|---:|---|---:|---:|---|---|
| development | `2020201` | `2121–2144` | `34013343205` | `9983168782` | `d7d5939eea31a0a84b1aa7b309d70e8f398e0a10cc4bde1f518a855807fb8a25` | **PASS** |
| transfer | `2020202` | `2145–2168` | `34013495480` | `9983211994` | `8e600de751547b704efe7e87603d1d9ea2e5df225ce4daee50b2642894bbe27b` | **PASS** |
| protected | `2020203` | `2169–2192` | `34013640844` | `9983246993` | `f6f1d9f8fe41f227467ae73ccf472346ee44edda90c79326c749bffc481acf88` | **PASS** |
| final | `2020204` | `2193–2216` | `34013829943` | `9983311430` | `f2a0cf4e1cf0765c3194025eb29072f9663f27e3cdd13b0594cde4643f33934e` | **PASS** |

Final artifact digest:

`sha256:d77bc71d4c99caedba582a116fbd1fcb8cc533ed6ce47ff4ae90ded3444ad338`

Final scientific SHA:

`e71b06838b8fc33eb80fa1ff9c8c7ce4603c005e`

## Endpoint attenuation across all four evidence roles

The primary quantity is the loss of the frozen simple-context coefficient's advantage relative to frozen Phase 14 when moving from the simple endpoint to the full hard endpoint.

| Role | Simple RMSE advantage | Full RMSE advantage | RMSE attenuation | Simple MAE advantage | Full MAE advantage | MAE attenuation |
|---|---:|---:|---:|---:|---:|---:|
| development | 8.61% | -5.52% | **14.13 pp** | 14.64% | -4.19% | **18.84 pp** |
| transfer | 13.03% | -5.48% | **18.51 pp** | 16.94% | -5.53% | **22.47 pp** |
| protected | 8.09% | -6.57% | **14.66 pp** | 13.85% | -5.58% | **19.43 pp** |
| final | 8.90% | -5.87% | **14.77 pp** | 15.20% | -5.25% | **20.45 pp** |

The attenuation therefore reproduced on both distribution-wide statistics at every sequential evidence role.

## Final holdout details

Simple endpoint `small_scale+temporal_dropout`:

- matched transitions: `1335`
- frozen-simple-coefficient RMSE advantage vs Phase 14: `0.0890248848` = **8.90%**
- frozen-simple-coefficient MAE advantage vs Phase 14: `0.1519678299` = **15.20%**
- static lateral coverage delta under latency: `-0.0404181185` = **-4.04 pp**
- static lateral p95 absolute-error inflation: `1.4554579237x`

Full hard endpoint `edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout`:

- matched transitions: `1157`
- frozen-simple-coefficient RMSE advantage vs Phase 14: `-0.0586552472` = **5.87% worse**
- frozen-simple-coefficient MAE advantage vs Phase 14: `-0.0525064826` = **5.25% worse**
- static lateral coverage delta under latency: `-0.1080882353` = **-10.81 pp**
- static lateral p95 absolute-error inflation: `1.3396302090x`

Final endpoint attenuation:

- RMSE: `0.1476801319` = **14.77 pp**
- MAE: `0.2044743125` = **20.45 pp**

The frozen coefficient-context crossover gate also passed: the frozen simple coefficient outperformed the frozen hard coefficient at the simple endpoint on both RMSE and MAE, while the frozen hard coefficient outperformed the frozen simple coefficient at the hard endpoint on both statistics.

## Final exact RMSE Shapley attribution

| Modifier | Contribution to attenuation |
|---|---:|
| `edge` | **0.0361434870** |
| `oblique` | 0.0317800205 |
| `blur_noise` | 0.0279624689 |
| `low_contrast` | 0.0272772895 |
| `dim` | 0.0245168660 |

Contribution sum: `0.1476801319`

Endpoint attenuation: `0.1476801319`

Shapley efficiency absolute error: `0.0`

## Final exact MAE Shapley attribution

| Modifier | Contribution to attenuation |
|---|---:|
| `edge` | **0.0477413095** |
| `oblique` | 0.0416285666 |
| `low_contrast` | 0.0401687590 |
| `blur_noise` | 0.0385224525 |
| `dim` | 0.0364132249 |

Contribution sum: `0.2044743125`

Endpoint attenuation: `0.2044743125`

Shapley efficiency absolute error: `0.0`

## Cross-stage attribution interpretation

All five modifiers made positive attenuation contributions on the recorded Phase 20 evidence. The contributions are distributed rather than collapsing onto a single factor.

`edge` was the largest contributor for both statistics in development and transfer, and again for both statistics in final. On protected validation, however, `oblique` narrowly exceeded `edge` on RMSE while `edge` remained largest on MAE.

Therefore Phase 20 **does not establish a universally dominant single modifier**. The stronger supported statement is that the reproducible simple→hard loss of distribution-wide residual advantage is jointly attributable across the five predefined synthetic modifiers, with the relative ranking showing some evidence-partition/statistic dependence.

## Supported conclusion

> Across fresh development, transfer, protected, and final matched synthetic factorial evidence, the simple-to-hard loss of distribution-wide one-step lateral residual advantage of the frozen simple-context latency coefficient was reproducible on RMSE and MAE and was exactly allocatable across the five predefined synthetic context modifiers using the complete 32-context Shapley decomposition. Contributions were distributed across multiple modifiers; no single modifier was established as universally dominant.

This is attribution inside the frozen synthetic generator only. The Shapley values are not physical causal effects.

The result does **not** mean latency is beneficial: absolute level error under pure two-frame latency continued to worsen at both endpoints, and Phase 12 interval widths were unchanged.

No physical-flight safety, physical latency causality, real-sensor equivalence, full-simulator invariance, certification relevance, controller improvement, production readiness, or operational-safety claim is authorized.