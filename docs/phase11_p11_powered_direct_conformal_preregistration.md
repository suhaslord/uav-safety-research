# Phase 11 P11 preregistration — second powered replication of soft update + direct grouped conformal

## Status

**PREREGISTERED BEFORE P11 DATA GENERATION**

Branch: `phase11-p11-powered-direct-conformal`

P10 stopped before candidate freeze because its fresh grouped-calibration split produced `50` horizon-4/5 continuity rows versus the unchanged preregistered minimum `60`. P10 fit seed `451451` and grouped-calibration seed `462462` are permanently seen. P10 transfer `473473` and protected validation `484484` were never exposed and are retired.

P11 preserves the P9/P10 scientific method and every sample-size/gate threshold unchanged. The only design change is additional fresh grouped-calibration trajectories to provide adequate power for the rare continuity groups.

## Research question

**With a substantially larger fresh calibration cohort, does the unchanged soft bounded-influence continuity estimator plus direct grouped conformal uncertainty transfer honestly and efficiently under unseen compositional shift?**

## Fresh P11 evidence boundary

- fit seed: `495495`
- grouped-calibration seed: `506506`
- seen-transfer seed: `517517`
- protected-validation seed: `528528`
- frames per sequence: `60`

Disjoint trajectory families:

- fit: `236..241` (`6` families)
- grouped calibration: `242..271` (`30` families)
- seen transfer: `272..287` (`16` families)
- protected validation: `288..303` (`16` families)

All are fresh and disjoint from prior Phase 11 families.

Fit domains, grouped-calibration compositions, seen-transfer compositions, and protected-validation compositions are identical in structure to P9/P10. The complete sequence remains the split unit.

Protected validation seed `528528` must not be generated before a candidate is frozen and all seen-transfer H1-H6 gates pass.

## Scientific method — unchanged from P9/P10

### Soft bounded-influence continuity

- genuine candidate perception outputs are the only motion-history anchors;
- inherited bridge outputs and P11 continuity outputs are never anchors;
- fit-only q99 absolute genuine-anchor slope cap, per axis;
- fit-only q95 absolute genuine-anchor innovation scale, per axis;
- `soft_scale_multiplier = 3.0`;
- `e_soft = e / sqrt(1 + (e/(3*s))^2)`;
- previous-slope blend weight `0.50`;
- soft-updated-slope blend weight `0.50`;
- final slope clipped to fit q99 velocity cap;
- inherited bridge horizons 1-2 unchanged;
- P11 continuity horizons 3-7 only;
- damping `0.85`;
- continuity is non-recursive.

### Direct grouped conformal uncertainty

No learned uncertainty model, adaptation correction, or transfer multiplier is allowed.

Exactly four fixed groups:

1. `base_output`;
2. `continuity_h3`;
3. `continuity_h45`;
4. `continuity_h67`.

For every group, axis, and target `{0.50,0.68,0.80,0.90,0.95}`, freeze the finite-sample conformal absolute-error radius from grouped-calibration seed `506506` using order statistic `ceil((n+1)*q)`.

No pooled fallback or data-dependent regrouping is allowed.

## Sample-size requirements — unchanged

Candidate-freeze calibration minimums:

- `base_output >= 1000`;
- `continuity_h3 >= 120`;
- `continuity_h45 >= 60`;
- `continuity_h67 >= 30`.

Seen-transfer minimums:

- `base_output >= 800`;
- `continuity_h3 >= 100`;
- `continuity_h45 >= 50`;
- `continuity_h67 >= 20`.

No threshold may be lowered after exposure.

## Primary gates — unchanged

### H1 useful availability

Truth-visible output availability `>=0.92`.

### H2 overall 95% coverage

Both axes must be in `[0.90,0.98]`.

### H3 calibration curve

Mean absolute coverage error over targets `{50%,68%,80%,90%,95%}` and both axes `<=0.06`.

### H4 overall interval efficiency

For each axis:

- median 95% half-width / all-available p95 absolute error `<=1.25`;
- p95 95% half-width / all-available p95 absolute error `<=2.25`.

### H5 continuity-specific honesty

Across all P11 continuity rows:

- lateral and altitude 95% coverage each in `[0.88,0.99]`;
- p95 95% half-width / continuity p95 error `<=2.75` on both axes.

### H6 base-output honesty

- lateral and altitude 95% coverage each in `[0.90,0.98]`;
- p95 95% half-width / base-output p95 error `<=2.25` on both axes.

H7 trajectory-level inherited-severity AUROC `>=0.85` remains diagnostic only.

## Staging and exposure policy

1. Generate only P11 fit + grouped-calibration evidence.
2. Freeze candidate and record its SHA-256 before transfer exposure.
3. Evaluate the exact candidate once on transfer seed `517517`.
4. If any group minimum or H1-H6 transfer gate fails, stop and do not expose `528528`.
5. If every H1-H6 gate passes, evaluate the exact frozen candidate once on protected seed `528528`.

Once any P11 seed is generated, it is permanently seen in its role. Unexposed protected seeds are retired if P11 stops.

Even a full P11 protected-validation pass does **not** authorize the final Phase 11 frozen holdout. Final-holdout exposure requires a separate explicit user approval at a later exact freeze checkpoint.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
