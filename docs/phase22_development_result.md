# Phase 22 development result

## Verdict

**PASS — all 10 preregistered development gates passed.**

The exact frozen Phase 22 additive fit candidate transferred to a wholly fresh 32-cell development context cube without refitting.

## Evidence identity

- role: `development`
- seed: `2222221`
- families: `2337–2360`
- workflow run: `34042524414`
- artifact: `9992124923` (`phase22-development`)
- artifact digest: `sha256:978c6efbd52289b7a7b890186c9c9a7d5f1be1e8bd0a628c17b16d4554f494de`
- scientific SHA: `7f739ffccfaa4c075651021949713b852099e14d`
- development result SHA-256: `ef4186021c0af863fc395bdc018b7755d5eaa14e48141d1bf03096edc2a930b8`
- frozen fit candidate SHA-256: `62e75d7b39088c2e66f1cc6be4d180501b79632f2f6847af1fbe0bd96be17551`

## Predictive transfer

RMSE advantage surface:

- cellwise R²: `0.8582832997579948`
- cellwise advantage prediction MAE: `0.009354398114358895`
- cellwise advantage prediction RMSE: `0.011539629320189494`
- stable-sign eligible cells: `16`
- stable-sign accuracy: `1.0`
- observed attenuation: `0.14935935459918237`
- predicted attenuation: `0.12421045489561888`
- attenuation absolute error: `0.025148899703563488`

MAE advantage surface:

- cellwise R²: `0.7864796271064965`
- cellwise advantage prediction MAE: `0.01606529884742199`
- cellwise advantage prediction RMSE: `0.01871363415138637`
- stable-sign eligible cells: `29`
- stable-sign accuracy: `1.0`
- observed attenuation: `0.1956929275205065`
- predicted attenuation: `0.1561377344962271`
- attenuation absolute error: `0.0395551930242794`

## Fresh endpoints

RMSE:

- simple advantage: `0.08987139011290257`
- hard advantage: `-0.0594879644862798`

MAE:

- simple advantage: `0.14514591772153007`
- hard advantage: `-0.05054700979897642`

## Gates

All P22.1–P22.10 passed, including complete fresh paired construction, R² thresholds, prediction-error thresholds, stable-sign transfer, endpoint attenuation transfer, static latency degradation, and zero adaptation.

Transfer remains authorized only with the exact frozen fit candidate. No Phase 22 model coefficient, factor, threshold, or implementation may change.

`simulation_only = true`
`safety_acceptance = false`
`controller_tuning_allowed = false`
