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

## Iteration 3 — innovation-residual normalized conformal

Iteration 3 was chosen only after the permanently-seen width-tail forensic analysis and was preregistered before the next development evaluation. The diagnostic showed that iteration-2 width was allocated mainly by severity/horizon even though normalized lateral anchor innovation was a substantially more stable predictor of realized continuity error across scale-fit, calibration A, calibration B, and development.

Frozen method:

`u = log1p(p9_anchor_innovation_lateral_abs / frozen_lateral_innovation_scale)`

A monotone residual contrast is fit per continuity horizon group using only Phase 12 scale-fit evidence. It modifies only lateral continuity uncertainty. Base, rescue, all altitude scales, point estimates, availability, groups, finite-sample conformal calculation, calibration A/B maximum, thresholds, and H1-H11 definitions remain unchanged.

- preregistration: `docs/phase12_iteration3_preregistration.md`
- forensic note: `docs/phase12_width_tail_forensics.md`
- frozen scientific head: `8d0617a83d699cd14eae6194ce3a86a5c034dfbc`
- candidate SHA-256: `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`
- development workflow run: `34004695243`
- development result SHA-256: `cc502dd7adc11d92f8efb331e6d16b629e6c264f4392549d5d419e31ceb0a9e0`
- candidate determinism: PASS; byte-identical independent rebuild
- targeted predecessor + Phase 12 invariants: PASS
- broad repository CI on frozen scientific head: PASS (`34004695207`)

### Iteration-3 development result

| Gate | Development result | Verdict |
|---|---:|---|
| H1 useful availability | `98.264%` | PASS |
| H2 lateral 95% coverage | `94.947%` | PASS |
| H2 altitude 95% coverage | `94.859%` | PASS |
| H3 calibration MACE | `0.003587` | PASS |
| H4 lateral median width / p95 error | `0.586486x` | PASS |
| H4 lateral p95 width / p95 error | **`2.168449x`** | **PASS** |
| H4 altitude median width / p95 error | `0.811724x` | PASS |
| H4 altitude p95 width / p95 error | `1.706228x` | PASS |
| H5 primary-continuity honesty | passed | PASS |
| H6 base-output honesty | passed | PASS |
| H8 high-severity honesty | passed | PASS |
| H9 rescue-output honesty | passed | PASS |
| H10 rescue accuracy floor | passed | PASS |
| H11 rescue effectiveness | `95.483%` recovery | PASS |

Overall iteration-3 development result: **PASS**. The candidate was frozen immediately; no further development tuning was performed.

## Downstream evidence status — immutable iteration-3 candidate

The following downstream results are not development evidence, but are recorded here to close the lineage and point to their dedicated evidence documents.

| Stage | Seed | Lateral H4 p95 ratio | Lateral 95% coverage | Result |
|---|---:|---:|---:|---|
| transfer | `913913` | `2.0580396987x` | `94.5035%` | PASS |
| protected validation | `924924` | `2.2124459142x` | `95.3994%` | PASS |
| final holdout | `935935` | `2.2303494666x` | `95.5333%` | PASS |

Dedicated records:

- `docs/phase12_iteration3_transfer_result.md`
- `docs/phase12_iteration3_protected_result.md`
- `docs/phase12_iteration3_final_report.md`

All three stages used candidate SHA `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991` and frozen scientific SHA `8d0617a83d699cd14eae6194ce3a86a5c034dfbc` without refit or recalibration.

### Final evidence ledger

- `880880` scale fit — seen
- `891891` calibration A — seen
- `902902` calibration B — seen
- `907907` development-only — seen; never promoted as protected evidence
- `913913` transfer — exposed once; PASS
- `924924` protected validation — exposed once; PASS
- `935935` final holdout — exposed once; PASS
- `858858` Phase 11 protected — **not reused / forbidden**
- `869869` retired Phase 11 P15-v2 — **not exposed / forbidden**

Phase 12 iteration 3 is complete. No further tuning or evidence exposure is authorized in this lineage.
