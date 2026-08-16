# Phase 11 P8 preregistration — innovation-clipped continuity

## Status

**PREREGISTERED BEFORE P8 DATA GENERATION**

Branch: `phase11-p8-innovation-clipped-continuity`

P7 is frozen as a development stop. P7 fit/calibration/adaptation/transfer seeds `297297`, `308308`, `319319`, and `330330` are permanently seen. P7 protected seed `341341` was never exposed and is retired rather than recycled.

All prior Phase 11 exposed evidence is permanently seen and may motivate P8 only. No prior row, threshold, fitted coefficient, calibration residual, or hidden-test label may be reused as P8 fitting/calibration/validation evidence.

## Research question

**Can an explicitly innovation-bounded causal anchor state prevent a bad newest genuine observation from poisoning short-gap continuity, while preserving honest uncertainty and at least 92% perception availability under fresh unseen compositional shift?**

P8 remains a simulation-only perception/reliability experiment. It does not modify or validate an aircraft controller.

## Why P8 exists

P6 protected validation showed that base-output uncertainty still transferred while continuity altitude calibration collapsed. Read-only forensics implicated poor newest-anchor quality and high slope-cap usage.

P7 then failed before candidate freeze for two reasons:

1. its disjoint adaptation population had only `38` robust-continuity rows versus the preregistered `80` minimum;
2. the proposed three-anchor median-pairwise trend had a direct counterexample where a bad newest anchor still became the extrapolation state.

P8 therefore makes the continuity state explicitly **innovation clipped**, and increases the number of fresh adaptation/transfer trajectories rather than relaxing sample-size requirements after exposure.

## New P8 evidence boundary

All P8 seeds and families are fresh.

- fit seed: `352352`
- single-factor calibration seed: `363363`
- continuity-adaptation seed: `374374`
- compositional transfer-calibration seed: `385385`
- protected validation seed: `396396`
- frames per sequence: `60`

Families are disjoint:

- fit: `120..125` (`6` families)
- calibration: `126..128` (`3` families)
- adaptation: `129..137` (`9` families)
- transfer calibration: `138..143` (`6` families)
- protected validation: `144..149` (`6` families)

The sequence is the split unit. Adjacent frames from one sequence may not be split across evidence roles.

### Fit / single-factor calibration domains

1. `nominal`
2. `edge`
3. `small_scale`
4. `oblique`
5. `dim`
6. `blur_noise`
7. `temporal_dropout`
8. `low_contrast`

### Seen adaptation compositions

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
6. `small_scale+blur_noise+temporal_dropout`
7. `edge+dim+low_contrast+temporal_dropout`
8. `small_scale+oblique+blur_noise+temporal_dropout`

### Protected validation compositions

1. `edge+low_contrast+temporal_dropout`
2. `small_scale+oblique+temporal_dropout`
3. `dim+low_contrast+temporal_dropout`
4. `blur_noise+low_contrast+temporal_dropout`
5. `edge+small_scale+oblique+temporal_dropout`
6. `edge+oblique+dim+blur_noise+temporal_dropout`
7. `small_scale+dim+blur_noise+low_contrast+temporal_dropout`
8. `edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout`

Protected validation seed `396396` must not be generated before an exact candidate-freeze checkpoint.

## Frozen inherited front end

P8 inherits the existing synthetic perception response generator and unchanged non-recursive two-frame bridge.

Only genuine candidate observations may become anchor history.

- two-frame bridge outputs are never anchors;
- P8 continuity outputs are never anchors;
- truth state, true error, domain name, family ID, future frames, and future reacquisition are forbidden continuity inputs.

## Fit-frozen anchor statistics

P8 derives two kinds of per-axis caps from the fresh fit split only.

### Velocity cap

Using consecutive genuine anchors, compute absolute per-frame slopes and freeze the empirical `99th` percentile independently for lateral and altitude.

### Innovation cap

Whenever at least three genuine anchors `(a,b,c)` exist, use the two anchors before the newest anchor to predict the newest:

`pred_c = b + ((b-a)/(t_b-t_a)) * (t_c-t_b)`

Compute absolute innovation:

`innovation = abs(c - pred_c)`

Freeze the empirical **95th percentile** of fit-split genuine-anchor innovation independently for lateral and altitude.

These velocity and innovation caps are frozen before P8 adaptation, transfer, and validation.

## P8 innovation-clipped anchor state

P8 continuity is calculated independently by axis.

### Three-or-more-anchor state

For the latest three genuine anchors `(a,b,c)`:

1. previous slope:
   `m_prev = (b-a)/(t_b-t_a)`
2. predict newest anchor:
   `pred_c = b + m_prev*(t_c-t_b)`
3. raw newest innovation:
   `e = c - pred_c`
4. clipped innovation:
   `e_clip = clip(e, -innovation_cap, +innovation_cap)`
5. corrected newest state:
   `c_corrected = pred_c + e_clip`
6. corrected newest slope:
   `m_new = (c_corrected-b)/(t_c-t_b)`
7. blended continuity slope:
   `m = 0.5*m_prev + 0.5*m_new`
8. clip `m` to the fit-frozen velocity cap.

The continuity intercept/state is `c_corrected`, not the raw newest observation.

### Exactly-two-anchor state

With exactly two genuine anchors, use their ordinary two-point slope, clipped to the fit-frozen velocity cap, and use the newest genuine estimate as the state. Innovation is marked unavailable.

With fewer than two genuine anchors, P8 cannot create a continuity output.

### Bounded horizon and damping

The inherited two-frame bridge remains authoritative for horizons 1–2.

P8 continuity acts only when that bridge has no estimate.

- P8 continuity horizons: `3..7` inclusive;
- damping factor: `0.85`;
- no recursive continuation from P8 outputs.

For total gap horizon `h`:

`estimate_h = corrected_latest_state + m * sum(0.85^k for k=0..h-1)`

## Inference-visible P8 reliability features

All are causal.

- eight inherited risk components;
- scalar risk score;
- normalized coactivation count;
- largest and second-largest primary risk components;
- P8 continuity horizon;
- lateral and altitude slope-cap utilization in `[0,1]`;
- lateral and altitude raw newest-anchor innovation magnitude;
- lateral and altitude innovation-cap utilization, defined as `min(3.0, abs(raw_innovation)/innovation_cap)`;
- anchor-innovation-available indicator;
- source category.

Truth anchor error is forbidden.

## P8 base scale model

Separate lateral/altitude log-error scale models use the same low-capacity principles as P5–P7:

- fit only on fresh fit split;
- standardized causal basis;
- target `log(abs_error + 1e-4)`;
- target winsorization at empirical `2nd` / `98th` percentiles;
- ridge lambda `4.0`;
- fitted-log-scale q01/q99 guard expanded by `0.35`;
- source one-hots for partial-edge, center-regeometry, known-ArUco-refined, inherited temporal bridge, and `innovation_clipped_continuity`.

## Disjoint continuity-adaptation correction

P8 keeps the P7 principle of fitting a continuity-specific correction only on a separate adaptation split.

### Population and sample minimum

Use truth-visible available `innovation_clipped_continuity` rows from adaptation seed `374374` only.

Minimum adaptation continuity rows: **`90`**.

If fewer than 90 exist, P8 development stops and protected validation is not exposed.

### Correction target

For each axis:

`target = log(abs_error / max(base_predicted_scale,1e-9) + 1e-4)`

### Correction basis

- continuity horizon;
- lateral and altitude slope-cap utilization;
- lateral and altitude raw innovation magnitude;
- lateral and altitude innovation-cap utilization;
- innovation-available indicator;
- scalar risk score;
- normalized coactivation count.

### Correction fit

- standardized on adaptation continuity rows only;
- separate lateral/altitude ridge models;
- ridge lambda `4.0`;
- target winsorization q02/q98;
- fitted correction q01/q99 guard expanded by `0.35`.

Non-continuity rows receive correction factor exactly `1.0`.

## Single-factor conformal calibration

After fitting the base and adaptation models, use the fresh single-factor calibration split to freeze finite-sample conformal quantiles at targets:

`{0.50,0.68,0.80,0.90,0.95}`

with order statistic `ceil((n+1)*q)`.

Normalized residual:

`abs_error / max(corrected_predicted_scale,1e-9)`

## Source-conditional transfer calibration

The fresh transfer split freezes exactly two groups:

- `base_output`
- `innovation_clipped_continuity`

Minimum transfer rows:

- base output: `400`;
- continuity: **`60`**.

No pooled fallback is allowed.

For each group/axis/target:

`R_single = corrected_scale * Q_single(axis,q)`

`transfer_ratio = abs_error / max(R_single,1e-9)`

Freeze finite-sample conformal multiplier `T(group,axis,q)`.

Final interval radius:

`R_P8 = corrected_scale * Q_single * T(group,axis,q)`

Radii are monotonized by cumulative maximum over increasing target coverage.

## Primary gates

The same gates are evaluated on seen transfer calibration and, only if development passes, on one protected validation exposure.

### H1 — useful availability

Truth-visible output availability `>=0.92`.

### H2 — overall 95% coverage

Both axes in `[0.90,0.98]`.

### H3 — calibration curve quality

Mean absolute coverage error across `{50%,68%,80%,90%,95%}` over both axes `<=0.06`.

### H4 — overall interval efficiency

For each axis:

- median 95% half-width / all-available p95 error `<=1.25`;
- p95 95% half-width / all-available p95 error `<=2.25`.

### H5 — continuity-specific honesty

On `innovation_clipped_continuity` rows only:

- 95% coverage in `[0.88,0.99]` on both axes;
- p95 95% half-width / continuity p95 error `<=2.75` on both axes.

### H6 — base-output honesty

On `base_output` rows only:

- 95% coverage in `[0.90,0.98]` on both axes;
- p95 95% half-width / base-output p95 error `<=2.25` on both axes.

### H7 — shift discrimination

Trajectory-level mean inherited severity AUROC `>=0.85` between single-factor calibration and compositional evaluation. Diagnostic only.

## Secondary diagnostics

Report without candidate tuning:

- continuity rows by horizon;
- unavailable rows by `insufficient_anchors` vs `gap_beyond_horizon`;
- innovation magnitude/utilization distributions;
- slope-cap-utilization distributions;
- continuity point MAE/p95 by horizon;
- fraction of continuity rows whose innovation is clipped;
- on identical fresh P8 rows, diagnostic point-error comparison against the frozen P5 newest-anchor-intercept continuation where both produce an estimate.

## Candidate-freeze rule

P8 may generate fit, calibration, adaptation, and seen transfer evidence only after this preregistration commit.

Before protected validation, freeze:

- exact code commit;
- all seeds/families/domains;
- velocity caps;
- innovation caps;
- all fixed continuity constants;
- base model coefficients/standardizer/guards;
- adaptation correction coefficients/standardizer/guards;
- single-factor conformal quantiles;
- two transfer multiplier tables;
- adaptation and transfer row counts;
- seen transfer gate metrics;
- SHA-256 manifest and workflow artifact digest.

If either sample-size minimum or any H1–H6 transfer gate fails, protected validation seed `396396` must not be exposed.

If all H1–H6 pass, the exact frozen candidate may be evaluated exactly once on protected seed `396396` with no scientific changes.

## Exposure policy

After adaptation seed `374374` is generated it is permanently seen fitting evidence.

After transfer seed `385385` is generated it is permanently seen calibration/development evidence.

After protected validation seed `396396` is generated it is permanently seen validation evidence regardless of outcome.

No P8 method change may be re-evaluated on an exposed P8 split as if unseen.

Even a successful P8 protected validation does **not** authorize a final Phase 11 frozen holdout. A final holdout remains behind a separate explicit user approval at an exact future freeze checkpoint.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
- negative/mixed/failed results remain permanent evidence
