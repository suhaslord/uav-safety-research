# Phase 11 P15 preregistration — source-observation calibration for independent fallback

## Status

**PREREGISTERED BEFORE P15 DATA GENERATION**

Branch: `phase11-p15-source-observation-calibration`

P14 stopped before candidate freeze because only `66` rows in the easier base-calibration split actually invoked the auxiliary fallback, below the preregistered `300`-row auxiliary minimum. P14 fit/base/transfer-calibration seeds `638638`, `649649`, and `660660` are permanently seen. Challenge `671671` and protected validation `682682` were never exposed and are retired.

P15 preserves the P14 auxiliary observation process and runtime fallback rule exactly. The only scientific change is that auxiliary uncertainty is calibrated from **all available auxiliary observations** on calibration splits, rather than only the subset of frames where primary failure caused the observation to be used as final output.

## Research question

**Does source-observation calibration let an independent coarse fallback recover anchorless primary failures while remaining honestly calibrated and efficient under unseen compositional shift?**

## Fresh evidence boundary

- fit seed: `693693`
- base calibration seed: `704704`
- transfer-calibration seed: `715715`
- seen challenge seed: `726726`
- protected validation seed: `737737`
- frames per sequence: `60`

Disjoint families:

- fit: `650..655` (6)
- base calibration: `656..703` (48)
- transfer calibration: `704..735` (32)
- seen challenge: `736..759` (24)
- protected validation: `760..783` (24)

The complete sequence is the split unit.

Base, transfer, challenge, and protected compositions use the same structural difficulty ladder as P14, but all rows are freshly generated from the P15 seeds/families.

Protected seed `737737` must not be generated before the exact P15 candidate has passed all H1-H7 seen-challenge gates.

## Primary and auxiliary observation processes — unchanged from P14

### Primary stack

The P9/P13 soft primary continuity stack remains unchanged:

- genuine primary candidate observations only are motion-history anchors;
- bridge horizons `1..2` unchanged;
- soft bounded-influence continuity horizons `3..7`;
- fit-only q99 velocity cap;
- fit-only q95 innovation scale;
- `soft_scale_multiplier = 3.0`;
- 0.50/0.50 slope blend;
- damping `0.85`;
- no recursive continuity.

### Independent coarse auxiliary observation

Exactly the P14 synthetic observation model:

- independent availability probability `0.96`;
- lateral sigma `0.075 m`;
- altitude sigma `0.160 m`;
- independent tail probability `0.025`;
- tail scale uniform in `[2.5,4.0]`;
- independent deterministic RNG stream;
- truth used only to synthesize the simulated noisy measurement;
- auxiliary observations never become primary anchors;
- at runtime they are used only when the primary stack has no estimate.

No real-sensor performance claim is made.

## Four final-output groups — unchanged

1. `base_output`
2. `primary_continuity_h3`
3. `primary_continuity_h47`
4. `auxiliary_fallback`

## P15 source-observation calibration rule

### Primary groups

For `base_output`, `primary_continuity_h3`, and `primary_continuity_h47`, calibration uses only rows where that source is the actual final output, exactly as in P14/P13.

### Auxiliary group

For `auxiliary_fallback`, calibration uses **every truth-visible row on which the independent auxiliary observation was generated successfully**, even if the primary stack also had an estimate and therefore the auxiliary observation was not selected as the final runtime output.

The calibration target is the auxiliary observation's own absolute error:

`abs(aux_measurement - truth)`

The final runtime estimator remains fallback-only. Auxiliary calibration observations do not become primary anchors or final outputs merely because they are used for calibration.

This rule is valid because auxiliary generation is independent of primary availability by construction and is frozen before P15 data generation.

## Stage 1 — source-specific base conformal

On base calibration seed `704704`, freeze finite-sample absolute-error conformal radii for each group/axis/target `{0.50,0.68,0.80,0.90,0.95}`.

Minimum calibration evidence:

- base final-output rows `>=1500`;
- h3 final-output rows `>=150`;
- h47 final-output rows `>=100`;
- available auxiliary observations `>=5000`.

## Stage 2 — source-specific transfer calibration

On disjoint transfer-calibration seed `715715`:

- primary groups use their actual final-output rows;
- the auxiliary group again uses every available auxiliary observation.

For each group/axis/target:

`ratio = source_abs_error / max(R_base(group,axis,q),1e-9)`

Freeze finite-sample conformal multiplier `T(group,axis,q)` and final radius:

`R_final = R_base * T`

Minimum transfer evidence:

- base final-output rows `>=1200`;
- h3 final-output rows `>=120`;
- h47 final-output rows `>=80`;
- available auxiliary observations `>=3000`.

No learned uncertainty model and no post-challenge multiplier are allowed.

## Seen-challenge runtime minimums

On the actual fallback-only final estimator:

- base output `>=1000`;
- h3 `>=100`;
- h47 `>=60`;
- auxiliary fallback outputs `>=200`.

## Primary gates

### H1 useful availability
Final truth-visible output availability `>=0.95`.

### H2 overall 95% coverage
Lateral and altitude each in `[0.90,0.98]`.

### H3 calibration curve
MACE over `{50,68,80,90,95}%` and both axes `<=0.06`.

### H4 overall interval efficiency
For each axis:
- median 95% half-width / all-available p95 error `<=1.25`;
- p95 95% half-width / all-available p95 error `<=2.25`.

### H5 primary-continuity honesty
Across h3+h47 primary continuity:
- lateral and altitude 95% coverage in `[0.88,0.99]`;
- p95 half-width / continuity p95 error `<=2.75` on both axes.

### H6 base-output honesty
- lateral/altitude 95% coverage in `[0.90,0.98]`;
- p95 half-width / base p95 error `<=2.25` on both axes.

### H7 auxiliary-fallback honesty
On actual runtime auxiliary fallback outputs:
- lateral/altitude 95% coverage in `[0.90,0.98]`;
- p95 half-width / auxiliary fallback p95 error `<=2.25` on both axes.

H8 visual-shift AUROC `>=0.85` remains diagnostic only.

## Secondary diagnostics

Report without tuning:

- auxiliary observation calibration row counts versus actual fallback-use counts;
- fraction of primary-missing rows recovered by auxiliary fallback;
- remaining unavailable rows;
- zero-primary-candidate sequences recovered by auxiliary outputs;
- auxiliary tail rate and error distribution;
- primary continuity error/coverage by exact horizon;
- final source mix.

## Staging

1. Generate only fit + base calibration + transfer calibration.
2. Freeze/hash the exact P15 candidate.
3. Evaluate once on seen challenge `726726`.
4. If any minimum or H1-H7 fails, stop; do not expose `737737`.
5. If H1-H7 all pass, evaluate the exact frozen candidate once on protected `737737`.

No P15 observation-model constant, calibration rule, grouping rule, radius, multiplier, or gate may change after challenge exposure.

Even a full protected-validation pass does not authorize the final Phase 11 frozen holdout; that later holdout still requires separate explicit user approval.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
- no real auxiliary-sensor performance claim
