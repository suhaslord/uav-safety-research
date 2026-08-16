# Phase 11 P4 preregistration — all-available calibrated uncertainty

## Status

**PREREGISTERED BEFORE P4 DATA GENERATION**

Branch: `phase11-p4-all-available-calibration`

All previously exposed Phase 11 evidence remains permanently seen. In particular, P0 `33033`, duplicate `63333`, P1 `77077`, P2 transfer `101101`, and P3 transfer `143143` may not be used as hidden evidence. P2 `112112` and P3 `154154` were never generated and are retired rather than recycled.

## Research question

**Can AegisLand provide honest and efficient uncertainty on every estimate its simulation-only perception layer can produce under unseen compositional shift, without a hard reliability accept/reject gate?**

P4 treats calibrated uncertainty itself as the reliability output. Availability is therefore determined only by whether the frozen perception/short-horizon bridge produces an estimate; there is no severity threshold or interval-width abstention in the primary method.

## Motivation

P1 showed that a binary severity gate collapsed usable availability despite strong shift discrimination. P2 removed that gate but inherited a hand-written risk multiplier that created extreme interval tails. P3 removed the hand multiplier and reduced the p95 interval-tail ratios dramatically, but still narrowly missed the lateral tail-efficiency gate on seen transfer data.

P4 makes one further principled change: regularize the learned scale model against extrapolation by using a simpler standardized basis and robustly bounded log-error targets. Two-stage conformal calibration remains responsible for coverage.

## New P4 evidence boundary

All seeds and trajectory families are new.

- fit seed: `165165`
- single-factor calibration seed: `176176`
- compositional transfer-calibration seed: `187187`
- protected validation seed: `198198`
- frames per sequence: `60`

Families are disjoint:

- fit: `57..62`
- calibration: `63..65`
- transfer calibration: `66..68`
- protected validation: `69..71`

The complete sequence is the split unit.

### Fit / calibration domains

1. `nominal`
2. `edge`
3. `small_scale`
4. `oblique`
5. `dim`
6. `blur_noise`
7. `temporal_dropout`
8. `low_contrast`

### Seen transfer-calibration compositions

1. `edge+small_scale`
2. `oblique+dim`
3. `blur_noise+temporal_dropout`
4. `small_scale+low_contrast`
5. `edge+oblique+blur_noise`
6. `small_scale+dim+temporal_dropout`
7. `edge+blur_noise+low_contrast`
8. `oblique+dim+low_contrast`

### Protected validation compositions

1. `edge+oblique`
2. `small_scale+temporal_dropout`
3. `dim+low_contrast`
4. `edge+small_scale+blur_noise`
5. `oblique+dim+temporal_dropout`
6. `small_scale+blur_noise+low_contrast`
7. `edge+oblique+dim+low_contrast`
8. `edge+small_scale+oblique+blur_noise+temporal_dropout`

Protected validation seed `198198` must not be generated before the P4 candidate-freeze checkpoint.

## Frozen estimator layer

P4 inherits unchanged from P1/P3:

- factor-identifiable appearance cues;
- non-recursive constant-velocity bridge, maximum horizon `2`;
- eight causal risk components;
- detector/source category;
- candidate point estimates.

No controller behavior changes.

## P4 robust scale model

Separate lateral and altitude models predict log absolute error scale.

### Fixed feature basis

Continuous basis before standardization:

1. eight P1 risk components: edge, scale, oblique, dim, blur, contrast, temporal, track;
2. scalar risk score;
3. normalized coactivation count `coactivation_count / 7`;
4. largest primary risk component;
5. second-largest primary risk component;
6. bridge horizon.

Categorical source one-hots are appended for:

- partial-edge;
- center-regeometry;
- known-ArUco-refined;
- temporal-bridge.

An intercept is included.

P4 intentionally removes quadratic risk/coactivation terms and bridge×risk interaction from P3 to reduce extrapolative leverage.

### Standardization

Fit-split means and standard deviations for continuous basis features are frozen. Standard deviations below `1e-6` are replaced by `1.0`.

### Robust log-error target

For each axis on available truth-visible fit observations:

`y = log(abs_error + 1e-4)`

Freeze the empirical `2nd` and `98th` percentiles of y and winsorize y to those bounds before fitting.

### Ridge fit

Fixed ridge lambda: `4.0`.

The intercept is not penalized. All other coefficients use the same L2 penalty.

### Prediction guard

On the fit split, compute fitted log-scale predictions and freeze their empirical `1st` and `99th` percentiles. At inference, predicted log-scale is clipped to:

`[fit_q01 - 0.35, fit_q99 + 0.35]`

before exponentiation.

This guard is fixed before transfer/validation exposure and prevents a small number of extrapolative feature combinations from producing unbounded interval tails. It is not tuned on challenge error.

## Two-stage conformal calibration

### Single-factor stage

On all available truth-visible calibration rows:

`normalized_residual = abs_error / max(predicted_scale, 1e-9)`

For targets `{0.50,0.68,0.80,0.90,0.95}`, freeze finite-sample conformal quantiles using order statistic `ceil((n+1)*q)`.

### Compositional transfer stage

On all available truth-visible seen transfer rows:

`R_single(axis,q) = predicted_scale * Q_single(axis,q)`

`transfer_ratio = abs_error / max(R_single, 1e-9)`

Freeze `T(axis,q)` as the finite-sample q conformal quantile of transfer ratios.

Final radius:

`R_P4(axis,q) = predicted_scale * Q_single(axis,q) * T(axis,q)`

Final radii are monotonized by cumulative maximum across increasing q to guarantee nested intervals.

## Primary method

P4 evaluates **every available estimate**. There is no severity cutoff and no uncertainty-width abstention in the primary gate set.

An optional interval-width flag may be reported as a secondary diagnostic only; it may not remove observations from the primary coverage/efficiency metrics.

## Primary gates

### H1 — 95% coverage transfer

On every available protected-validation estimate, 95% empirical coverage must be in `[0.90,0.98]` on both lateral and altitude axes.

### H2 — calibration curve quality

Mean absolute coverage error across targets `{50%,68%,80%,90%,95%}` over both axes must be `<=0.06`.

### H3 — interval efficiency

On every available protected-validation estimate:

- median 95% half-width / all-available p95 absolute error `<=1.25` on each axis;
- p95 95% half-width / all-available p95 absolute error `<=2.25` on each axis.

All four conditions must pass.

### H4 — useful estimator availability

Preselection truth-visible availability from the unchanged perception + short bridge must be `>=0.90`.

No additional reliability gate may reduce this number for the primary P4 result.

### H5 — shift discrimination remains informative

Trajectory-level mean P1 severity must distinguish P4 single-factor calibration from protected compositional validation with AUROC `>=0.85`.

H5 is diagnostic; it does not establish safety.

## Candidate-freeze checkpoint

Fit, calibration, and seen transfer rows may be generated after this preregistration. Freeze and archive:

- feature means/stds;
- winsorization bounds;
- prediction guard bounds;
- ridge coefficients;
- single-factor conformal quantiles;
- transfer multipliers;
- seen transfer gate metrics;
- exact code commit.

If the seen transfer split fails H1, H2, H3, or H4, protected validation seed `198198` should not be exposed.

If all development gates pass, the frozen candidate may proceed to the preregistered protected validation split without changing any method constant.

## Validation exposure policy

Once seed `198198` is generated/evaluated it becomes permanently seen. No P4 method, gate, basis, winsor bound, prediction guard, ridge lambda, conformal rule, or transfer rule may change and then be evaluated again on `198198` as unseen evidence.

Passing P4 protected validation would still **not** authorize the final Phase 11 frozen holdout. A separate explicit user approval is required before any final protected Phase 11 holdout is generated.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
- negative and mixed outcomes remain permanent evidence
