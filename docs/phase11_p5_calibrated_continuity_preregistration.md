# Phase 11 P5 preregistration — calibrated perception continuity

## Status

**PREREGISTERED BEFORE P5 DATA GENERATION**

Branch: `phase11-p5-calibrated-continuity`

Development result: see `docs/phase11_p5_development_stop.md` — H5 long-bridge altitude fail (85.71% vs >=88%) archived before validation.

All earlier Phase 11 challenge/validation evidence is permanently seen and excluded from P5 hidden evaluation. P2 `112112` and P3 `154154` remain ungenerated/retired. P4 protected validation seed `198198` is permanently seen.

## Research question

**Can a bounded, causally available temporal continuity layer recover multi-frame perception gaps while preserving the calibrated uncertainty behavior achieved by P4?**

P5 targets the sole failed P4 primary gate: estimator availability. It does not retune P4 on seed `198198`; it creates new evidence and refits the reliability model for longer bridge horizons.

## Motivation from read-only P4 forensics

P4 passed coverage, calibration-curve, interval-efficiency, and shift-discrimination gates but produced estimates on only `83.13%` of truth-visible protected-validation frames.

Post-exposure descriptive forensics showed that the two worst compositional domains had P4/P1 availability of approximately `36.1%` and `55.0%`. Their raw miss-run median lengths were `4` and `3` frames, while the inherited bridge was capped at `2` frames. This observation motivates P5 but is not reused as hidden evidence.

## New P5 evidence boundary

All seeds and trajectory families are new.

- fit seed: `209209`
- single-factor calibration seed: `220220`
- compositional transfer-calibration seed: `231231`
- protected validation seed: `242242`
- frames per sequence: `60`

Trajectory families:

- fit: `72..77`
- calibration: `78..80`
- transfer calibration: `81..83`
- protected validation: `84..86`

Complete sequences are the separation unit.

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

1. `edge+temporal_dropout`
2. `small_scale+blur_noise`
3. `oblique+dim`
4. `blur_noise+low_contrast`
5. `edge+small_scale+temporal_dropout`
6. `oblique+blur_noise+low_contrast`
7. `edge+dim+temporal_dropout`
8. `small_scale+oblique+blur_noise`

### Protected validation compositions

1. `edge+blur_noise`
2. `small_scale+dim+temporal_dropout`
3. `oblique+low_contrast`
4. `edge+small_scale+dim`
5. `blur_noise+low_contrast+temporal_dropout`
6. `edge+oblique+temporal_dropout`
7. `small_scale+oblique+dim+low_contrast`
8. `edge+small_scale+oblique+blur_noise+temporal_dropout`

Protected validation seed `242242` must not be generated before candidate freeze.

## Frozen raw perception generator

P5 inherits the same simulation-only raw observation generator and factor-identifiable features used by P1–P4. No raw detector availability probability or point-error generator parameter is changed.

## P5 bounded continuity layer

### Maximum horizon

Maximum bridge horizon is fixed at `5` consecutive missing frames.

### History requirement

- With at least two prior **direct** observations in the same sequence, estimate per-frame velocity from the two most recent direct observations.
- With exactly one prior direct observation, a hold-last bridge is permitted only for horizon `1`.
- A bridged estimate is never inserted into the direct-observation history used to estimate future velocity.

### Fit-frozen velocity caps

Using only consecutive pairs of direct, candidate-available observations on the P5 fit split, compute absolute per-frame direct-state changes for lateral and altitude independently.

Freeze velocity caps as the empirical `99th` percentile absolute per-frame change on each axis.

For bridging, clip estimated velocity independently to `[-cap,+cap]` on each axis before extrapolation.

### Bridge prediction

For horizon `h` after the most recent direct observation:

`predicted_state = last_direct_state + clipped_velocity * h`

for `h <= 5`.

No truth value, future frame, domain identity, or reliability label enters the bridge.

### Bridge source metadata

Every recovered frame records:

- `continuity_source = temporal_bridge`;
- `bridge_horizon in {1,2,3,4,5}`;
- the same inference-visible risk features as the missing frame.

## P5 uncertainty model

P5 uses the P4 robust all-available uncertainty architecture, refit entirely on new P5 evidence so horizons `3..5` can be calibrated.

### Scale model

Separate lateral/altitude ridge log-error models use:

- eight risk components;
- risk score;
- normalized coactivation count;
- largest and second-largest primary risk components;
- bridge horizon normalized by `5`;
- source one-hots.

Continuous features are fit-standardized.

Target log absolute error is winsorized at fit q02/q98.

Ridge lambda is fixed at `4.0`.

Predicted log scale is clipped to fit predicted q01/q99 expanded by `0.35` log units.

No hand-written multiplicative risk inflation is used.

### Two-stage conformal calibration

As in P4:

1. single-factor calibration produces finite-sample conformal normalized-residual quantiles for targets `{0.50,0.68,0.80,0.90,0.95}`;
2. seen compositional transfer calibration produces a second finite-sample conformal transfer multiplier;
3. final target radii are monotonized by cumulative maximum to guarantee nesting.

No hard severity or interval-width gate removes observations from the primary P5 result.

## Primary gates

### H1 — estimator availability

On protected validation, P5 must produce an estimate on `>=90%` of truth-visible frames.

### H2 — 95% coverage transfer

Across every available protected-validation estimate, 95% coverage must be in `[0.90,0.98]` on both axes.

### H3 — calibration curve quality

Mean absolute coverage error across `{50%,68%,80%,90%,95%}` over both axes must be `<=0.06`.

### H4 — interval efficiency

Across every available protected-validation estimate:

- median 95% half-width / all-available p95 absolute error `<=1.25` on each axis;
- p95 95% half-width / all-available p95 absolute error `<=2.25` on each axis.

### H5 — long-bridge honesty

For the subset of available observations with bridge horizon `3..5`:

- if at least `40` such observations exist, 95% empirical coverage must be `>=0.88` on both axes;
- median 95% half-width must be at least the median absolute error on the corresponding axis (intervals may not be systematically narrower than typical long-bridge error).

If fewer than `40` long-bridge observations exist, H5 is reported as insufficient evidence and P5 cannot be described as a complete pass.

### H6 — shift discrimination remains informative

Trajectory-level mean P1-style severity must distinguish single-factor calibration from protected compositional validation with AUROC `>=0.85`.

## Development/candidate-freeze rule

Fit, single-factor calibration, and seen transfer-calibration may be generated after this preregistration. Before protected validation, freeze:

- velocity caps;
- bridge horizon rule;
- standardization values;
- winsorization bounds;
- prediction guards;
- ridge coefficients;
- conformal quantiles;
- transfer multipliers;
- exact code SHA;
- all seen transfer gate metrics.

If H1–H5 already fail on the seen transfer split, protected validation should not be exposed.

## Validation exposure policy

Once protected seed `242242` is generated/evaluated it is permanently seen. No bridge horizon, velocity-cap rule, model basis, ridge lambda, prediction guard, conformal rule, transfer rule, or gate may change and then be re-evaluated on `242242` as unseen evidence.

Passing P5 protected validation still does **not** authorize the final Phase 11 frozen holdout. A separate explicit user approval is required for that final exposure.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
- negative and mixed results remain permanent evidence
