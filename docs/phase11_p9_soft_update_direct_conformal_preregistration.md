# Phase 11 P9 preregistration — soft anchor update + direct grouped conformal

## Status

**PREREGISTERED BEFORE P9 DATA GENERATION**

Branch: `phase11-p9-soft-update-direct-conformal`

P8 is frozen as a development failure. P8 fit/calibration/adaptation/transfer seeds `352352`, `363363`, `374374`, and `385385` are permanently seen. P8 protected validation seed `396396` was never exposed and is retired rather than recycled.

All earlier Phase 11 evidence is permanently seen. Prior rows and labels may motivate the P9 hypothesis only; they may not be used for P9 fitting, conformal calibration, candidate selection, or hidden testing.

## Research question

**Can a smooth bounded-influence update of the newest genuine perception anchor preserve short-gap continuity without P8's widespread hard clipping, while a direct grouped conformal interval design achieves honest coverage without the interval inflation created by stacked learned-scale and transfer-multiplier layers?**

P9 is simulation-only perception/reliability research. It does not modify, tune, or validate a physical aircraft controller.

## P9 changes — exactly two

Relative to the P8 concept, P9 makes only these two scientific changes:

1. replace hard newest-anchor innovation clipping with a preregistered analytic soft bounded-influence update;
2. replace the learned base-scale + adaptation-correction + transfer-multiplier uncertainty stack with direct finite-sample absolute-error conformal radii in four fixed source/horizon groups.

No learned uncertainty model is used in P9.

## Fresh P9 evidence boundary

All P9 seeds and trajectory families are new.

- fit seed: `407407`
- grouped conformal calibration seed: `418418`
- seen compositional transfer seed: `429429`
- protected validation seed: `440440`
- frames per sequence: `60`

Families are disjoint:

- fit: `150..155` (`6` families)
- grouped calibration: `156..167` (`12` families)
- seen transfer: `168..177` (`10` families)
- protected validation: `178..187` (`10` families)

The complete trajectory/sequence is the split unit. No adjacent-frame random split is allowed.

### Fit domains

1. `nominal`
2. `edge`
3. `small_scale`
4. `oblique`
5. `dim`
6. `blur_noise`
7. `temporal_dropout`
8. `low_contrast`

### Grouped-calibration compositions

1. `edge+temporal_dropout`
2. `small_scale+temporal_dropout`
3. `oblique+temporal_dropout`
4. `dim+temporal_dropout`
5. `blur_noise+temporal_dropout`
6. `low_contrast+temporal_dropout`
7. `edge+small_scale+temporal_dropout`
8. `oblique+dim+temporal_dropout`

### Seen-transfer compositions

1. `edge+blur_noise+temporal_dropout`
2. `small_scale+dim+temporal_dropout`
3. `oblique+low_contrast+temporal_dropout`
4. `dim+blur_noise+temporal_dropout`
5. `edge+oblique+temporal_dropout`
6. `small_scale+blur_noise+low_contrast+temporal_dropout`
7. `edge+dim+low_contrast+temporal_dropout`
8. `small_scale+oblique+blur_noise+temporal_dropout`

### Protected-validation compositions

1. `edge+low_contrast+temporal_dropout`
2. `small_scale+oblique+temporal_dropout`
3. `dim+low_contrast+temporal_dropout`
4. `blur_noise+low_contrast+temporal_dropout`
5. `edge+small_scale+oblique+temporal_dropout`
6. `edge+oblique+dim+blur_noise+temporal_dropout`
7. `small_scale+dim+blur_noise+low_contrast+temporal_dropout`
8. `edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout`

Protected validation seed `440440` must not be generated before the exact P9 candidate-freeze checkpoint.

## Frozen inherited front end

P9 inherits the same procedural perception-response generator and unchanged non-recursive two-frame temporal bridge.

Only genuine candidate perception outputs may become motion-history anchors.

- inherited bridge outputs are never anchors;
- P9 continuity outputs are never anchors;
- future observations, future reacquisition, domain labels, family IDs, truth state, true anchor error, and future true error are forbidden continuity inputs.

## Fit-frozen motion and innovation scales

### Velocity cap

Using only consecutive genuine-anchor pairs on the P9 fit split, freeze the empirical `99th` percentile of absolute per-frame slope independently for lateral and altitude axes.

`velocity_cap_quantile = 0.99`

### Innovation scale

Using only genuine-anchor triples `(A,B,C)` on the P9 fit split:

1. compute `m_prev = (B-A)/(t_B-t_A)`;
2. clip `m_prev` to the fit-frozen velocity cap;
3. predict `C_pred = B + m_prev*(t_C-t_B)`;
4. compute signed innovation `e = C_observed - C_pred`.

Freeze the empirical `95th` percentile of `abs(e)` independently by axis.

`innovation_scale_quantile = 0.95`

The innovation scale is not a hard clipping threshold in P9.

## P9 soft bounded-influence newest-anchor update

### Three-or-more-anchor state

For the latest genuine-anchor triple `(A,B,C)`, independently by axis:

1. `m_prev = clip((B-A)/(t_B-t_A), +/- velocity_cap)`
2. `C_pred = B + m_prev*(t_C-t_B)`
3. `e = C_observed - C_pred`
4. `s = innovation_scale`
5. `e_soft = e / sqrt(1 + (e/(3*s))^2)`
6. `C_state = C_pred + e_soft`
7. `m_latest = (C_state-B)/(t_C-t_B)`
8. `m_blend = 0.5*m_prev + 0.5*m_latest`
9. `m_state = clip(m_blend, +/- velocity_cap)`

Fixed constants:

- `soft_scale_multiplier = 3.0`
- previous-slope blend weight: `0.50`
- soft-updated-slope blend weight: `0.50`

This influence function is smooth. It approaches the raw innovation for small `|e|` and bounds the effective innovation continuously toward `+/-3*s` for extreme `|e|`. There is no hard discontinuous innovation clip.

Define the causal measurement gain for diagnostics:

- if `e != 0`: `gain = e_soft/e`;
- if `e == 0`: `gain = 1`.

### Exactly two genuine anchors

Use the newest genuine anchor as the state and their two-point slope clipped to the velocity cap. Innovation is marked unavailable and gain is `1`.

With fewer than two genuine anchors, P9 cannot create continuity.

### Horizon and damping

The inherited bridge remains authoritative at horizons `1..2`.

P9 continuity may act only for total horizons `3..7` inclusive.

- `max_continuity_gap = 7`
- `damping = 0.85`

For horizon `h`:

`estimate_h = C_state + m_state * sum(0.85^k for k=0..h-1)`

P9 continuity is non-recursive.

## Direct grouped conformal uncertainty

P9 deliberately contains **no learned error-scale model, no adaptation correction, and no post-hoc transfer multiplier**.

Intervals are constant within one of four preregistered groups and vary only by axis and target coverage.

### Fixed groups

1. `base_output` — every available non-P9-continuity output;
2. `continuity_h3` — P9 continuity at horizon exactly 3;
3. `continuity_h45` — P9 continuity at horizons 4 or 5;
4. `continuity_h67` — P9 continuity at horizons 6 or 7.

There is no pooled fallback and no data-dependent regrouping.

### Calibration rule

On grouped-calibration seed `418418`, for each group, axis, and target `q` in `{0.50,0.68,0.80,0.90,0.95}`:

1. collect `abs_error` from truth-visible available rows in that exact group;
2. sort finite residuals;
3. use finite-sample conformal order statistic `ceil((n+1)*q)`;
4. freeze the selected absolute-error radius.

Radii are monotonized by cumulative maximum over increasing target coverage.

No information from transfer seed `429429` may alter these radii.

### Required grouped-calibration sample sizes

Before a P9 candidate exists, grouped calibration must contain at least:

- `base_output >= 1000` rows;
- `continuity_h3 >= 120` rows;
- `continuity_h45 >= 60` rows;
- `continuity_h67 >= 30` rows.

If any minimum fails, P9 development stops and protected validation is not exposed.

### Required seen-transfer sample sizes

For the transfer gate set to be considered evaluable, seed `429429` must contain at least:

- `base_output >= 800` rows;
- `continuity_h3 >= 100` rows;
- `continuity_h45 >= 50` rows;
- `continuity_h67 >= 20` rows.

If any minimum fails, P9 development stops and protected validation is not exposed.

## Primary gates

The frozen candidate is evaluated first on the untouched seen-transfer split. Only if H1-H6 pass may protected validation be exposed once.

### H1 — useful availability

Truth-visible output availability `>=0.92`.

### H2 — overall 95% coverage

Both lateral and altitude empirical 95% coverage must be in `[0.90,0.98]`.

### H3 — overall calibration curve

Mean absolute coverage error across targets `{50%,68%,80%,90%,95%}` over both axes must be `<=0.06`.

### H4 — overall interval efficiency

Across all available outputs, for each axis:

- median 95% half-width / all-available p95 absolute error `<=1.25`;
- p95 95% half-width / all-available p95 absolute error `<=2.25`.

### H5 — continuity-specific honesty

Across all P9 continuity rows combined:

- lateral 95% coverage in `[0.88,0.99]`;
- altitude 95% coverage in `[0.88,0.99]`;
- p95 95% half-width / continuity p95 absolute error `<=2.75` on both axes.

### H6 — base-output honesty

On `base_output` rows only:

- lateral and altitude 95% coverage each in `[0.90,0.98]`;
- p95 95% half-width / base-output p95 absolute error `<=2.25` on both axes.

### H7 — shift discrimination

Trajectory-level mean inherited severity must distinguish fit/single-factor regime from seen compositional transfer with AUROC `>=0.85`.

H7 is diagnostic only and does not establish safety.

## Secondary diagnostics

Report but do not use for candidate retuning:

- each of the four group row counts;
- 95% coverage and p95 width/error ratio in each continuity horizon group;
- point MAE/p95 by horizon;
- measurement-gain distributions by axis;
- fraction of rows with gain `<0.9`, `<0.75`, and `<0.5`;
- velocity-cap utilization distributions;
- unavailable rows by `insufficient_anchors` and `gap_beyond_horizon`;
- descriptive point-error comparison against P8 hard-clipped continuity on the same fresh P9 rows where both methods produce an estimate.

## Candidate-freeze checkpoint

After this preregistration, P9 may generate fit and grouped-calibration evidence and freeze a candidate consisting only of:

- exact scientific-code commit;
- all seeds/families/domains;
- velocity caps;
- innovation scales;
- fixed soft-update constants;
- the four-group direct conformal radius table;
- grouped-calibration row counts;
- SHA-256 manifest and workflow artifact digest.

The candidate may then be evaluated once on seen transfer seed `429429` without changing anything.

If any grouped-calibration/transfer minimum or any H1-H6 seen-transfer gate fails, protected validation seed `440440` must not be exposed.

If all H1-H6 pass, the exact frozen candidate may be evaluated exactly once on protected seed `440440`.

## Exposure policy

After grouped-calibration seed `418418` is generated it is permanently seen calibration evidence.

After transfer seed `429429` is generated it is permanently seen development evidence.

After protected validation seed `440440` is generated it is permanently seen validation evidence regardless of result.

No method change may be re-evaluated on an exposed P9 split as if unseen.

Even a complete P9 protected-validation pass does **not** authorize the final Phase 11 frozen holdout. That final holdout remains behind a separate explicit user approval at an exact future freeze checkpoint.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
- failed/mixed results remain permanent evidence
