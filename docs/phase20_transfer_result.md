# Phase 20 transfer result — PASS

Phase 20 transfer repeated the exact preregistered 32-context Shapley attenuation study with the frozen implementation and no refit.

## Evidence identity

- run: `34013495480`
- artifact: `9983211994`
- artifact digest: `sha256:4c87f4a8d2801dbb57ac5613ab922d88e86eca22c0bf51e9d4e49e80ec97a843`
- scientific SHA: `9705505ff8122ae513a3b7d740b98cfecd405ff4`
- result JSON SHA-256: `8e600de751547b704efe7e87603d1d9ea2e5df225ce4daee50b2642894bbe27b`
- seed: `2020202`
- families: `2145–2168`
- verdict: **PASS — all 10 gates**

## Endpoint attenuation

- simple endpoint RMSE advantage: `0.1303032909` = **13.03%**
- full endpoint RMSE advantage: `-0.0547572458` = **5.48% worse than Phase 14**
- RMSE endpoint attenuation: `0.1850605368` = **18.51 pp**

- simple endpoint MAE advantage: `0.1693895003` = **16.94%**
- full endpoint MAE advantage: `-0.0553344163` = **5.53% worse than Phase 14**
- MAE endpoint attenuation: `0.2247239167` = **22.47 pp**

## Exact RMSE Shapley attenuation

| Modifier | Contribution |
|---|---:|
| `edge` | **0.0456940395** |
| `blur_noise` | 0.0378183859 |
| `oblique` | 0.0362324155 |
| `low_contrast` | 0.0361281560 |
| `dim` | 0.0291875398 |

Efficiency absolute error: `0.0`.

## Exact MAE Shapley attenuation

| Modifier | Contribution |
|---|---:|
| `edge` | **0.0528586609** |
| `oblique` | 0.0461572255 |
| `blur_noise` | 0.0434075738 |
| `low_contrast` | 0.0420290662 |
| `dim` | 0.0402713901 |

Efficiency absolute error: `0.0`.

`edge` is again the largest attenuator on both distribution-wide statistics. This repeated ranking is descriptive; it was not added as a new gate after development.

## Boundary

This remains a simulation-only synthetic-context attribution result. Static latency degradation remains required by the preregistration; no controller or interval changed.

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`

Protected validation is authorized only with this exact frozen transfer result and the unchanged Phase 20 scientific implementation.