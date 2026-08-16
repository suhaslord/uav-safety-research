# Phase 11 P12 preregistration — three-group direct conformal continuity

## Status

**PREREGISTERED BEFORE P12 DATA GENERATION**

Branch: `phase11-p12-three-group-direct-conformal`

P11 stopped before candidate freeze because the preregistered standalone horizon-6/7 calibration bucket contained only `8` rows despite a 30-family calibration cohort. P11 fit seed `495495` and calibration seed `506506` are permanently seen. P11 transfer `517517` and protected validation `528528` were never exposed and are retired.

P12 preserves the P9/P10/P11 **soft bounded-influence point estimator exactly**. The only scientific change is a preregistered simplification of direct-conformal grouping from four buckets to three:

1. `base_output`;
2. `continuity_h3`;
3. `continuity_h47` for horizons 4, 5, 6, or 7.

This is motivated by the frozen P9-P11 evidence that h6-7 continuity is too rare to support a standalone conformal bucket efficiently. No prior threshold is lowered and no P11 row is reused for P12 calibration.

## Research question

**Can a simpler, adequately powered three-group direct conformal design preserve honest/efficient uncertainty for the unchanged soft continuity estimator under unseen compositional shift?**

## Fresh P12 evidence boundary

- fit seed: `539539`
- grouped-calibration seed: `550550`
- seen-transfer seed: `561561`
- protected-validation seed: `572572`
- frames per sequence: `60`

Disjoint trajectory families:

- fit: `304..309` (`6` families)
- grouped calibration: `310..357` (`48` families)
- seen transfer: `358..377` (`20` families)
- protected validation: `378..397` (`20` families)

All are fresh and disjoint from every earlier Phase 11 family.

The complete sequence is the split unit. No adjacent-frame random split is allowed.

### Fit domains

`nominal`, `edge`, `small_scale`, `oblique`, `dim`, `blur_noise`, `temporal_dropout`, `low_contrast`.

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

Protected seed `572572` must not be generated before candidate freeze and successful seen-transfer gating.

## Point estimator — unchanged from P9/P10/P11

Only genuine candidate perception outputs may become anchors. Inherited bridge outputs and P12 continuity outputs are never anchors.

Fit-only constants/rules:

- q99 absolute genuine-anchor slope cap per axis;
- q95 absolute genuine-anchor innovation scale per axis;
- `soft_scale_multiplier = 3.0`;
- `e_soft = e / sqrt(1 + (e/(3*s))^2)`;
- previous-slope weight `0.50`;
- soft-updated-slope weight `0.50`;
- final slope clipped to q99 velocity cap;
- inherited bridge horizons 1-2 unchanged;
- P12 continuity horizons 3-7 only;
- damping `0.85`;
- no recursive continuity.

No P12 point-estimator constant may change after generation begins.

## Three-group direct conformal uncertainty

P12 uses **no learned error-scale model, no adaptation correction, and no transfer multiplier**.

Fixed groups:

- `base_output`: every available non-P12-continuity estimate;
- `continuity_h3`: P12 continuity at horizon exactly 3;
- `continuity_h47`: P12 continuity at horizons 4-7 inclusive.

On grouped-calibration seed `550550`, independently for each group, axis, and target `q` in `{0.50,0.68,0.80,0.90,0.95}`:

1. collect finite absolute point errors from truth-visible available rows in the exact group;
2. sort them;
3. select finite-sample conformal order statistic `ceil((n+1)*q)`;
4. monotonize radii by cumulative maximum over increasing q.

No transfer row may alter the candidate radii.

## Sample-size requirements

These are fixed before P12 generation.

### Candidate-freeze grouped-calibration minimums

- `base_output >= 1500`;
- `continuity_h3 >= 150`;
- `continuity_h47 >= 100`.

### Seen-transfer minimums

- `base_output >= 1000`;
- `continuity_h3 >= 100`;
- `continuity_h47 >= 60`.

No threshold may be lowered after exposure. If any minimum fails, the phase stops before the next evidence stage.

## Primary gates

### H1 — useful availability

Truth-visible output availability `>=0.92`.

### H2 — overall 95% coverage

Lateral and altitude empirical 95% coverage each in `[0.90,0.98]`.

### H3 — overall calibration curve

Mean absolute coverage error across `{50%,68%,80%,90%,95%}` and both axes `<=0.06`.

### H4 — overall interval efficiency

For each axis:

- median 95% half-width / all-available p95 absolute error `<=1.25`;
- p95 95% half-width / all-available p95 absolute error `<=2.25`.

### H5 — continuity-specific honesty

Across all P12 continuity rows (h3 plus h4-7):

- lateral and altitude 95% coverage each in `[0.88,0.99]`;
- p95 95% half-width / continuity p95 absolute error `<=2.75` on both axes.

### H6 — base-output honesty

On `base_output` rows only:

- lateral and altitude 95% coverage each in `[0.90,0.98]`;
- p95 95% half-width / base-output p95 absolute error `<=2.25` on both axes.

### H7 — shift discrimination

Trajectory-level inherited-severity AUROC `>=0.85` is reported as a diagnostic only.

## Secondary diagnostics

Report without candidate tuning:

- row counts and 95% coverage for each of the three groups;
- group-specific p95 point error and p95 half-width/error ratio;
- continuity MAE/p95 by exact horizon 3-7;
- soft measurement-gain distributions;
- unavailable reasons;
- descriptive comparison against prior P8 hard-clipped continuity on the same fresh P12 rows where both produce estimates.

## Staging

1. Generate only fit seed `539539` and grouped calibration seed `550550`.
2. If sample minimums pass, freeze candidate and hash it.
3. Evaluate that exact candidate once on seen transfer seed `561561`.
4. If any transfer minimum or H1-H6 fails, stop; do not expose `572572`.
5. Only if all H1-H6 pass may the exact candidate be evaluated once on protected seed `572572`.

Any exposed P12 seed becomes permanently seen. Any unexposed protected seed is retired if P12 stops.

Even a complete P12 protected-validation pass does **not** authorize the final Phase 11 frozen holdout. Final holdout exposure remains behind a separate explicit user approval at an exact later freeze checkpoint.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
