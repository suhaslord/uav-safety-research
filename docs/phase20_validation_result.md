# Phase 20 protected validation result — PASS

Phase 20 protected validation repeated the exact 32-context factorial/Shapley study with the frozen implementation and no refit.

## Evidence identity

- run: `34013640844`
- artifact: `9983246993`
- artifact digest: `sha256:61fb3b307b78631dfbaae59fe8ee181ac0feedf0077cda7963d04c3e2e659bf2`
- scientific SHA: `4c9afcac47b6269af50b5bcc6d664c550814f23e`
- result JSON SHA-256: `f6f1d9f8fe41f227467ae73ccf472346ee44edda90c79326c749bffc481acf88`
- seed: `2020203`
- families: `2169–2192`
- verdict: **PASS — all 10 gates**

## Endpoint attenuation

- simple endpoint RMSE advantage: `0.0808711972` = **8.09%**
- full endpoint RMSE advantage: `-0.0657387797` = **6.57% worse than Phase 14**
- RMSE endpoint attenuation: `0.1466099770` = **14.66 pp**

- simple endpoint MAE advantage: `0.1384829505` = **13.85%**
- full endpoint MAE advantage: `-0.0558256851` = **5.58% worse than Phase 14**
- MAE endpoint attenuation: `0.1943086356` = **19.43 pp**

## Exact RMSE Shapley attenuation

| Modifier | Contribution |
|---|---:|
| `oblique` | **0.0329913109** |
| `edge` | 0.0315812271 |
| `dim` | 0.0299761405 |
| `blur_noise` | 0.0290831515 |
| `low_contrast` | 0.0229781469 |

Efficiency absolute error: `0.0`.

## Exact MAE Shapley attenuation

| Modifier | Contribution |
|---|---:|
| `edge` | **0.0467441142** |
| `dim` | 0.0415791123 |
| `oblique` | 0.0403028594 |
| `blur_noise` | 0.0344087468 |
| `low_contrast` | 0.0312738030 |

Efficiency absolute error: `0.0`.

The largest contributor is not identical across the two statistics on protected evidence: `oblique` is largest for RMSE, while `edge` remains largest for MAE. No winner-stability gate was preregistered, so this is preserved as evidence rather than tuned away.

## Boundary

Protected validation supports stable endpoint attenuation and exact factor allocation, not a claim that one modifier is universally dominant.

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`

Final holdout is authorized only with this exact frozen protected result and the unchanged Phase 20 scientific implementation.