# Phase 22 fit freeze

## Verdict

**PASS — all 8 preregistered fit gates passed.**

This file records the immutable Phase 22 fit candidate. No Phase 22 model coefficient, factor, threshold, or implementation may change after this freeze.

## Evidence identity

- role: `fit`
- seed: `2222220`
- families: `2313–2336`
- workflow run: `34042362702`
- artifact: `9992081402` (`phase22-fit`)
- artifact digest: `sha256:2156cc54f127ec2b417a6e4b7f1f8c6f73c1e26b54ed0eb04a8c9b60b18ffaf9`
- scientific SHA: `b960351882f5bac1692a5219c70433659b1f5f4d`
- fit result SHA-256: `ff110ea500a25e797f0b12a2123490468a8b38d7b6f460c4244b66dbe4f39ce1`
- **fit candidate SHA-256: `62e75d7b39088c2e66f1cc6be4d180501b79632f2f6847af1fbe0bd96be17551`**

## Fit gates

All passed:

- F22.1 lineage integrity
- F22.2 complete matched factorial construction
- F22.3 fit endpoint phenomenon remains present
- F22.4 first-order fit structure
- F22.5 balanced factor direction
- F22.6 finite frozen candidate
- F22.7 static latency degradation at fit endpoints
- F22.8 zero adaptation and claim boundary

## Fit endpoint

RMSE:

- simple advantage: `0.09454282168027117`
- hard advantage: `-0.049162139926905546`
- attenuation: `0.14370496160717672`

MAE:

- simple advantage: `0.13545417339398713`
- hard advantage: `-0.048869299463559335`
- attenuation: `0.18432347285754647`

## First-order variance share

- RMSE: `0.8037913997296677`
- MAE: `0.8013996931594806`

## Frozen additive models

Effect coding is `+1` for factor present and `-1` for factor absent.

### RMSE advantage model

Intercept:

`-0.002232251681940814`

Main effects:

- `edge`: `-0.015227165371012236`
- `oblique`: `-0.011625789781545236`
- `dim`: `-0.013596902414146822`
- `blur_noise`: `-0.01150638682159618`
- `low_contrast`: `-0.010148983059508968`

### MAE advantage model

Intercept:

`0.03217701062234656`

Main effects:

- `edge`: `-0.019810568920743156`
- `oblique`: `-0.013994817652360055`
- `dim`: `-0.017268184116372667`
- `blur_noise`: `-0.016054624517100415`
- `low_contrast`: `-0.010940672041537258`

No interaction coefficient is retained.

## Permanent boundary

Development, transfer, protected, and final must use the exact candidate SHA above. No refit, clipping, shrinkage, recalibration, interaction activation, or threshold change is permitted.

`simulation_only = true`
`safety_acceptance = false`
`controller_tuning_allowed = false`
