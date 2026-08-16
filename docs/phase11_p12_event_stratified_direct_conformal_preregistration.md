# Phase 11 P12 preregistration — event-stratified rare-gap direct conformal

## Status

**PREREGISTERED BEFORE P12 DATA GENERATION**

Branch: `phase11-p12-event-stratified-direct-conformal`

P9, P10, and P11 all stopped before transfer exposure because random grouped-calibration cohorts failed to produce enough rows in at least one preregistered continuity-horizon group. P11 used 30 fresh calibration families and still produced only 8 `continuity_h67` rows versus the required 30.

P12 treats this as a **study-design problem**, not a reason to lower thresholds or pool away the rare long-gap regime.

## Research question

**If rare observation gaps are introduced by a preregistered truth-independent intervention rather than left to random incidence, does the unchanged P9 soft bounded-influence continuity estimator plus unchanged four-group direct conformal uncertainty achieve honest, efficient transfer across unseen compositional visual shift?**

P12 remains simulation-only perception/reliability research. It does not tune, command, or validate a physical aircraft controller.

## Scientific significance

P12 changes the experimental design, not the estimator:

- rare gaps become controlled interventions;
- gap duration is an independent experimental factor;
- long-gap reliability remains separately measurable instead of being pooled away;
- calibration power is guaranteed by design rather than post-hoc top-up;
- natural-frequency behavior is still reported separately as a diagnostic so the balanced intervention cohort is not misrepresented as an operational frequency distribution.

## Fresh evidence boundary

All P12 seeds and families are fresh.

- fit seed: `583583`
- event-stratified grouped-calibration seed: `594594`
- seen-transfer seed: `605605`
- protected-validation seed: `616616`
- frames per sequence: `60`

Families are disjoint:

- fit: `500..505` (6 families)
- grouped calibration: `506..529` (24 families)
- seen transfer: `530..541` (12 families)
- protected validation: `542..553` (12 families)

### Gap-length strata

Grouped calibration:

- gap-3 families: `506..513`
- gap-5 families: `514..521`
- gap-7 families: `522..529`

Seen transfer:

- gap-3 families: `530..533`
- gap-5 families: `534..537`
- gap-7 families: `538..541`

Protected validation:

- gap-3 families: `542..545`
- gap-5 families: `546..549`
- gap-7 families: `550..553`

The complete trajectory remains the split unit.

## Domains

Fit uses the unchanged P9 single-factor domains:

`nominal`, `edge`, `small_scale`, `oblique`, `dim`, `blur_noise`, `temporal_dropout`, `low_contrast`.

Grouped calibration uses the unchanged P9 calibration composition structure:

1. `edge+temporal_dropout`
2. `small_scale+temporal_dropout`
3. `oblique+temporal_dropout`
4. `dim+temporal_dropout`
5. `blur_noise+temporal_dropout`
6. `low_contrast+temporal_dropout`
7. `edge+small_scale+temporal_dropout`
8. `oblique+dim+temporal_dropout`

Seen transfer and protected validation use the same previously preregistered composition structures as P9/P10/P11 but with entirely fresh seeds and families.

## Truth-independent observation-gap intervention

The underlying procedural scene, truth trajectory, latent visual context, observed features, and stochastic candidate generation are created exactly as before.

P12 then applies a **predeclared observation-outage mask** to the candidate stream.

For a forced-outage frame only:

- `candidate_available = false`;
- candidate source is cleared;
- candidate metric estimates/errors are set to missing;
- truth state and observed scene/context features remain unchanged;
- a diagnostic `forced_dropout=true` flag is recorded.

The intervention never reads or conditions on truth state, candidate error, residual, uncertainty, future observations, future reacquisition, or domain outcome.

### Fixed outage windows

Each event-stratified sequence receives exactly two forced gaps of its assigned stratum length.

Grouped calibration starts:

- frame `12`;
- frame `42`.

Seen transfer starts:

- frame `13`;
- frame `43`.

Protected validation starts:

- frame `14`;
- frame `44`.

For a gap length `g`, forced frames are `start ... start+g-1` inclusive.

Different stage start frames prevent exact replay of the same outage timing across evidence roles.

No post-hoc top-up, row selection, or event relocation is allowed.

## Frozen estimator — identical to P9/P10/P11

P12 uses `run_phase11_p9_soft_update_direct_conformal` unchanged for the scientific estimator.

- genuine candidate outputs only are motion-history anchors;
- bridge and continuity outputs are never anchors;
- fit-only q99 absolute genuine-anchor velocity cap per axis;
- fit-only q95 genuine-anchor innovation scale per axis;
- `soft_scale_multiplier = 3.0`;
- `e_soft = e / sqrt(1 + (e/(3*s))^2)`;
- previous-slope / soft-updated-slope blend = `0.50 / 0.50`;
- final slope clipped to fit q99 velocity cap;
- inherited bridge horizons 1-2;
- P12/P9 continuity horizons 3-7;
- damping `0.85`;
- non-recursive continuation.

No estimator constant may change after P12 generation starts.

## Direct grouped conformal uncertainty — unchanged four-group partition

No learned uncertainty scale, adaptation correction, transfer multiplier, pooled fallback, or data-dependent regrouping is allowed.

Exactly four groups remain:

1. `base_output`;
2. `continuity_h3`;
3. `continuity_h45`;
4. `continuity_h67`.

For each group, axis, and target `{0.50,0.68,0.80,0.90,0.95}`, freeze the finite-sample absolute-error conformal order statistic `ceil((n+1)*q)` using only event-stratified calibration seed `594594`.

## Sample-size requirements

The original P9 calibration minimums remain necessary:

- `base_output >= 1000`;
- `continuity_h3 >= 120`;
- `continuity_h45 >= 60`;
- `continuity_h67 >= 30`.

P12 additionally preregisters a **2x calibration power margin** before candidate freeze:

- `base_output >= 2000`;
- `continuity_h3 >= 240`;
- `continuity_h45 >= 120`;
- `continuity_h67 >= 60`.

If any P12 power-margin count fails, candidate freeze stops and transfer is not exposed.

Seen-transfer must satisfy the original P9 transfer minimums plus a preregistered event-study margin:

- `base_output >= 1200`;
- `continuity_h3 >= 150`;
- `continuity_h45 >= 75`;
- `continuity_h67 >= 30`.

Protected validation reports the same counts but does not permit any method change after exposure.

## Primary reliability gates — unchanged H1-H6

### H1 useful availability

Event-stratified truth-visible output availability `>=0.92`.

### H2 overall 95% coverage

Both axes in `[0.90,0.98]`.

### H3 calibration curve

Mean absolute coverage error over `{50%,68%,80%,90%,95%}` and both axes `<=0.06`.

### H4 overall interval efficiency

Each axis:

- median 95% half-width / all-available p95 absolute error `<=1.25`;
- p95 95% half-width / all-available p95 absolute error `<=2.25`.

### H5 continuity-specific honesty

Across all continuity rows:

- lateral and altitude 95% coverage each in `[0.88,0.99]`;
- p95 95% half-width / continuity p95 error `<=2.75` on both axes.

### H6 base-output honesty

- lateral and altitude 95% coverage each in `[0.90,0.98]`;
- p95 95% half-width / base-output p95 error `<=2.25` on both axes.

H7 trajectory shift AUROC `>=0.85` remains diagnostic only.

## Horizon-specific secondary diagnostics

For each of h3, h4-5, and h6-7 report independently:

- row count;
- lateral/altitude 95% coverage;
- p95 absolute error;
- p95 interval half-width;
- p95 half-width / p95 error;
- point MAE and p95 by exact horizon 3..7.

Also report gain and slope-cap-utilization diagnostics already provided by P9.

## Natural-stream diagnostic

At transfer and protected-validation stages, P12 also evaluates the same fresh raw trajectories **without** the forced-outage intervention.

This natural-stream result is descriptive only:

- it is not used to tune radii;
- it is not used to decide whether the protected validation may be exposed;
- sparse natural horizon groups do not trigger regrouping;
- it prevents the balanced event-stratified cohort from being misrepresented as a natural-frequency availability estimate.

## Staging

1. Generate natural fit plus event-stratified calibration only.
2. Verify the P12 2x calibration power margin.
3. Freeze exact candidate and SHA-256 artifact before transfer exposure.
4. Evaluate the exact candidate once on event-stratified seen transfer seed `605605`; also report its natural-stream counterpart descriptively.
5. Protected validation seed `616616` may be exposed only if:
   - P12 seen-transfer power margins pass; and
   - every unchanged H1-H6 gate passes.
6. Evaluate the exact frozen candidate once on protected seed `616616`; also report natural-stream diagnostics.
7. Stop. Even a full protected-validation pass does **not** authorize the final Phase 11 frozen holdout. Final holdout exposure requires a separate explicit user approval at an exact future freeze checkpoint.

## Exposure policy

Once generated, every P12 seed is permanently seen in its role.

No P12 intervention schedule, family stratum, estimator constant, conformal group, threshold, or gate may change after seeing that role and then be re-evaluated on the same seed as unseen.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
- natural-stream and event-stratified results must be clearly distinguished
- negative/mixed/failed outcomes remain permanent evidence
