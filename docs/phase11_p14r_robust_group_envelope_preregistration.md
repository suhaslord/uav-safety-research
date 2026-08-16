# Phase 11 P14R preregistration — robust groupwise conformal envelope

## Status

**PREREGISTERED BEFORE ANY P14R DATA GENERATION**

Authoritative predecessor: P14 bounded independent rescue, frozen seen-transfer stop at `465176b16f823d4c7d93331ffc26ecfbf24a1999`.

P14 established that the independent rescue mechanism solves the availability bottleneck, but its severity-Mondrian intervals undercovered under fresh compound shift and several low-severity evaluation cells became underpowered. P14 protected validation seed `748748` and the original P15 seed `759759` remain unexposed and are retired with that failed lineage rather than reused.

## Research question

Can the exact successful P14 point-estimation/rescue system retain its high availability while a distributionally robust, groupwise conformal envelope restores uncertainty honesty under fresh compound shift without relying on brittle severity cells?

## Scientific change relative to P14

Exactly one uncertainty-calibration change is allowed:

- keep the P14 point estimator, seven-frame bounded nonrecursive primary continuity, intervention definitions, and independent rescue observation model unchanged;
- remove low/mid/high severity from the conformal calibration cells;
- calibrate direct finite-sample absolute-error radii separately for the five frozen output groups;
- fit each group independently on two disjoint fresh calibration environments (`calibration_a` and `calibration_b`);
- for every group, axis, and target coverage, freeze the candidate radius as the pointwise maximum of the two environment-specific conformal radii.

The five groups remain:

1. `base_output`
2. `continuity_h3`
3. `continuity_h45`
4. `continuity_h67`
5. `independent_coarse_rescue`

Severity remains inference-visible only for H8 subgroup evaluation and H7 shift discrimination. It does not choose interval width and therefore cannot create sparse calibration/evaluation cells.

## Fresh evidence boundary

- fit seed: `814814`
- calibration A seed: `825825`
- calibration B seed: `836836`
- seen transfer seed: `847847`
- protected validation seed: `858858`
- final P15 seed: `869869`
- frames per sequence: `60`

Complete-sequence family units are disjoint:

- fit: `815..820` (6)
- calibration A: `821..852` (32)
- calibration B: `853..884` (32)
- seen transfer: `885..908` (24)
- protected validation: `909..932` (24)
- final P15: `933..956` (24)

No P14/P14R/P15 evidence seed or family may cross roles.

## Truth-independent event strata

Calibration A, calibration B, transfer, validation, and final holdout families are divided equally across the same four event strata as P14:

- `bootstrap5`: suppress primary candidates at frames `0..4`
- `gap3`: suppress at `12..14` and `42..44`
- `gap7`: suppress at `12..18` and `42..48`
- `gap12`: suppress at `12..23` and `42..53`

The intervention is fixed by family and frame only. It may not inspect truth, error, confidence, severity, or future observations.

## Calibration environments

### Calibration A — moderate compounds

1. `edge+blur_noise+temporal_dropout`
2. `small_scale+dim+temporal_dropout`
3. `oblique+low_contrast+temporal_dropout`
4. `edge+small_scale+dim+temporal_dropout`
5. `small_scale+oblique+blur_noise+temporal_dropout`
6. `edge+dim+low_contrast+temporal_dropout`
7. `oblique+dim+blur_noise+temporal_dropout`
8. `edge+small_scale+low_contrast+temporal_dropout`

### Calibration B — hard compounds

1. `edge+small_scale+oblique+temporal_dropout`
2. `edge+dim+blur_noise+temporal_dropout`
3. `small_scale+dim+blur_noise+low_contrast+temporal_dropout`
4. `edge+oblique+dim+low_contrast+temporal_dropout`
5. `edge+small_scale+blur_noise+low_contrast+temporal_dropout`
6. `small_scale+oblique+dim+blur_noise+temporal_dropout`
7. `edge+oblique+dim+blur_noise+low_contrast+temporal_dropout`
8. `edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout`

### Seen transfer domains

1. `edge+oblique+blur_noise+temporal_dropout`
2. `small_scale+oblique+low_contrast+temporal_dropout`
3. `edge+small_scale+dim+low_contrast+temporal_dropout`
4. `small_scale+dim+blur_noise+temporal_dropout`
5. `oblique+dim+blur_noise+low_contrast+temporal_dropout`
6. `edge+small_scale+oblique+blur_noise+temporal_dropout`
7. `edge+dim+blur_noise+low_contrast+temporal_dropout`
8. `edge+small_scale+oblique+dim+low_contrast+temporal_dropout`
9. `small_scale+oblique+dim+low_contrast+temporal_dropout`
10. `edge+small_scale+dim+blur_noise+low_contrast+temporal_dropout`

### Protected validation domains

1. `edge+low_contrast+temporal_dropout`
2. `small_scale+blur_noise+temporal_dropout`
3. `oblique+dim+temporal_dropout`
4. `edge+oblique+dim+temporal_dropout`
5. `small_scale+oblique+blur_noise+low_contrast+temporal_dropout`
6. `edge+small_scale+oblique+dim+temporal_dropout`
7. `edge+oblique+blur_noise+low_contrast+temporal_dropout`
8. `small_scale+dim+low_contrast+temporal_dropout`
9. `edge+small_scale+oblique+low_contrast+temporal_dropout`
10. `edge+small_scale+dim+blur_noise+temporal_dropout`

The P15 final domains are frozen separately in `docs/phase11_p15_final_holdout_v2_preregistration.md` before any P14R generation.

## Unchanged rescue model

P14 rescue parameters are frozen unchanged:

- availability probability `0.95`
- lateral Gaussian sigma `0.10 m`
- altitude Gaussian sigma `0.20 m`
- independent rare-tail probability `0.02`
- rare-tail sigma multiplier `3.0`
- rescue only when the primary stack is unavailable
- rescue output never becomes a primary anchor
- rescue output is never recursively propagated

## Candidate freeze

For each calibration environment independently, compute finite-sample conformal absolute-error radii at targets `{0.50,0.68,0.80,0.90,0.95}` using the existing `ceil((n+1)q)` order-statistic rule and monotone cumulative maxima across increasing q.

For each group/axis/target, freeze:

`robust_radius = max(radius_calibration_a, radius_calibration_b)`

No parameter may be selected using transfer, validation, or final-holdout rows.

Calibration minimum rows per group **in each environment separately**:

- base `>=900`
- h3 `>=180`
- h45 `>=135`
- h67 `>=90`
- rescue `>=180`

If either calibration environment misses any minimum, stop before transfer.

## Evaluation power minimums

Seen transfer and protected validation minimum rows per group:

- base `>=360`
- h3 `>=60`
- h45 `>=45`
- h67 `>=30`
- rescue `>=60`

Final P15 minimums are stricter and frozen in its preregistration.

## Primary gates

P14R retains P14's numerical standards.

- H1 useful availability: `>=0.92`
- H2 overall 95% coverage: each axis `[0.90,0.98]`
- H3 MACE across `{50,68,80,90,95}%` and both axes: `<=0.06`
- H4 interval efficiency: median 95% half-width / overall p95 error `<=1.25`; p95 half-width / p95 error `<=2.25` each axis
- H5 primary-continuity honesty: each axis coverage `[0.88,0.99]`; p95 width/error `<=2.75`
- H6 base-output honesty: each axis coverage `[0.90,0.98]`; p95 width/error `<=2.25`
- H7 shift AUROC `>=0.85`, diagnostic only
- H8 high-severity honesty: each axis coverage `[0.88,0.99]`; p95 width/error `<=2.75`
- H9 rescue-output honesty: each axis coverage `[0.90,0.98]`; p95 width/error `<=2.25`
- H10 rescue accuracy: lateral MAE `<=0.15 m`, altitude MAE `<=0.30 m`, lateral p95 `<=0.35 m`, altitude p95 `<=0.70 m`
- H11 rescue effectiveness: recover at least `85%` of truth-visible primary-unavailable rows

H8 high severity is defined before evaluation by the 2/3 severity quantile within each group on the union of calibration A+B. Those thresholds are evaluation subgroup boundaries only, not interval cells.

Transfer/validation passes only if group minimums and H1-H6/H8-H11 all pass. H7 remains diagnostic.

## Gated sequence

1. Freeze exact P14R scientific code/tests/preregistrations.
2. Generate fresh fit + calibration A + calibration B only; freeze and hash exact candidate.
3. Expose seen transfer `847847` exactly once.
4. If any required transfer gate fails, stop. Do not generate protected validation or P15.
5. If transfer passes, expose protected validation `858858` exactly once with the unchanged candidate.
6. If any required validation gate fails, stop. Do not generate P15.
7. If validation passes, expose P15 `869869` exactly once with the unchanged candidate and no method changes.
8. Freeze the final outcome. No post-P15 tuning is allowed under this protocol.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no claim that any real auxiliary sensor has the synthetic rescue distribution
- no new raw-camera accuracy claim
- all negative/mixed outcomes remain permanent evidence
