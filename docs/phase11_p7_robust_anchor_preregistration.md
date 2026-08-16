# Phase 11 P7 preregistration — robust-anchor continuity under compositional shift

## Status

**PREREGISTERED BEFORE P7 DATA GENERATION**

Branch: `phase11-p7-robust-anchor-continuity`

P6 is frozen as a mixed/failed protected-validation result. Protected validation seed `286286` and every earlier exposed Phase 11 split are permanently seen and may motivate P7 design only; they may not be used for P7 fitting, calibration, threshold selection, candidate selection, or hidden testing.

## Research question

**Can a causal robust trend over recent genuine perception anchors prevent continuity extrapolation from inheriting a bad newest anchor, while a disjoint continuity-adaptation stage keeps uncertainty honest and a bounded seven-frame horizon restores useful perception availability under unseen compositional shift?**

P7 remains a simulation-only perception/reliability experiment. It does not modify or evaluate a real aircraft controller.

## Motivation from frozen P6 evidence

P6 source-conditional calibration passed every development gate but failed protected validation specifically on continuity-extension behavior:

- base-output 95% coverage remained acceptable (`90.89%` lateral / `93.64%` altitude);
- continuity lateral coverage became `99.28%`;
- continuity altitude coverage collapsed to `63.77%`;
- total availability was `90.42%`, below the preregistered `92%` floor.

Read-only P6 forensics found that protected-validation continuity rows more often operated near the fit-frozen altitude slope cap and that later altitude extension error was strongly associated with the truth error of the latest genuine anchor. Truth anchor error is not inference-visible and is forbidden as a P7 input. This motivates a legal causal proxy: **newest-anchor innovation relative to the trend implied by earlier genuine anchors**.

P7 does not retune P6 on seed `286286`.

## New P7 evidence boundary

All P7 seeds and trajectory families are new.

- fit seed: `297297`
- single-factor calibration seed: `308308`
- continuity-adaptation seed: `319319`
- compositional transfer-calibration seed: `330330`
- protected validation seed: `341341`
- frames per sequence: `60`

Families are disjoint:

- fit: `102..107`
- calibration: `108..110`
- continuity adaptation: `111..113`
- transfer calibration: `114..116`
- protected validation: `117..119`

The full trajectory/sequence is the split unit. No adjacent-frame random split is allowed.

### Fit and single-factor calibration domains

1. `nominal`
2. `edge`
3. `small_scale`
4. `oblique`
5. `dim`
6. `blur_noise`
7. `temporal_dropout`
8. `low_contrast`

### Seen continuity-adaptation compositions

1. `edge+temporal_dropout`
2. `small_scale+temporal_dropout`
3. `oblique+temporal_dropout`
4. `dim+temporal_dropout`
5. `blur_noise+temporal_dropout`
6. `low_contrast+temporal_dropout`
7. `edge+small_scale+temporal_dropout`
8. `oblique+dim+temporal_dropout`

### Seen transfer-calibration compositions

1. `edge+blur_noise+temporal_dropout`
2. `small_scale+dim+temporal_dropout`
3. `oblique+low_contrast+temporal_dropout`
4. `dim+blur_noise+temporal_dropout`
5. `edge+oblique+temporal_dropout`
6. `small_scale+blur_noise+low_contrast`
7. `edge+dim+low_contrast`
8. `small_scale+oblique+blur_noise`

### Protected validation compositions

1. `edge+low_contrast+temporal_dropout`
2. `small_scale+oblique+temporal_dropout`
3. `dim+low_contrast+temporal_dropout`
4. `blur_noise+low_contrast+temporal_dropout`
5. `edge+small_scale+oblique`
6. `edge+oblique+dim+blur_noise`
7. `small_scale+dim+blur_noise+temporal_dropout`
8. `edge+small_scale+oblique+dim+blur_noise+temporal_dropout`

Protected validation seed `341341` must not be generated before an exact P7 candidate-freeze checkpoint.

## Frozen inherited front end

P7 inherits the same synthetic perception response generator and the existing non-recursive two-frame bridge used by P5/P6.

- genuine candidate outputs remain the only motion-history anchors;
- inherited two-frame bridge estimates are never anchors;
- P7 continuity estimates are never anchors;
- no future frame, future reacquisition event, domain label, truth state, or true error is available to the continuity predictor.

## P7 robust genuine-anchor trend

### Anchor window

Use up to the **three most recent genuine candidate anchors** within a sequence.

### Robust slope

With three anchors, compute every pairwise per-frame slope for each axis and use the median pairwise slope (three pairwise slopes total). With exactly two anchors, use their ordinary two-point slope. With fewer than two genuine anchors, P7 cannot create a continuity estimate.

### Robust intercept / current trend state

For each available anchor `(t_i, y_i)` and the frozen robust slope `m`, compute `b_i = y_i - m*t_i` and use the median `b_i` as the robust intercept.

The robust trend value at the latest genuine-anchor time is therefore:

`y_trend_latest = median_i(y_i - m*t_i) + m*t_latest`

P7 extrapolates from this robust trend state rather than treating the newest genuine estimate as an unquestioned intercept.

### Fit-frozen velocity caps

As in P5/P6, derive independent lateral and altitude absolute slope caps from the P7 fit split only using genuine-anchor-to-genuine-anchor slopes.

Freeze the empirical `99th` percentile per axis. Clip the robust P7 slope to those caps before extrapolation.

### Bounded horizon and damping

The inherited two-frame bridge remains unchanged. P7 continuity may act only when that inherited layer still has no estimate.

- minimum P7 continuity horizon: `3` frames after the latest genuine anchor;
- maximum total continuity horizon: **`7` frames**;
- damping factor: **`0.85`** per extrapolated step.

For horizon `h`, after slope clipping:

`estimate_h = y_trend_latest + m_clipped * sum(0.85^k for k=0..h-1)`

The horizon extension from 5 to 7 is motivated by frozen P6 read-only availability forensics but is evaluated only on fresh P7 evidence.

## Inference-visible anchor-consistency features

P7 exposes new causal diagnostics to the reliability model. None uses truth error.

### Newest-anchor innovation

When at least three genuine anchors exist, predict the newest anchor from the preceding two genuine anchors using their two-point trend and compute:

- `anchor_innovation_lateral_abs`
- `anchor_innovation_altitude_abs`

When fewer than three genuine anchors exist, both are `0` and `anchor_innovation_available=false`.

### Slope-cap utilization

After robust-slope clipping, expose:

- `lateral_slope_cap_utilization = abs(m_lateral_clipped) / lateral_cap`
- `altitude_slope_cap_utilization = abs(m_altitude_clipped) / altitude_cap`

clipped to `[0,1]`.

### Other causal continuity features

- continuity horizon (`0..7`);
- scalar inherited reliability risk score;
- normalized inherited coactivation count;
- eight inherited causal risk components;
- source category.

Truth labels, true anchor error, domain name, trajectory family, and future observations are forbidden inputs.

## P7 base scale model

The base lateral/altitude scale model keeps the P5/P6 low-capacity architecture principles:

- standardized causal continuous basis;
- log absolute-error target with `1e-4` floor;
- fit-target winsorization at empirical `2nd` and `98th` percentiles;
- ridge regression lambda `4.0`;
- fitted-log-scale q01/q99 prediction guard expanded by `0.35`;
- finite-sample single-factor conformal calibration at targets `{0.50,0.68,0.80,0.90,0.95}`.

The P7 base scale basis contains:

1. eight inherited causal risk components;
2. scalar risk score;
3. normalized coactivation count;
4. largest and second-largest primary risk components;
5. P7 continuity horizon;
6. lateral and altitude slope-cap utilization;
7. lateral and altitude anchor innovation;
8. anchor-innovation-available indicator;
9. source one-hots for partial-edge, center-regeometry, known-ArUco-refined, inherited temporal bridge, and P7 robust continuity.

## Disjoint continuity-adaptation model

P7 introduces one small model fitted **only on the separate continuity-adaptation split**, never on transfer calibration.

### Population

Use only truth-visible available `robust_continuity` rows from adaptation seed `319319`.

Minimum required adaptation continuity rows: **`80`**. If fewer exist, P7 development fails and protected validation is not exposed.

### Correction target

For each axis, using the already-frozen fit scale model:

`target = log(abs_error / max(predicted_base_scale, 1e-9) + 1e-4)`

### Correction basis

Only continuity-specific causal quantities:

- continuity horizon;
- lateral slope-cap utilization;
- altitude slope-cap utilization;
- lateral anchor innovation;
- altitude anchor innovation;
- anchor-innovation-available indicator;
- scalar risk score;
- normalized coactivation count.

The correction basis is standardized using the adaptation continuity population only.

### Correction fit

- separate lateral and altitude ridge models;
- fixed ridge lambda `4.0`;
- target winsorization at adaptation empirical `2nd` / `98th` percentiles;
- predicted log-correction guard at fitted q01/q99 expanded by `0.35`.

For non-continuity rows, correction factor is exactly `1.0`.

For robust-continuity rows:

`corrected_scale = base_scale * exp(predicted_log_correction)`

No candidate search over correction architectures is allowed.

## Single-factor and transfer conformal calibration

Single-factor calibration uses the corrected scale where applicable and finite-sample conformal order statistic `ceil((n+1)*q)`.

The separate seen transfer split then freezes exactly two transfer-calibration groups:

- `base_output`
- `robust_continuity`

Minimum required transfer rows:

- base output: `200`;
- robust continuity: **`50`**.

No pooled fallback is allowed.

For each group/axis/target:

`R_single = corrected_scale * Q_single(axis,q)`

`transfer_ratio = abs_error / max(R_single, 1e-9)`

and the finite-sample conformal transfer multiplier is `T(group,axis,q)`.

Final radius:

`R_P7 = corrected_scale * Q_single * T(group,axis,q)`

Radii are monotonized by cumulative maximum over increasing target coverage.

## Primary development / validation gates

The same gates are applied to seen transfer calibration and, if development passes, to the one protected validation exposure.

### H1 — useful availability

Truth-visible output availability must be `>=0.92`.

### H2 — overall 95% coverage transfer

Across all available outputs, 95% empirical coverage must be in `[0.90,0.98]` on both axes.

### H3 — overall calibration curve

Mean absolute coverage error across `{50%,68%,80%,90%,95%}` over both axes must be `<=0.06`.

### H4 — overall interval efficiency

Across all available outputs:

- median 95% half-width / all-available p95 absolute error `<=1.25` on each axis;
- p95 95% half-width / all-available p95 absolute error `<=2.25` on each axis.

### H5 — robust-continuity honesty

On `robust_continuity` rows only:

- 95% coverage in `[0.88,0.99]` on both axes;
- p95 95% half-width / continuity p95 absolute error `<=2.75` on both axes.

### H6 — base-output honesty

On `base_output` rows only:

- 95% coverage in `[0.90,0.98]` on both axes;
- p95 95% half-width / base-output p95 absolute error `<=2.25` on both axes.

### H7 — shift discrimination

Trajectory-level mean inherited severity must distinguish single-factor calibration from compositional evaluation with AUROC `>=0.85`.

H7 is diagnostic only.

## Secondary diagnostics

Report without using them for candidate tuning:

- continuity row counts by horizon;
- anchor-innovation distributions by axis;
- slope-cap-utilization distributions;
- robust-continuity MAE and p95 error by horizon;
- base vs robust-continuity source proportions;
- still-unavailable rows by causal reason (`insufficient_anchors` or `gap_beyond_horizon`);
- comparison of robust-continuity point error against the inherited P5 newest-anchor-intercept continuation **on the same fresh P7 rows**, diagnostic only.

## Candidate-freeze checkpoint

P7 may generate fit, calibration, adaptation, and seen transfer evidence after this preregistration.

Before protected validation, freeze and archive:

- exact P7 code commit;
- all seeds and families;
- velocity caps;
- robust-trend constants;
- base scale standardizer, target bounds, prediction guards, and coefficients;
- continuity-adaptation standardizer, target bounds, prediction guards, and coefficients;
- single-factor conformal quantiles;
- two source-conditional transfer multiplier tables;
- adaptation and transfer group counts;
- seen transfer gate metrics;
- artifact SHA-256 hashes.

If adaptation/transfer minimum counts or any H1-H6 seen-transfer gate fails, protected validation seed `341341` must not be exposed.

If all H1-H6 pass, the frozen candidate may be evaluated exactly once on seed `341341` with no method changes.

## Exposure policy

After adaptation seed `319319` is generated it is permanently seen fitting evidence.

After transfer seed `330330` is generated it is permanently seen calibration/development evidence.

After protected validation seed `341341` is generated it is permanently seen validation evidence regardless of outcome.

No P7 parameter may change after protected validation and then be re-evaluated on `341341` as unseen.

Even a fully successful P7 protected validation does **not** authorize the final Phase 11 frozen holdout. A final holdout requires a separate explicit user approval at an exact future candidate-freeze checkpoint.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
- negative, mixed, and failed outcomes remain permanent evidence
