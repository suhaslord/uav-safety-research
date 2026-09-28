# Phase 22 protected validation result

## Verdict

**PASS — all 10 preregistered protected-validation gates passed.**

The exact frozen Phase 22 additive fit candidate transferred to a third wholly fresh 32-cell protected context cube without refitting.

## Evidence identity

- role: `protected validation`
- seed: `2222223`
- families: `2385–2408`
- workflow run: `34042891337`
- artifact: `9992245302` (`phase22-validation`)
- artifact digest: `sha256:085ba21620de0c4ffeaeb1d684a3b6ed9ce38e3f97829fa0addcb9ca84782ca2`
- scientific SHA: `31df52f0c83547e616549ba85cd652036b576244`
- protected result SHA-256: `7852797ff69fa87a5a1037948b6183f314d3391fd50a185e9911afd45f6570b1`
- frozen fit candidate SHA-256: `62e75d7b39088c2e66f1cc6be4d180501b79632f2f6847af1fbe0bd96be17551`

## Predictive transfer

RMSE advantage surface:

- cellwise R²: `0.8374612557838519`
- cellwise advantage prediction MAE: `0.009526597752050576`
- prediction RMSE: `0.012093274768653982`
- stable-sign eligible cells: `14`
- stable-sign accuracy: `1.0`
- observed attenuation: `0.13995093781724377`
- predicted attenuation: `0.12421045489561888`
- attenuation absolute error: `0.015740482921624888`

MAE advantage surface:

- cellwise R²: `0.794413366918568`
- cellwise advantage prediction MAE: `0.016729703027936357`
- prediction RMSE: `0.01920028936422742`
- stable-sign eligible cells: `28`
- stable-sign accuracy: `1.0`
- observed attenuation: `0.18230706524739515`
- predicted attenuation: `0.1561377344962271`
- attenuation absolute error: `0.026169330751168063`

## Fresh endpoints

RMSE:

- simple advantage: `0.08062258251949939`
- hard advantage: `-0.059328355297744384`

MAE:

- simple advantage: `0.14385266237724237`
- hard advantage: `-0.03845440287015278`

## Gates

All P22.1–P22.10 passed. Final holdout is authorized with the exact frozen candidate and unchanged thresholds.

No fit coefficient, interaction term, factor, threshold, or scientific implementation changed after transfer.

`simulation_only = true`
`safety_acceptance = false`
`controller_tuning_allowed = false`
