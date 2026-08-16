# Phase 11 P6 preregistration — source-conditional continuity calibration

## Status

**PREREGISTERED BEFORE P6 DATA GENERATION**

Branch: `phase11-p6-source-conditional-calibration`

P5 is preserved as a development stop. Its seen transfer seed `231231` is permanently seen and its protected validation seed `242242` was not generated and is retired rather than recycled.

All earlier Phase 11 exposed evidence remains permanently seen, including P0 `33033`, duplicate `63333`, P1 `77077`, P2 transfer `101101`, P3 transfer `143143`, P4 transfer `187187`, and P4 validation `198198`.

## Research question

**Can the P5 perception-continuity estimator retain its availability gain while source-conditional conformal transfer calibration makes uncertainty honest for both continuity-extension and ordinary outputs under unseen compositional shift?**

P6 makes one scientific change only: the compositional transfer-calibration stage is conditioned on whether an estimate came from `continuity_extension` or from the base estimator/short bridge.

## Frozen P5 continuity method

The P5 continuity estimator is inherited unchanged:

- genuine perception outputs are the only motion-history anchors;
- inherited bridge outputs are never anchors;
- continuity-extension outputs are never anchors;
- fit-derived q99 absolute genuine-anchor slope caps are used independently by axis;
- at most the three most recent genuine anchors are considered;
- component-wise median of the two most recent anchor-to-anchor slopes is used when three anchors exist;
- extension occurs only beyond the inherited two-frame bridge and through total gap horizon `5`;
- damping factor remains exactly `0.85`;
- no future frames, truth state, domain labels, or future reacquisition information may be used.

No motion/continuity constant may be tuned in P6.

## New P6 evidence boundary

All seeds and trajectory families are new.

- fit seed: `253253`
- single-factor calibration seed: `264264`
- compositional transfer-calibration seed: `275275`
- protected validation seed: `286286`
- frames per sequence: `60`

Families are disjoint:

- fit: `87..92`
- calibration: `93..95`
- transfer calibration: `96..98`
- protected validation: `99..101`

The full sequence is the split unit.

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
2. `oblique+temporal_dropout`
3. `dim+blur_noise`
4. `small_scale+low_contrast`
5. `edge+dim+temporal_dropout`
6. `small_scale+oblique+blur_noise`
7. `edge+blur_noise+low_contrast`
8. `oblique+dim+low_contrast+temporal_dropout`

### Protected validation compositions

1. `edge+oblique`
2. `small_scale+blur_noise`
3. `dim+temporal_dropout`
4. `edge+low_contrast+temporal_dropout`
5. `small_scale+oblique+dim`
6. `edge+small_scale+blur_noise+low_contrast`
7. `oblique+dim+blur_noise+temporal_dropout`
8. `edge+small_scale+oblique+dim+temporal_dropout`

Protected validation seed `286286` must not be generated before the P6 candidate-freeze checkpoint.

## P6 uncertainty model

P6 preserves the P5 scale-model architecture and single-factor conformal stage unchanged:

- separate lateral and altitude log-error scale models;
- P5 standardized low-capacity causal basis;
- fit-target winsorization at empirical `2nd` / `98th` percentiles;
- ridge lambda `4.0`;
- fit-prediction guard based on fitted q01/q99 expanded by `0.35`;
- finite-sample single-factor conformal calibration for targets `{0.50,0.68,0.80,0.90,0.95}`;
- no hard reliability accept/reject threshold.

### Exactly two transfer-calibration groups

Each available estimate receives one calibration group:

- `continuity_extension`: `p5_source == "continuity_extension"`
- `base_output`: every other available P5 source, including genuine detections and inherited short-horizon bridge outputs

No other grouping or subgroup search is allowed.

### Minimum group size

The seen transfer split must contain at least `40` available truth-visible `continuity_extension` rows and at least `200` `base_output` rows.

If either minimum is not met, P6 development fails and protected validation is not exposed. There is no fallback to a pooled transfer multiplier for a missing group.

### Source-conditional transfer calibration

First compute the unchanged P5 single-factor provisional radius:

`R_single(axis,q) = predicted_scale * Q_single(axis,q)`

Within each predeclared group independently:

`transfer_ratio = abs_error / max(R_single, 1e-9)`

Freeze finite-sample conformal multiplier:

`T(group,axis,q)`

using order statistic `ceil((n+1)*q)`.

Final radius for an observation is:

`R_P6(axis,q) = predicted_scale * Q_single(axis,q) * T(group,axis,q)`

Radii are monotonized by cumulative maximum across increasing q for each observation.

## Primary gates

### H1 — useful availability

Truth-visible P6 output availability must be `>=0.92`.

### H2 — overall 95% coverage transfer

Across all available outputs, 95% empirical coverage must be in `[0.90,0.98]` on both lateral and altitude axes.

### H3 — overall calibration curve quality

Mean absolute coverage error across `{50%,68%,80%,90%,95%}` over both axes must be `<=0.06`.

### H4 — overall interval efficiency

Across all available outputs:

- median 95% half-width / all-available p95 absolute error `<=1.25` on each axis;
- p95 95% half-width / all-available p95 absolute error `<=2.25` on each axis.

All four conditions must pass.

### H5 — continuity-specific honesty

On `continuity_extension` rows only:

- 95% coverage must be in `[0.88,0.99]` on both axes;
- p95 95% half-width / continuity-only p95 absolute error must be `<=2.75` on both axes.

### H6 — base-output honesty

On `base_output` rows only:

- 95% coverage must be in `[0.90,0.98]` on both axes;
- p95 95% half-width / base-output p95 absolute error must be `<=2.25` on both axes.

### H7 — shift discrimination

Trajectory-level mean inherited severity must distinguish single-factor calibration from compositional evaluation with AUROC `>=0.85`.

H7 is diagnostic and does not establish safety.

## Candidate-freeze checkpoint

After this preregistration, P6 may generate only fit, calibration, and seen transfer data.

Freeze and archive:

- P5 continuity constants and new fit-derived velocity caps;
- P5 scale-model standardizer, winsor bounds, prediction guards, and ridge coefficients;
- single-factor conformal quantiles;
- source-conditional transfer multipliers;
- group row counts;
- seen transfer gate metrics;
- exact code commit and artifact hashes.

If group-size requirements or H1-H6 fail on seen transfer data, protected validation seed `286286` must not be exposed.

If all H1-H6 pass, the candidate may proceed exactly once to the protected validation split without changing any method constant.

## Validation exposure policy

Once seed `286286` is generated/evaluated it becomes permanently seen. No P6 continuity rule, source grouping, group-size rule, scale model, conformal rule, target, multiplier, or gate may change and then be re-evaluated on `286286` as unseen evidence.

Passing P6 protected validation still does **not** authorize the final Phase 11 frozen holdout. A final holdout requires a separate explicit user approval at an exact candidate-freeze checkpoint.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
- negative and mixed outcomes remain permanent evidence
