# Phase 22 transfer result

## Verdict

**PASS — all 10 preregistered transfer gates passed.**

The exact frozen Phase 22 additive fit candidate transferred to a second wholly fresh 32-cell context cube without refitting.

## Evidence identity

- role: `transfer`
- seed: `2222222`
- families: `2361–2384`
- workflow run: `34042700363`
- artifact: `9992184175` (`phase22-transfer`)
- artifact digest: `sha256:57b70571413339f67c1263ef53118b8ebce9fbe4e4ae30bd3ab368d0422f0d3a`
- scientific SHA: `5a4acab87796dbbf36fdef85101b84f45c5717b9`
- transfer result SHA-256: `af8d9f5f95e1e86a550cc98a9f40e27548279e89c3b969f8f78db2cd51d115ab`
- frozen fit candidate SHA-256: `62e75d7b39088c2e66f1cc6be4d180501b79632f2f6847af1fbe0bd96be17551`

## Predictive transfer

RMSE advantage surface:

- cellwise R²: `0.8460055914085471`
- cellwise advantage prediction MAE: `0.009431808321962904`
- prediction RMSE: `0.014181312403974966`
- stable-sign eligible cells: `15`
- stable-sign accuracy: `1.0`
- observed attenuation: `0.18375606371692144`
- predicted attenuation: `0.12421045489561888`
- attenuation absolute error: `0.059545608821302554`

MAE advantage surface:

- cellwise R²: `0.8150148367214042`
- cellwise advantage prediction MAE: `0.013894753656916366`
- prediction RMSE: `0.017851105164880317`
- stable-sign eligible cells: `27`
- stable-sign accuracy: `1.0`
- observed attenuation: `0.21390205151171093`
- predicted attenuation: `0.1561377344962271`
- attenuation absolute error: `0.057764317015483846`

## Fresh endpoints

RMSE:

- simple advantage: `0.1182304232117003`
- hard advantage: `-0.06552564050522114`

MAE:

- simple advantage: `0.1636079614336421`
- hard advantage: `-0.05029409007806884`

## Gates

All P22.1–P22.10 passed. Protected validation is authorized with the exact frozen candidate and unchanged thresholds.

The transfer attenuation errors remain below the preregistered `0.07` limit but are not treated as evidence for changing that limit.

`simulation_only = true`
`safety_acceptance = false`
`controller_tuning_allowed = false`
