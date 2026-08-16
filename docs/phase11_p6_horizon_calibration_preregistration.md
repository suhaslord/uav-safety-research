# Phase 11 P6 preregistration — horizon-aware uncertainty calibration

## Status

**PREREGISTERED BEFORE P6 DATA GENERATION**

Branch: `phase11-p6-horizon-calibration`

All prior Phase 11 challenge/validation evidence is permanently seen. In particular P0 `33033`, duplicate `63333`, P1 `77077`, P2 transfer `101101`, P3 transfer `143143`, P4 validation `198198`, and P5 transfer `231231` may not be reused as hidden evidence. P2 `112112`, P3 `154154`, and P5 `242242` remain ungenerated and are retired.

## Research question

**Can the P5 five-frame continuity layer retain its availability gain while separate conformal transfer calibration for direct/short versus long bridge states restores honest long-horizon uncertainty on unseen compositional shifts?**

P6 does not change the raw perception generator, bridge horizon, bridge point-estimation rule, or controller behavior. It changes only uncertainty calibration by recognizing that horizon `3..5` bridge estimates form a different uncertainty regime from direct and short (`0..2`) estimates.

## Motivation from frozen P5 development evidence

P5 seen transfer calibration produced:

- estimator availability `99.51%`;
- overall 95% coverage `95.12%` lateral / `95.12%` altitude;
- calibration MACE `0.000923`;
- efficient p95 interval ratios `1.594x` lateral / `1.453x` altitude;
- long-bridge count `42`;
- long-bridge lateral coverage `88.10%`;
- long-bridge altitude coverage `85.71%`.

The only failed P5 development gate was long-horizon altitude coverage. P6 therefore keeps the P5 estimator/continuity behavior fixed and changes only calibration granularity.

## New P6 evidence boundary

All seeds and trajectory families are new.

- fit seed: `253253`
- single-factor calibration seed: `264264`
- compositional transfer-calibration seed: `275275`
- independent development-challenge seed: `286286`
- protected-validation seed: `297297`
- frames per sequence: `60`

Trajectory families are disjoint:

- fit: `87..92`
- calibration: `93..95`
- transfer calibration: `96..98`
- development challenge: `99..101`
- protected validation: `102..104`

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

1. `edge+temporal_dropout`
2. `dim+temporal_dropout`
3. `blur_noise+temporal_dropout`
4. `small_scale+temporal_dropout`
5. `edge+blur_noise`
6. `oblique+dim`
7. `edge+small_scale+temporal_dropout`
8. `oblique+blur_noise+temporal_dropout`

### Independent development-challenge compositions

These are not used for fitting or calibration:

1. `edge+dim`
2. `small_scale+blur_noise`
3. `oblique+low_contrast`
4. `edge+low_contrast+temporal_dropout`
5. `small_scale+dim+temporal_dropout`
6. `edge+oblique+blur_noise`
7. `dim+blur_noise+temporal_dropout`
8. `edge+small_scale+oblique+low_contrast+temporal_dropout`

### Protected-validation compositions

These must not be generated before the development challenge passes with the frozen candidate:

1. `edge+small_scale`
2. `oblique+temporal_dropout`
3. `dim+low_contrast`
4. `edge+blur_noise+temporal_dropout`
5. `small_scale+oblique+dim`
6. `blur_noise+low_contrast+temporal_dropout`
7. `edge+oblique+dim+low_contrast`
8. `edge+small_scale+oblique+blur_noise+temporal_dropout`

## Frozen continuity layer

P6 inherits the P5 point-estimation architecture, refit only where the preregistration requires fit-derived constants:

- maximum bridge horizon `5`;
- only direct observations enter velocity history;
- one-direct-observation hold-last allowed only at horizon `1`;
- with two direct observations, constant-velocity extrapolation is used;
- lateral/altitude velocity caps are independently frozen at fit-split q99 direct per-frame changes;
- bridged estimates never recursively feed future velocity estimation.

No point-estimator choice is made from P6 development-challenge or validation results.

## Base uncertainty model

P6 uses the P5 robust scale model unchanged in form:

- eight causal risk components;
- risk score;
- normalized coactivation count;
- largest and second-largest primary risk components;
- bridge horizon normalized by `5`;
- source one-hots;
- fit standardization;
- q02/q98 winsorized log-error target;
- ridge lambda `4.0`;
- fit-prediction q01/q99 guard expanded by `0.35` log units;
- no hand-written multiplicative risk inflation.

## Single-factor conformal stage

On every available truth-visible single-factor calibration row:

`normalized_residual = abs_error / max(predicted_scale, 1e-9)`

For targets `{0.50,0.68,0.80,0.90,0.95}`, freeze finite-sample conformal quantiles using order statistic `ceil((n+1)*q)`.

## Horizon group

Each available estimate belongs to exactly one group using only inference-visible bridge state:

- `direct_short`: bridge horizon `0,1,2`;
- `long`: bridge horizon `3,4,5`.

## Horizon-aware compositional transfer calibration

For each axis, target q, and horizon group, on the seen transfer-calibration split compute:

`R_single = predicted_scale * Q_single(axis,q)`

`transfer_ratio = abs_error / max(R_single, 1e-9)`

Freeze a separate finite-sample conformal multiplier:

`T(axis,q,group) = conformal_q(transfer_ratio | group)`

A group must contain at least `40` available transfer-calibration observations. If the `long` group has fewer than `40`, P6 is insufficiently calibrated and protected validation may not be exposed.

Final radius:

`R_P6(axis,q) = predicted_scale * Q_single(axis,q) * T(axis,q,horizon_group)`

Final target radii are monotonized by cumulative maximum across increasing q for every observation.

There is no severity threshold or interval-width abstention in the primary method.

## Candidate-freeze checkpoint

After fit, calibration, and transfer-calibration only, freeze and archive:

- fit-derived velocity caps;
- scale standardizer, winsor bounds, prediction guards, ridge coefficients;
- single-factor conformal quantiles;
- horizon-group transfer multipliers and group sample counts;
- exact code SHA.

At this checkpoint neither development-challenge seed `286286` nor protected-validation seed `297297` may have been generated.

## Independent development challenge

After candidate freeze, evaluate the unchanged P6 candidate exactly once on seed `286286`.

Seed `286286` then becomes permanently seen.

### Development gates

All must pass before protected validation may be exposed.

#### D1 — availability

Estimate availability `>=90%` of truth-visible frames.

#### D2 — overall 95% coverage

95% empirical coverage in `[0.90,0.98]` on both axes.

#### D3 — calibration curve

Mean absolute coverage error across `{50%,68%,80%,90%,95%}` over both axes `<=0.06`.

#### D4 — interval efficiency

- median 95% half-width / all-available p95 error `<=1.25` on each axis;
- p95 95% half-width / all-available p95 error `<=2.25` on each axis.

#### D5 — long-bridge calibration

There must be at least `40` available long-bridge (`3..5`) observations.

For those observations:

- 95% coverage must be in `[0.90,0.99]` on both axes;
- p95 95% half-width / long-bridge p95 absolute error must be `<=2.50` on both axes.

#### D6 — direct/short calibration

For bridge horizon `0..2`, 95% coverage must be in `[0.90,0.98]` on both axes.

#### D7 — shift discrimination

Trajectory-level mean P1-style severity AUROC between single-factor calibration and development challenge `>=0.85`.

If any D1–D7 gate fails, protected validation seed `297297` must remain ungenerated and be retired.

## Protected validation gates

Only if all development gates pass, the exact frozen candidate may be evaluated once on seed `297297`.

The protected-validation gates are identical to D1–D7 except the evidence role changes to protected validation.

No constant may change between development challenge and protected validation.

## Exposure policy

- Transfer seed `275275` becomes seen during calibration.
- Development challenge seed `286286` becomes permanently seen on first evaluation.
- Protected seed `297297` becomes permanently seen only if the development challenge passes and validation is actually run.
- Any method change after development challenge requires P7 with new evidence; P6 cannot be revised and re-tested on `286286` as unseen.

Even if P6 protected validation passes, the **final Phase 11 frozen holdout remains ungenerated and requires separate explicit user approval**.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
- negative/mixed results remain permanent evidence
