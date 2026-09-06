# Phase 12 development log

This file records permanently-seen development iterations. It is **not** transfer, protected-validation, or final evidence.

## Iteration 1 — severity-linear normalized conformal

- workflow run: `34003594803`
- scientific head: `5b7b6f65846fdd6bd0ef50c427ff649b3ffc856c`
- candidate SHA-256: `e5edd7523def68a97158194baa318b47d2489e5a9dd722a2f068e7fdd2af408f`
- development result SHA-256: `a6527f409b2dd771bc32989978f4c7d21349951ec5c172b2dfd817ae1a4dce15`
- development seed: `907907` only
- transfer `913913`: **unexposed**
- protected `924924`: **unexposed**
- final `935935`: **unexposed**

Implementation/invariant checks: `21 passed`.

### Result

| Gate | Development result | Verdict |
|---|---:|---|
| H1 useful availability | `97.951%` | PASS |
| H2 lateral 95% coverage | `94.984%` | PASS |
| H2 altitude 95% coverage | `95.339%` | PASS |
| H3 calibration MACE | `0.007944` | PASS |
| H4 lateral median width / p95 error | `0.5885x` | PASS component |
| H4 lateral p95 width / p95 error | `2.3620x` | **FAIL** (`<=2.25x`) |
| H4 altitude median width / p95 error | `0.8139x` | PASS component |
| H4 altitude p95 width / p95 error | `1.7277x` | PASS component |
| H5 pooled continuity honesty | passed | PASS |
| H6 base-output honesty | passed | PASS |
| H8 high-severity honesty | passed | PASS |
| H9 rescue-output honesty | passed | PASS |
| H10 rescue accuracy floor | passed | PASS |
| H11 rescue effectiveness | passed | PASS |

Overall development result: **MIXED / FAILED** because H4 lateral tail efficiency remained above the locked boundary.

### Diagnosis

The first adaptive model improved the targeted tail metric relative to the closed Phase 11 protected result (`2.4354x -> 2.3620x`) without sacrificing nominal overall coverage. The remaining failure is narrow: median lateral width is already efficient, while only the upper width tail remains too large.

The largest possible lateral half-widths come from the continuity groups because their severity scale has the widest absolute magnitude and groupwise robust conformal multipliers are necessarily larger. Development continuity coverage was `97.08%`, so the problem is not lack of honesty; the current within-group heteroscedastic scale allocates too much width to its upper-severity tail.

### Iteration 2 decision — before any transfer exposure

Keep all evidence identities, gates, point-estimator behavior, rescue behavior, severity anchors, calibration environments, and the robust max rule unchanged.

Change only the *within-continuity scale contrast*: after computing the preregistered clipped linear severity scale, shrink its ratio around the group/axis geometric center with exponent `0.5` for `continuity_h3`, `continuity_h45`, and `continuity_h67`. Base and independent-rescue scales remain exponent `1.0`.

For raw scale `s`, low/high anchors `l,h`, center `c=sqrt(l*h)`, the iteration-2 scale is:

`scale_v2 = c * (s / c)^0.5`

when `h > l`; otherwise it is unchanged.

This preserves positivity and monotonicity, reduces unstable tail contrast, and still lets the two fresh calibration environments determine every conformal quantile. It does **not** multiply final intervals by a hand-tuned shrink factor; therefore uniform calibration still cancels arbitrary absolute scale changes.

Iteration 2 is allowed to reuse development seed `907907` because that split was permanently designated debugging-only before first exposure. No transfer/protected/final seed may be generated until a candidate and scientific head are frozen.

## Iteration 2 — continuity-contrast shrinkage

- workflow run: `34003903120`
- scientific head: `c22bdc2fae7b0d3d2467898bd207231bc2683d1b`
- candidate SHA-256: `f1cbb56a89896739ac5aa4ccd2946264fd60d7f4e6aa65ed376fc584a59aab46`
- development result SHA-256: `d0165cee0ac0830e97d2bfcafa0f25d191103c4d2a5358d5b99dbef6e90a3269`
- development artifact ID: `9980339458`
- development seed: `907907` only
- transfer `913913`: **unexposed**
- protected `924924`: **unexposed**
- final `935935`: **unexposed**

Implementation/invariant checks: `26 passed`.

### Result

| Gate | Development result | Verdict |
|---|---:|---|
| H1 useful availability | `98.012%` | PASS |
| H2 lateral 95% coverage | `95.279%` | PASS |
| H2 altitude 95% coverage | `95.191%` | PASS |
| H3 calibration MACE | `0.004838` | PASS |
| H4 lateral median width / p95 error | `0.5886x` | PASS component |
| H4 lateral p95 width / p95 error | `2.3485x` | **FAIL** (`<=2.25x`) |
| H4 altitude median width / p95 error | `0.8129x` | PASS component |
| H4 altitude p95 width / p95 error | `1.7050x` | PASS component |
| H5 primary-continuity honesty | passed (`97.382%` lateral coverage) | PASS |
| H6 base-output honesty | passed | PASS |
| H8 high-severity honesty | passed | PASS |
| H9 rescue-output honesty | passed | PASS |
| H10 rescue accuracy floor | passed | PASS |
| H11 rescue effectiveness | passed (`94.83%` recovery) | PASS |

Overall iteration-2 development result: **MIXED / FAILED** because the sole H4 lateral p95 component remains `0.0985x` above the locked boundary.

### Interpretation

Iteration 2 moved the targeted metric in the intended direction (`2.3620x -> 2.3485x`) while improving calibration error and retaining all other required gates. The effect size is too small to justify exposing transfer.

The remaining evidence argues against simply increasing the continuity contrast shrinkage further as the main solution: continuity honesty is already strong, but the overall lateral tail remains driven by a small set of high-width outputs. The two calibration-environment 95% normalized radii also differ only modestly on the lateral axis (about `1.0%` to `6.7%` by group), so replacing the robust maximum alone is unlikely to be a complete fix.

### Next development target

Do **not** expose transfer yet. The next development iteration should remain on seed `907907` and test a more targeted uncertainty allocation change that is still inference-visible and low-capacity. Candidate directions are:

1. add a preregistered continuity-only reliability feature already available at inference (for example a bounded function of anchor innovation / gain) to the local scale; or
2. simplify continuity calibration into a pooled continuity uncertainty cell if diagnostics show the separate horizon cells are creating width cliffs without corresponding error separation.

Whichever direction is chosen must be amended into the preregistration before implementation and before transfer seed `913913` is ever exposed. No gate relaxation or post-hoc interval multiplier is allowed.