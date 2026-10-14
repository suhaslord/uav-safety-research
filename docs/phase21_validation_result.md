# Phase 21 protected validation result — Orthogonal Context Spectrum

## Verdict

**PASS — all 10 preregistered protected-validation gates passed.**

This result is frozen before final holdout exposure.

## Evidence identity

- role: protected validation
- seed: `2121213`
- families: `2265–2288`
- workflow run: `34014872701`
- artifact: `9983605823`
- artifact digest: `sha256:087dd866b544e20006398cc9c4de06dff3cf77435a12b8f9eb130720eac51e69`
- result SHA-256: `2bddc712ccba4f0a0e5f116aaed21874c367c4e452e7ac84eae91adcecf6c0df`
- frozen validation scientific SHA: `6d69dd2b70adeaee4946078c9772b97b32d64a32`

## Endpoint replication

RMSE:

- simple advantage: `0.08562134042808911`
- hard advantage: `-0.06569508841796723`
- endpoint attenuation: `0.15131642884605634`

MAE:

- simple advantage: `0.1412038510934115`
- hard advantage: `-0.06296303702516037`
- endpoint attenuation: `0.20416688811857187`

## Orthogonal structure

RMSE:

- first-order variance share: **`0.8408330195667463`**
- interaction variance share: `0.15916698043325372`
- Parseval absolute error: `1.0842021724855044e-19`

MAE:

- first-order variance share: **`0.752022601182325`**
- interaction variance share: `0.247977398817675`
- Parseval absolute error: `2.168404344971009e-19`

### First-order coefficients

RMSE:

- `edge`: `-0.01703797094353241`
- `oblique`: `-0.009792345714118002`
- `dim`: `-0.012099488722906122`
- `blur_noise`: `-0.011049599030606809`
- `low_contrast`: `-0.009807180091203647`

MAE:

- `edge`: `-0.01913189807469938`
- `oblique`: `-0.01277482445614092`
- `dim`: `-0.015413551334145355`
- `blur_noise`: `-0.014273742224559918`
- `low_contrast`: `-0.013630060599436687`

All five balanced first-order effects point toward attenuation on both statistics. No factor ranking is promoted into a claim.

## Gate result

All `O21.1–O21.10` passed with unchanged implementation and thresholds.

## Boundary

This remains a synthetic context-surface result only. It does not mean latency is beneficial and does not establish physical modifier causality or physical UAV safety.

`simulation_only = true`
`safety_acceptance = false`
`controller_tuning_allowed = false`
