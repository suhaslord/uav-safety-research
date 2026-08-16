# Phase 11 P13 preregistration — severity-conditioned Mondrian direct conformal

## Status

**PREREGISTERED BEFORE P13 DATA GENERATION**

Branch: `phase11-p13-severity-mondrian-conformal`

P12 is frozen as a powered seen-transfer failure. P12 fit `583583`, calibration `594594`, and transfer `605605` are permanently seen. P12 protected seed `616616` was not exposed and is retired.

P12 read-only forensics found that inherited inference-visible severity shifted upward inside every source/horizon group while p95 residuals also increased. P13 tests that hypothesis on completely fresh evidence; no P12 row, severity cutpoint, error, residual, radius, or threshold is reused.

## Research question

**Can direct conformal uncertainty conditioned jointly on continuity regime and a separately frozen inference-visible severity regime restore calibration under unseen compositional shift while retaining the interval efficiency of P12?**

P13 remains simulation-only perception/reliability research and does not modify or validate a physical aircraft controller.

## Scientific changes relative to P12

Exactly one uncertainty-design change is allowed:

- P12 direct conformal group = `source/horizon` only;
- P13 direct conformal group = `source/horizon x severity regime`.

The P9 soft bounded-influence continuity estimator and P12 event-stratified rare-gap study design remain unchanged.

No learned error-scale model, learned correction model, transfer multiplier, or post-challenge inflation factor is allowed.

## Fresh evidence boundary

- natural fit seed: `638638`
- severity-partition seed: `649649`
- event-stratified conformal-calibration seed: `660660`
- seen-transfer seed: `671671`
- protected-validation seed: `682682`
- frames per sequence: `60`

Disjoint families:

- fit: `600..605` (6)
- severity partition: `606..623` (18)
- conformal calibration: `624..659` (36)
- seen transfer: `660..677` (18)
- protected validation: `678..695` (18)

The full sequence is the split unit.

## Gap strata

Partition families:
- gap 3: `606..611`
- gap 5: `612..617`
- gap 7: `618..623`

Calibration families:
- gap 3: `624..635`
- gap 5: `636..647`
- gap 7: `648..659`

Transfer families:
- gap 3: `660..665`
- gap 5: `666..671`
- gap 7: `672..677`

Validation families:
- gap 3: `678..683`
- gap 5: `684..689`
- gap 7: `690..695`

## Fresh severity-spectrum partition/calibration compositions

The partition and calibration roles use the same predeclared composition *set* but disjoint seeds/families:

1. `edge+temporal_dropout`
2. `small_scale+dim+temporal_dropout`
3. `oblique+low_contrast+temporal_dropout`
4. `dim+blur_noise+temporal_dropout`
5. `edge+oblique+blur_noise+temporal_dropout`
6. `small_scale+dim+low_contrast+temporal_dropout`
7. `edge+small_scale+oblique+dim+temporal_dropout`
8. `edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout`

This spectrum is fixed before generation and intentionally spans lower to higher compositional coactivation without using any truth/error outcome.

## Seen-transfer compositions

1. `edge+low_contrast+temporal_dropout`
2. `small_scale+oblique+temporal_dropout`
3. `dim+low_contrast+temporal_dropout`
4. `blur_noise+low_contrast+temporal_dropout`
5. `edge+small_scale+blur_noise+temporal_dropout`
6. `oblique+dim+blur_noise+temporal_dropout`
7. `edge+oblique+dim+low_contrast+temporal_dropout`
8. `small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout`

## Protected-validation compositions

1. `edge+dim+temporal_dropout`
2. `small_scale+blur_noise+temporal_dropout`
3. `oblique+dim+temporal_dropout`
4. `edge+small_scale+low_contrast+temporal_dropout`
5. `small_scale+oblique+blur_noise+temporal_dropout`
6. `edge+dim+blur_noise+low_contrast+temporal_dropout`
7. `edge+small_scale+oblique+low_contrast+temporal_dropout`
8. `edge+small_scale+dim+blur_noise+low_contrast+temporal_dropout`

## Truth-independent event intervention

P13 uses the same P12 intervention semantics: forced candidate unavailability is scheduled only from stage, family gap stratum, and frame index. It may not inspect truth, error, residual, severity, uncertainty, or future outcomes.

Fixed two-event starts:

- partition: frames `10` and `40`;
- calibration: frames `12` and `42`;
- transfer: frames `13` and `43`;
- validation: frames `14` and `44`.

Each family receives the fixed gap length assigned by its stratum. All trajectory rows are retained; no post-hoc event relocation/top-up is allowed.

## Point estimator — unchanged P9/P12 method

- genuine candidates only as anchors;
- fit q99 velocity cap per axis;
- fit q95 innovation scale per axis;
- soft multiplier `3.0`;
- soft update `e/sqrt(1+(e/(3s))^2)`;
- 0.50/0.50 prior/new slope blend;
- bridge horizons 1–2;
- continuity horizons 3–7;
- damping `0.85`;
- non-recursive continuation.

## Base source/horizon groups — unchanged

1. `base_output`
2. `continuity_h3`
3. `continuity_h45`
4. `continuity_h67`

## Separately frozen severity partition

Severity is the existing inference-visible inherited `severity` field. No truth/error feature is used.

On the **partition split only**, for each of the four base groups independently:

- freeze lower cutpoint = empirical `1/3` quantile of severity;
- freeze upper cutpoint = empirical `2/3` quantile of severity.

Assignment:

- `low`: severity <= lower cutpoint;
- `mid`: lower < severity <= upper;
- `high`: severity > upper.

Partition cutpoints are frozen before conformal-calibration residuals are generated/evaluated. They may not change afterward.

This yields exactly 12 predeclared Mondrian cells: 4 source/horizon groups x 3 severity regimes.

## Direct Mondrian conformal calibration

On calibration seed `660660`, compute finite-sample absolute-error radii independently for each cell, axis, and target `{0.50,0.68,0.80,0.90,0.95}` using order statistic `ceil((n+1)q)`.

Radii are monotonized over increasing q.

No pooled fallback is allowed.

### Calibration cell minimums

Every severity cell must contain at least:

- `base_output`: `500` rows per severity regime;
- `continuity_h3`: `100` rows per severity regime;
- `continuity_h45`: `75` rows per severity regime;
- `continuity_h67`: `50` rows per severity regime.

If any cell misses its minimum, P13 stops before candidate freeze and transfer remains unexposed.

## Seen-transfer cell minimums

Every severity cell must contain at least:

- `base_output`: `200` rows;
- `continuity_h3`: `40` rows;
- `continuity_h45`: `30` rows;
- `continuity_h67`: `15` rows.

If any seen-transfer cell misses its minimum, protected validation is not exposed.

## Primary gates

H1–H6 remain numerically identical to P12/P9.

### H1 useful availability
`>=0.92`.

### H2 overall 95% coverage
Both axes in `[0.90,0.98]`.

### H3 calibration curve
MACE across `{50%,68%,80%,90%,95%}` and both axes `<=0.06`.

### H4 interval efficiency
For each axis:
- median 95% half-width / all-available p95 error `<=1.25`;
- p95 95% half-width / all-available p95 error `<=2.25`.

### H5 continuity honesty
- both-axis 95% coverage in `[0.88,0.99]`;
- both-axis p95 half-width / continuity p95 error `<=2.75`.

### H6 base-output honesty
- both-axis 95% coverage in `[0.90,0.98]`;
- both-axis p95 half-width / base p95 error `<=2.25`.

### H7 shift discrimination
Inherited severity AUROC `>=0.85`, diagnostic only.

### H8 high-severity honesty — new primary gate

Across all rows assigned to a `high` severity cell:

- lateral and altitude 95% coverage each in `[0.88,0.99]`;
- p95 95% half-width / high-severity p95 error `<=2.75` on each axis.

P13 protected validation requires H1–H6 **and H8** to pass on seen transfer.

## Natural-stream diagnostic

Transfer and protected-validation roles also evaluate the same fresh raw trajectories without forced outages. This is diagnostic only and cannot authorize validation or tune the candidate.

## Staging

1. Generate natural fit + event-stratified partition only; freeze severity cutpoints.
2. Generate separate event-stratified calibration; verify all 12 cell minimums.
3. Freeze exact candidate/radius table and SHA-256 artifact.
4. Expose seen transfer `671671` exactly once; report event-stratified and natural diagnostics.
5. Protected validation `682682` may be exposed only if all cell minimums and H1–H6 + H8 pass.
6. If protected validation passes, stop. Final Phase 11 holdout remains behind separate explicit user approval.

## Exposure / claim boundaries

- every generated seed becomes permanently seen in its stated role;
- no P13 cutpoint, cell, radius, threshold, estimator constant, or gate may change after exposure and be rerun on the same seed as unseen;
- `simulation_only = true`;
- `safety_acceptance = false`;
- `controller_tuning_allowed = false`;
- no physical-flight validation claim;
- no controller-performance claim;
- no new raw-camera accuracy claim.
