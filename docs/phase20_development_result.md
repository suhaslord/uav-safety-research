# Phase 20 development result — PASS

Phase 20 development completed the preregistered 32-context five-factor Shapley attenuation decomposition with no refit and no threshold change.

## Evidence identity

- run: `34013343205`
- artifact: `9983168782`
- artifact digest: `sha256:c89501c7f0886f37a741050ef13d66305844aa71cea887c0ac85a917eb356bc4`
- scientific SHA: `dbb1a4b158deb23084e19f41cdf054c72d8c7853`
- result JSON SHA-256: `d7d5939eea31a0a84b1aa7b309d70e8f398e0a10cc4bde1f518a855807fb8a25`
- seed: `2020201`
- families: `2121–2144`
- verdict: **PASS — all 10 gates**

## Endpoint reproduction

Simple endpoint `small_scale+temporal_dropout`:

- matched transitions: `1357`
- frozen-simple-coefficient RMSE advantage vs Phase 14: `0.0861173240` = **8.61%**
- frozen-simple-coefficient MAE advantage vs Phase 14: `0.1464223408` = **14.64%**
- static lateral coverage delta under latency: `-0.0334961619` = **-3.35 pp**
- static lateral p95 error inflation: `1.4567222197x`

Full hard endpoint `edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout`:

- matched transitions: `1241`
- frozen-simple-coefficient RMSE advantage vs Phase 14: `-0.0551782890` = **5.52% worse**
- frozen-simple-coefficient MAE advantage vs Phase 14: `-0.0419448441` = **4.19% worse**
- static lateral coverage delta under latency: `-0.1077147016` = **-10.77 pp**
- static lateral p95 error inflation: `1.3254975857x`

Endpoint attenuation:

- RMSE: `0.1412956131` = **14.13 pp**
- MAE: `0.1883671848` = **18.84 pp**

## Exact RMSE Shapley attenuation

| Modifier | Contribution |
|---|---:|
| `edge` | **0.0415120979** |
| `oblique` | 0.0273049250 |
| `blur_noise` | 0.0248383738 |
| `low_contrast` | 0.0238434063 |
| `dim` | 0.0237968102 |

Contribution sum equals endpoint attenuation exactly within recorded floating precision; efficiency absolute error is `0.0`.

## Exact MAE Shapley attenuation

| Modifier | Contribution |
|---|---:|
| `edge` | **0.0517748452** |
| `oblique` | 0.0414068464 |
| `dim` | 0.0383441381 |
| `low_contrast` | 0.0304963219 |
| `blur_noise` | 0.0263450332 |

Contribution sum equals endpoint attenuation exactly within recorded floating precision; efficiency absolute error is `0.0`.

`edge` emerged as the largest attenuator on both preregistered distribution-wide statistics. No factor winner was specified before evidence.

## Boundary

This is attribution inside the frozen synthetic generator only. The Shapley values are not physical causal effects.

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`

Transfer is authorized only with the exact frozen implementation and development result above.