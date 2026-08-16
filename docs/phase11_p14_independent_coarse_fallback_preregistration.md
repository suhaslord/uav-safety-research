# Phase 11 P14 preregistration — independent coarse fallback + two-stage grouped conformal

## Status

**PREREGISTERED BEFORE P14 DATA GENERATION**

Branch: `phase11-p14-independent-coarse-fallback`

P13 passed every seen-challenge gate but failed protected validation because useful availability fell to `80.02%` and continuity altitude coverage fell to `85.28%`. Validation seed `627627` is permanently seen. Read-only forensics found `1,515` unavailable rows with insufficient genuine primary anchors, including `1,103` rows before any genuine primary candidate had been observed and `11` complete validation sequences with zero primary candidate detections.

P14 does not retune P13 on those rows. It tests a new simulation-only redundancy hypothesis on entirely fresh evidence.

## Research question

**Can an independent, low-fidelity auxiliary observation channel recover anchorless perception failures under severe visual shift while the primary soft-continuity path and two-stage conformal uncertainty remain honest and efficient?**

P14 does **not** claim that any specific real sensor has the modeled performance. Truth is used only inside the simulator to synthesize the auxiliary observation; truth is never exposed to the estimator or calibration logic as an inference feature.

## Scientific changes relative to P13

Exactly two changes are allowed:

1. add a preregistered independent coarse auxiliary observation channel used only when the inherited P13/P9 primary stack has no estimate;
2. add `auxiliary_fallback` as a fourth fixed conformal group while retaining the P13 two-stage base + compositional-transfer calibration architecture.

The P9/P13 primary candidate, bridge, soft bounded-influence continuity equation, horizons, damping, and anchor rules remain unchanged.

## Fresh P14 evidence boundary

- fit seed: `638638`
- base grouped-calibration seed: `649649`
- transfer-calibration seed: `660660`
- seen challenge seed: `671671`
- protected validation seed: `682682`
- frames per sequence: `60`

Disjoint families:

- fit: `516..521` (6)
- base calibration: `522..569` (48)
- transfer calibration: `570..601` (32)
- seen challenge: `602..625` (24)
- protected validation: `626..649` (24)

The complete sequence is the split unit.

### Base calibration compositions

1. `edge+temporal_dropout`
2. `small_scale+temporal_dropout`
3. `oblique+temporal_dropout`
4. `dim+temporal_dropout`
5. `blur_noise+temporal_dropout`
6. `low_contrast+temporal_dropout`
7. `edge+small_scale+temporal_dropout`
8. `oblique+dim+temporal_dropout`

### Transfer-calibration compositions

1. `edge+blur_noise+temporal_dropout`
2. `small_scale+dim+temporal_dropout`
3. `oblique+low_contrast+temporal_dropout`
4. `edge+small_scale+oblique+temporal_dropout`
5. `edge+dim+blur_noise+low_contrast+temporal_dropout`
6. `small_scale+oblique+blur_noise+temporal_dropout`
7. `edge+oblique+dim+blur_noise+temporal_dropout`
8. `small_scale+dim+blur_noise+low_contrast+temporal_dropout`

### Seen challenge compositions

1. `edge+low_contrast+temporal_dropout`
2. `small_scale+oblique+temporal_dropout`
3. `dim+low_contrast+temporal_dropout`
4. `blur_noise+low_contrast+temporal_dropout`
5. `edge+small_scale+oblique+dim+temporal_dropout`
6. `edge+oblique+blur_noise+low_contrast+temporal_dropout`
7. `small_scale+dim+blur_noise+low_contrast+temporal_dropout`
8. `edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout`

### Protected validation compositions

1. `edge+small_scale+low_contrast+temporal_dropout`
2. `oblique+dim+blur_noise+temporal_dropout`
3. `edge+dim+low_contrast+temporal_dropout`
4. `small_scale+oblique+blur_noise+low_contrast+temporal_dropout`
5. `edge+small_scale+dim+blur_noise+temporal_dropout`
6. `edge+oblique+dim+low_contrast+temporal_dropout`
7. `small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout`
8. `edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout`

Protected seed `682682` must not be generated before the exact candidate has passed all H1-H7 seen-challenge gates.

## Primary stack — unchanged

P14 first runs the unchanged P9/P13 primary stack:

- genuine primary candidate observations only are motion-history anchors;
- inherited temporal bridge horizons `1..2` unchanged;
- soft bounded-influence continuity horizons `3..7` unchanged;
- fit-only q99 velocity caps;
- fit-only q95 innovation scales;
- `e_soft = e / sqrt(1 + (e/(3*s))^2)`;
- `soft_scale_multiplier = 3.0`;
- previous/updated slope blend `0.50 / 0.50`;
- damping `0.85`;
- no recursive continuity;
- auxiliary observations never become primary anchors.

## Independent coarse auxiliary observation model

The auxiliary channel is a **synthetic observation process** used only for simulation research. It is not a physical-sensor performance claim.

For every truth-visible frame, an auxiliary observation is synthesized with an RNG stream independent of the primary visual-candidate RNG.

### Availability

Fixed probability:

`p_aux_available = 0.96`

The auxiliary availability draw does not use visual-domain labels, primary candidate availability, primary errors, future observations, or controller state.

### Measurement noise

When available:

- lateral Gaussian sigma: `0.075 m`;
- altitude Gaussian sigma: `0.160 m`.

Independent rare-tail process:

- tail probability: `0.025`;
- if tail occurs, multiply both sigmas by a random factor uniformly distributed in `[2.5, 4.0]`.

The auxiliary measurement is generated as:

`aux_lateral = truth_lateral + independent_noise_lateral`

`aux_altitude = truth_altitude + independent_noise_altitude`

Truth is used here **only by the simulator to synthesize a noisy observation**. The resulting auxiliary measurement and its source flag are the only state values available to the estimator.

The auxiliary RNG seed is deterministically derived from the P14 split seed, family, frame, and a fixed P14 auxiliary-stream constant, and is independent of the primary candidate RNG stream.

### Use rule

If the unchanged primary stack already has an estimate, the auxiliary observation is ignored for the primary result.

If the primary stack has no estimate and the auxiliary observation is available:

- output the auxiliary lateral/altitude observation;
- source = `auxiliary_coarse_fallback`;
- do **not** append it to the primary anchor history;
- do **not** recursively propagate it.

If neither path is available, P14 remains unavailable.

## Four fixed uncertainty groups

1. `base_output` — all available non-primary-continuity, non-auxiliary primary outputs;
2. `primary_continuity_h3` — soft primary continuity at horizon exactly 3;
3. `primary_continuity_h47` — soft primary continuity at horizons 4..7;
4. `auxiliary_fallback` — independent coarse fallback outputs.

No pooled fallback and no data-dependent group reassignment are allowed.

## Stage 1 — base grouped conformal

On seed `649649`, freeze finite-sample absolute-error conformal radii separately for each group, axis, and target `{0.50,0.68,0.80,0.90,0.95}` using order statistic `ceil((n+1)*q)`.

Minimum base-calibration rows:

- `base_output >= 1500`;
- `primary_continuity_h3 >= 150`;
- `primary_continuity_h47 >= 100`;
- `auxiliary_fallback >= 300`.

## Stage 2 — compositional transfer calibration

On disjoint seed `660660`, for each group/axis/target:

`ratio = abs_error / max(R_base(group,axis,q), 1e-9)`

Freeze finite-sample conformal multiplier `T(group,axis,q)` and define:

`R_final = R_base * T`

Radii are monotonized over increasing targets.

Minimum transfer-calibration rows:

- `base_output >= 1200`;
- `primary_continuity_h3 >= 120`;
- `primary_continuity_h47 >= 80`;
- `auxiliary_fallback >= 300`.

No learned uncertainty model or post-challenge multiplier is allowed.

## Seen-challenge minimums

- `base_output >= 1000`;
- `primary_continuity_h3 >= 100`;
- `primary_continuity_h47 >= 60`;
- `auxiliary_fallback >= 200`.

If any minimum fails, P14 stops before protected validation.

## Primary gates

### H1 — useful availability

Truth-visible output availability `>=0.95`.

P14 deliberately raises the availability bar above P13 because the auxiliary channel exists specifically to address anchorless missingness.

### H2 — overall 95% coverage

Lateral and altitude empirical 95% coverage each in `[0.90,0.98]`.

### H3 — calibration curve

Mean absolute coverage error over both axes and targets `{50%,68%,80%,90%,95%}` `<=0.06`.

### H4 — overall interval efficiency

For each axis:

- median 95% half-width / all-available p95 absolute error `<=1.25`;
- p95 95% half-width / all-available p95 absolute error `<=2.25`.

### H5 — primary-continuity honesty

Across both primary-continuity groups combined:

- lateral and altitude 95% coverage each in `[0.88,0.99]`;
- p95 95% half-width / primary-continuity p95 error `<=2.75` on each axis.

### H6 — base-output honesty

On `base_output` only:

- lateral and altitude 95% coverage each in `[0.90,0.98]`;
- p95 half-width / base p95 error `<=2.25` on each axis.

### H7 — auxiliary-fallback honesty

On `auxiliary_fallback` only:

- lateral and altitude 95% coverage each in `[0.90,0.98]`;
- p95 half-width / auxiliary p95 error `<=2.25` on each axis.

### H8 — shift discrimination

Trajectory-level inherited visual severity AUROC `>=0.85` remains a diagnostic only. Auxiliary observations are not used to compute this diagnostic.

## Secondary diagnostics

Report without candidate tuning:

- fraction of previously-primary-unavailable rows recovered by auxiliary fallback;
- auxiliary fallback row count by composition;
- primary continuity coverage/error by exact horizon;
- number of rows still unavailable after auxiliary fallback;
- count of sequences with no primary candidate but at least one auxiliary output;
- auxiliary MAE/p95 and tail frequency;
- source composition of all final outputs.

## Staging / exposure rules

1. Generate fit + base calibration + transfer calibration only.
2. Freeze and hash the final four-group P14 candidate.
3. Evaluate the exact candidate once on seen challenge `671671`.
4. If any row minimum or H1-H7 fails, stop; protected seed `682682` remains unexposed.
5. If H1-H7 all pass, evaluate the exact frozen candidate once on protected seed `682682`.

No P14 scientific constant, auxiliary noise parameter, grouping rule, radius, transfer multiplier, or gate may change after challenge exposure.

Even a complete P14 protected-validation pass does **not** authorize the final Phase 11 frozen holdout. Final-holdout exposure still requires separate explicit user approval at an exact later freeze checkpoint.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
- no claim that a real auxiliary sensor matches the P14 synthetic observation model
