# Phase 11 P7 preregistration — powered horizon-aware calibration

## Status

**PREREGISTERED BEFORE P7 DATA GENERATION**

Branch: `phase11-p7-powered-horizon-calibration`

All previously exposed Phase 11 evidence remains permanently seen. P6 transfer seed `275275` is seen; P6 development `286286` and validation `297297` were never generated and are retired.

## Research question

**With enough preregistered long-bridge calibration examples, can the P5 continuity estimator plus horizon-group conformal transfer deliver honest, efficient uncertainty on unseen compositions while preserving >=90% availability?**

P7 does not loosen P6's minimum-support rule and does not change the P5 point estimator. It changes only the amount and composition of transfer-calibration evidence.

## New P7 evidence boundary

All seeds and trajectory families are new.

- fit seed: `308308`
- single-factor calibration seed: `319319`
- compositional transfer-calibration seed: `330330`
- independent development-challenge seed: `341341`
- protected-validation seed: `352352`
- frames per sequence: `60`

Trajectory families:

- fit: `105..110`
- calibration: `111..113`
- transfer calibration: `114..119` (**six families**, twice P6's transfer-family count)
- development challenge: `120..122`
- protected validation: `123..125`

Complete sequences are the split unit.

## Domain sets

### Fit / single-factor calibration

1. `nominal`
2. `edge`
3. `small_scale`
4. `oblique`
5. `dim`
6. `blur_noise`
7. `temporal_dropout`
8. `low_contrast`

### Seen transfer-calibration compositions

The transfer panel is intentionally enriched for conditions that produce missing-frame runs; this is calibration evidence, not hidden evaluation evidence.

1. `edge+temporal_dropout`
2. `small_scale+temporal_dropout`
3. `oblique+temporal_dropout`
4. `dim+temporal_dropout`
5. `blur_noise+temporal_dropout`
6. `low_contrast+temporal_dropout`
7. `edge+blur_noise+temporal_dropout`
8. `small_scale+dim+temporal_dropout`

### Independent development-challenge compositions

1. `edge+dim`
2. `small_scale+blur_noise`
3. `oblique+low_contrast`
4. `edge+small_scale+blur_noise`
5. `oblique+dim+temporal_dropout`
6. `edge+low_contrast+temporal_dropout`
7. `small_scale+oblique+dim`
8. `edge+small_scale+oblique+low_contrast+temporal_dropout`

### Protected-validation compositions

1. `edge+small_scale`
2. `oblique+dim`
3. `blur_noise+low_contrast`
4. `small_scale+dim+temporal_dropout`
5. `edge+oblique+blur_noise`
6. `dim+low_contrast+temporal_dropout`
7. `small_scale+oblique+blur_noise+low_contrast`
8. `edge+small_scale+oblique+dim+temporal_dropout`

## Frozen continuity estimator

P7 inherits the P5 continuity rule unchanged in form:

- maximum bridge horizon `5`;
- only direct observations enter velocity history;
- one-direct-observation hold-last only at horizon `1`;
- otherwise constant-velocity extrapolation from the two most recent direct observations;
- per-axis velocity clipped to fit-only q99 direct transition rates;
- bridged outputs never feed future velocity history.

Fit-derived velocity caps are recomputed only from the new P7 fit split and frozen before later exposures.

## Base uncertainty model

P7 inherits the P5 robust scale-model form unchanged:

- eight causal risk components;
- risk score;
- normalized coactivation count;
- top two primary risks;
- bridge horizon / 5;
- source one-hots;
- fit standardization;
- q02/q98 winsorized log-error target;
- ridge lambda `4.0`;
- fit prediction q01/q99 guard plus/minus `0.35` log units;
- no hand-written multiplicative risk inflation.

## Single-factor conformal stage

Using all available truth-visible single-factor calibration rows, freeze finite-sample normalized-residual conformal quantiles at targets `{0.50,0.68,0.80,0.90,0.95}`.

## Horizon groups

- `direct_short`: bridge horizon `0..2`;
- `long`: bridge horizon `3..5`.

## Horizon-aware transfer calibration

On seen transfer-calibration rows, for each axis, target, and horizon group:

`R_single = predicted_scale * Q_single(axis,q)`

`transfer_ratio = abs_error / max(R_single,1e-9)`

Freeze:

`T(axis,q,group) = finite_sample_conformal_q(transfer_ratio | group)`

The minimum support remains **40 available observations per horizon group**. This threshold is not lowered from P6.

Final P7 radius:

`R_P7(axis,q) = predicted_scale * Q_single(axis,q) * T(axis,q,horizon_group)`

Target radii are monotonized across increasing q for interval nesting.

There is no hard severity or interval-width rejection in the primary method.

## Candidate-freeze checkpoint

After fit + single-factor calibration + transfer calibration only, freeze:

- velocity caps;
- scale-model standardization/winsor/prediction-guard values and coefficients;
- single-factor conformal quantiles;
- horizon-specific transfer multipliers;
- horizon-group calibration counts;
- exact code SHA.

At freeze, neither development seed `341341` nor protected seed `352352` may have been generated.

If either horizon group has fewer than `40` available transfer rows, candidate freeze fails and both later seeds remain ungenerated.

## Independent development challenge

After candidate freeze, evaluate the unchanged candidate exactly once on `341341`. That seed then becomes permanently seen.

All D1-D7 gates below must pass before protected validation is allowed.

### D1 — availability

Estimate availability `>=90%`.

### D2 — overall 95% coverage

Both axes in `[0.90,0.98]`.

### D3 — calibration curve

MACE over `{50%,68%,80%,90%,95%}` and both axes `<=0.06`.

### D4 — interval efficiency

- median 95% half-width / all-available p95 error `<=1.25` each axis;
- p95 95% half-width / p95 error `<=2.25` each axis.

### D5 — long-bridge calibration

At least `40` available horizon-3..5 observations, with:

- 95% coverage in `[0.90,0.99]` both axes;
- p95 95% half-width / long-bridge p95 error `<=2.50` both axes.

### D6 — direct/short calibration

Horizon-0..2 95% coverage in `[0.90,0.98]` both axes.

### D7 — shift discrimination

Trajectory-level mean P1-style severity AUROC `>=0.85` between single-factor calibration and development challenge.

If any development gate fails, seed `352352` must remain ungenerated and be retired.

## Protected validation

Only if D1-D7 all pass may the exact frozen candidate be evaluated once on seed `352352`.

Protected-validation gates are identical to D1-D7. No method constant may change between development challenge and protected validation.

## Exposure policy

- transfer seed `330330` becomes seen during calibration;
- development seed `341341` becomes permanently seen on first development evaluation;
- protected seed `352352` is exposed only after all independent development gates pass.

Any method change after the development challenge requires P8 with new evidence.

Even a P7 protected-validation pass **does not authorize the final Phase 11 frozen holdout**; that final holdout requires a separate explicit user approval checkpoint.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
- negative/mixed results remain permanent evidence
