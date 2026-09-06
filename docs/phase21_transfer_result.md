# Phase 21 transfer result — Orthogonal Context Spectrum

## Verdict

**PASS — all 10 preregistered transfer gates passed.**

This result is frozen before protected validation.

## Evidence identity

- role: transfer
- seed: `2121212`
- families: `2241–2264`
- workflow run: `34014762359`
- artifact: `9983568761`
- artifact digest: `sha256:4410e4181f902d3829d0a3e123235ec654fcc114c8c1a9c25d0f2b511fe8cfa2`
- result SHA-256: `245dde7406c163abdf8a68a0b3f91ccf2f88c0000d8fd694518f835ee7d0cc55`
- frozen transfer scientific SHA: `359c835bc9d95d62d1864044a30f0cd3db07af69`

## Endpoint replication

RMSE:

- simple advantage: `0.12592704951000866`
- hard advantage: `-0.044648450513759874`
- endpoint attenuation: `0.17057550002376853`

MAE:

- simple advantage: `0.1695223331446396`
- hard advantage: `-0.03820214620531237`
- endpoint attenuation: `0.20772447934995197`

## Orthogonal structure

RMSE:

- first-order variance share: **`0.794523779801918`**
- interaction variance share: `0.20547622019808198`
- Parseval absolute error: `6.505213034913027e-19`

MAE:

- first-order variance share: **`0.7798994813866257`**
- interaction variance share: `0.22010051861337432`
- Parseval absolute error: `2.168404344971009e-19`

### First-order coefficients

RMSE:

- `edge`: `-0.019098424840617224`
- `oblique`: `-0.01186357055129282`
- `dim`: `-0.01267926312523613`
- `blur_noise`: `-0.016248499809717917`
- `low_contrast`: `-0.010982897694350138`

MAE:

- `edge`: `-0.021796917099290197`
- `oblique`: `-0.014839367960204835`
- `dim`: `-0.014571089321686857`
- `blur_noise`: `-0.017266297574107154`
- `low_contrast`: `-0.015118646348802205`

All five balanced first-order effects point toward attenuation on both statistics. No factor ranking is promoted into a claim.

## Gate result

All `O21.1–O21.10` passed with unchanged implementation and thresholds.

## Boundary

This remains a synthetic context-surface result only. It does not mean latency is beneficial and does not establish physical causal effects or physical UAV safety.

`simulation_only = true`
`safety_acceptance = false`
`controller_tuning_allowed = false`
