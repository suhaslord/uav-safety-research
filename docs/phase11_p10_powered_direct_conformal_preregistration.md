# Phase 11 P10 preregistration — powered replication of soft update + direct grouped conformal

## Status

**PREREGISTERED BEFORE P10 DATA GENERATION**

Branch: `phase11-p10-powered-direct-conformal`

P9 stopped before candidate freeze because grouped calibration contained `110` horizon-3 continuity rows versus the preregistered minimum `120`. P9 fit seed `407407` and grouped-calibration seed `418418` are permanently seen. P9 transfer `429429` and protected validation `440440` were never exposed and are retired rather than recycled.

P10 is a **powered replication**, not a method revision. The P9 soft-update equation, direct conformal grouping, row-count thresholds, and H1-H6 gates are retained unchanged.

## Research question

**When supplied with enough fresh grouped-calibration trajectories to satisfy the predeclared horizon-group sample minimums, does the P9 soft bounded-influence continuity estimator plus direct grouped conformal uncertainty transfer honestly and efficiently to unseen compositional shift?**

## Fresh evidence boundary

- fit seed: `451451`
- grouped-calibration seed: `462462`
- seen-transfer seed: `473473`
- protected-validation seed: `484484`
- frames per sequence: `60`

Disjoint families:

- fit: `188..193` (`6` families)
- grouped calibration: `194..211` (`18` families)
- seen transfer: `212..223` (`12` families)
- protected validation: `224..235` (`12` families)

No P9 rows are reused.

### Domains

Fit domains are unchanged from P9: `nominal`, `edge`, `small_scale`, `oblique`, `dim`, `blur_noise`, `temporal_dropout`, `low_contrast`.

Grouped-calibration compositions are unchanged in structure from P9:

1. `edge+temporal_dropout`
2. `small_scale+temporal_dropout`
3. `oblique+temporal_dropout`
4. `dim+temporal_dropout`
5. `blur_noise+temporal_dropout`
6. `low_contrast+temporal_dropout`
7. `edge+small_scale+temporal_dropout`
8. `oblique+dim+temporal_dropout`

Seen-transfer compositions:

1. `edge+blur_noise+temporal_dropout`
2. `small_scale+dim+temporal_dropout`
3. `oblique+low_contrast+temporal_dropout`
4. `dim+blur_noise+temporal_dropout`
5. `edge+oblique+temporal_dropout`
6. `small_scale+blur_noise+low_contrast+temporal_dropout`
7. `edge+dim+low_contrast+temporal_dropout`
8. `small_scale+oblique+blur_noise+temporal_dropout`

Protected-validation compositions:

1. `edge+low_contrast+temporal_dropout`
2. `small_scale+oblique+temporal_dropout`
3. `dim+low_contrast+temporal_dropout`
4. `blur_noise+low_contrast+temporal_dropout`
5. `edge+small_scale+oblique+temporal_dropout`
6. `edge+oblique+dim+blur_noise+temporal_dropout`
7. `small_scale+dim+blur_noise+low_contrast+temporal_dropout`
8. `edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout`

Protected seed `484484` must not be generated before the candidate has frozen and the seen-transfer gates have passed.

## Frozen P10 scientific method

The following are identical to P9 and may not change after P10 generation begins:

### Soft continuity update

- genuine perception candidates only may become anchors;
- inherited bridge outputs and P10 continuity outputs are never anchors;
- fit-only velocity cap = q99 absolute genuine-anchor slope per axis;
- fit-only innovation scale = q95 absolute newest-anchor innovation per axis;
- `soft_scale_multiplier = 3.0`;
- `e_soft = e / sqrt(1 + (e/(3*s))^2)`;
- previous-slope weight `0.50`;
- soft-updated-slope weight `0.50`;
- final slope clipped to fit q99 velocity cap;
- inherited bridge horizons 1-2 unchanged;
- P10 continuity horizons 3-7 only;
- damping `0.85`;
- no recursive continuity.

### Direct grouped conformal uncertainty

No learned uncertainty model, no adaptation correction, and no transfer multiplier are allowed.

Exactly four groups:

1. `base_output`;
2. `continuity_h3`;
3. `continuity_h45`;
4. `continuity_h67`.

For each group/axis/target `{0.50,0.68,0.80,0.90,0.95}`, freeze the finite-sample conformal absolute-error quantile from grouped-calibration seed `462462` using order statistic `ceil((n+1)*q)`.

No pooled fallback or data-dependent regrouping is allowed.

## Sample-size requirements — unchanged from P9

Candidate-freeze grouped-calibration minimums:

- `base_output >= 1000`;
- `continuity_h3 >= 120`;
- `continuity_h45 >= 60`;
- `continuity_h67 >= 30`.

Seen-transfer evaluation minimums:

- `base_output >= 800`;
- `continuity_h3 >= 100`;
- `continuity_h45 >= 50`;
- `continuity_h67 >= 20`.

Thresholds are not lowered after exposure.

## Primary gates — unchanged from P9

### H1 availability

Truth-visible output availability `>=0.92`.

### H2 overall 95% coverage

Both axes in `[0.90,0.98]`.

### H3 calibration curve

Mean absolute coverage error over `{50%,68%,80%,90%,95%}` and both axes `<=0.06`.

### H4 overall efficiency

Each axis:

- median 95% half-width / all-available p95 error `<=1.25`;
- p95 95% half-width / all-available p95 error `<=2.25`.

### H5 continuity honesty

Across all continuity rows:

- 95% coverage `[0.88,0.99]` on each axis;
- p95 95% half-width / continuity p95 error `<=2.75` on each axis.

### H6 base-output honesty

- 95% coverage `[0.90,0.98]` on each axis;
- p95 95% half-width / base-output p95 error `<=2.25` on each axis.

H7 shift AUROC `>=0.85` remains diagnostic only.

## Staging

1. Generate fresh fit + grouped-calibration data and freeze candidate.
2. Hash candidate before transfer exposure.
3. Evaluate candidate once on seen transfer seed `473473`.
4. If any sample minimum or H1-H6 fails, stop; protected seed `484484` remains unexposed.
5. Only if all H1-H6 pass may the exact candidate be evaluated once on `484484`.

No P10 scientific constant may change between stages.

Even a complete P10 protected-validation pass does **not** authorize the final Phase 11 frozen holdout. Final holdout exposure still requires separate explicit user approval at an exact future freeze checkpoint.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
