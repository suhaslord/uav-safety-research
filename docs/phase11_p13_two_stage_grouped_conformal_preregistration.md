# Phase 11 P13 preregistration — two-stage three-group conformal transfer

## Status

**PREREGISTERED BEFORE P13 DATA GENERATION**

Branch: `phase11-p13-two-stage-grouped-conformal`

P12 froze a candidate successfully and then failed on seen transfer because one-stage grouped conformal undercovered under harder compositional shift while interval efficiency remained comfortably inside the preregistered bounds. P12 fit `539539`, grouped calibration `550550`, and seen transfer `561561` are permanently seen; protected `572572` was never exposed and is retired.

P13 preserves the P9 soft point estimator and the P12 three groups exactly. The only new scientific step is a **disjoint compositional transfer-calibration layer** applied to the already-frozen base grouped radii before a separate seen challenge is evaluated.

## Research question

**Can a second, disjoint conformal transfer-calibration stage restore coverage under compositional shift without sacrificing the interval-efficiency margin seen in P12?**

## Fresh evidence boundary

- fit seed: `583583`
- base grouped-calibration seed: `594594`
- compositional transfer-calibration seed: `605605`
- seen challenge seed: `616616`
- protected validation seed: `627627`
- frames per sequence: `60`

Disjoint families:

- fit: `398..403` (6)
- base calibration: `404..451` (48)
- transfer calibration: `452..475` (24)
- seen challenge: `476..495` (20)
- protected validation: `496..515` (20)

The complete sequence is the split unit.

### Base calibration compositions

Same eight calibration compositions used by P12/P9.

### Transfer-calibration compositions

1. `edge+blur_noise+temporal_dropout`
2. `small_scale+dim+temporal_dropout`
3. `oblique+low_contrast+temporal_dropout`
4. `dim+blur_noise+temporal_dropout`
5. `edge+oblique+temporal_dropout`
6. `small_scale+blur_noise+low_contrast+temporal_dropout`
7. `edge+dim+low_contrast+temporal_dropout`
8. `small_scale+oblique+blur_noise+temporal_dropout`

### Seen-challenge compositions

1. `edge+small_scale+low_contrast+temporal_dropout`
2. `oblique+blur_noise+temporal_dropout`
3. `edge+dim+temporal_dropout`
4. `small_scale+oblique+low_contrast+temporal_dropout`
5. `edge+blur_noise+low_contrast+temporal_dropout`
6. `small_scale+dim+blur_noise+temporal_dropout`
7. `oblique+dim+low_contrast+temporal_dropout`
8. `edge+small_scale+oblique+blur_noise+temporal_dropout`

### Protected-validation compositions

1. `edge+low_contrast+temporal_dropout`
2. `small_scale+oblique+temporal_dropout`
3. `dim+low_contrast+temporal_dropout`
4. `blur_noise+low_contrast+temporal_dropout`
5. `edge+small_scale+oblique+temporal_dropout`
6. `edge+oblique+dim+blur_noise+temporal_dropout`
7. `small_scale+dim+blur_noise+low_contrast+temporal_dropout`
8. `edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout`

Protected seed `627627` must not be generated before the final P13 candidate is frozen and the separate seen challenge passes H1-H6.

## Point estimator — unchanged

P13 imports the exact P9/P12 soft bounded-influence continuity method unchanged:

- genuine perception candidates are the only anchors;
- q99 fit-only velocity cap;
- q95 fit-only innovation scale;
- `soft_scale_multiplier = 3.0`;
- `e_soft = e / sqrt(1 + (e/(3*s))^2)`;
- 0.50/0.50 prior/updated slope blend;
- horizons 3-7 only beyond the unchanged two-frame bridge;
- damping `0.85`;
- no recursive continuity.

## Three fixed groups — unchanged

1. `base_output`
2. `continuity_h3`
3. `continuity_h47` (horizons 4-7)

## Stage 1 — base grouped conformal

On seed `594594`, freeze finite-sample absolute-error conformal radii for every group, axis, and target `{0.50,0.68,0.80,0.90,0.95}` using order statistic `ceil((n+1)*q)`.

Base-calibration minimums remain:

- base `>=1500`
- h3 `>=150`
- h47 `>=100`

## Stage 2 — compositional transfer calibration

On the disjoint transfer-calibration seed `605605`, for each group/axis/target:

`ratio = abs_error / max(R_base(group,axis,q), 1e-9)`

Freeze:

`T(group,axis,q) = finite_sample_conformal_quantile(ratio, q)`

Final radius:

`R_final(group,axis,q) = R_base(group,axis,q) * T(group,axis,q)`

Final radii are monotonized by cumulative maximum over increasing q.

Transfer-calibration minimums:

- base `>=1000`
- h3 `>=100`
- h47 `>=60`

No learned scale model, no learned correction model, and no additional post-challenge multiplier are allowed.

The final P13 candidate is frozen **after** transfer calibration and **before** seen challenge seed `616616` is generated.

## Seen challenge minimums

- base `>=1000`
- h3 `>=100`
- h47 `>=60`

If any minimum fails, protected validation is not exposed.

## Primary gates on seen challenge and protected validation

### H1 availability
Truth-visible output availability `>=0.92`.

### H2 overall coverage
95% empirical coverage on both axes in `[0.90,0.98]`.

### H3 calibration curve
MACE across targets `{50,68,80,90,95}%` and both axes `<=0.06`.

### H4 interval efficiency
For each axis:
- median 95% half-width / all-available p95 error `<=1.25`;
- p95 95% half-width / all-available p95 error `<=2.25`.

### H5 continuity honesty
Across all continuity rows:
- 95% coverage `[0.88,0.99]` on each axis;
- p95 95% half-width / continuity p95 error `<=2.75` on each axis.

### H6 base-output honesty
- 95% coverage `[0.90,0.98]` on each axis;
- p95 95% half-width / base p95 error `<=2.25` on each axis.

H7 inherited-severity AUROC `>=0.85` is diagnostic only.

## Staging / exposure rules

1. Generate fit + base calibration + transfer calibration only.
2. Freeze and hash the final two-stage candidate.
3. Generate/evaluate seen challenge `616616` exactly once.
4. If any H1-H6 challenge gate fails, stop and retire unexposed `627627`.
5. If every H1-H6 challenge gate passes, the exact candidate may be evaluated once on protected validation `627627`.

No P13 constant, grouping rule, radius, multiplier, threshold, or gate may change after challenge exposure.

A complete protected-validation pass still does **not** authorize the final Phase 11 frozen holdout. Final-holdout exposure requires separate explicit user approval at a later exact checkpoint.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
