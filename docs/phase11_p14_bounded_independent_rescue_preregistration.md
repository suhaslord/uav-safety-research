# Phase 11 P14 preregistration — bounded primary continuity + independent rescue

## Status

**PREREGISTERED BEFORE P14 DATA GENERATION**

Branch: `phase11-p14-bounded-independent-rescue`

Authoritative predecessor: P13 severity-conditioned Mondrian direct conformal on branch `phase11-p13-severity-mondrian-conformal`, frozen through read-only forensics at `6a320ba85794a6aa9d597e30b7f206222f2f5ca8`.

P13 permanently exposed fit `638638`, partition `649649`, calibration `660660`, and seen transfer `671671`. P13 protected seed `682682` was never exposed and is retired. None of those seeds may be reused by P14.

The older branches `phase11-p14-independent-coarse-fallback` and `phase11-p15-source-observation-calibration` belong to an incompatible earlier P13 lineage and are explicitly non-authoritative for this study.

## Research question

**Can an inference-independent coarse observation rescue frames where the frozen seven-frame primary continuity path correctly becomes unavailable, while preserving the severity-conditioned uncertainty honesty recovered by P13?**

P14 intentionally does **not** extend the primary extrapolation horizon beyond seven frames. The primary path remains bounded and nonrecursive. Missing primary evidence is addressed by independent evidence rather than by making extrapolation less conservative.

## Scientific changes relative to current P13

Exactly one estimator-level change is allowed:

1. when the unchanged P13/P9 primary stack has no estimate on a truth-visible frame, a preregistered independent synthetic coarse observation may provide a one-frame rescue output.

Unchanged:

- genuine primary candidates are the only primary motion anchors;
- temporal bridge horizons 1–2;
- soft bounded-influence primary continuity horizons 3–7;
- q99 fit-only velocity caps;
- q95 fit-only innovation scales;
- `soft_scale_multiplier = 3.0`;
- 0.50 / 0.50 previous-slope / soft-updated-slope blend;
- damping `0.85`;
- no recursive primary continuity;
- low/mid/high inference-visible severity conditioning;
- finite-sample direct conformal calibration at targets `{0.50, 0.68, 0.80, 0.90, 0.95}`.

The rescue observation never becomes a primary anchor and is never recursively propagated.

## Fresh P14 evidence boundary

- fit seed: `704704`
- severity-partition seed: `715715`
- conformal-calibration seed: `726726`
- seen-transfer seed: `737737`
- protected-validation seed: `748748`
- frames per sequence: `60`

Fresh complete-sequence family units:

- fit: `700..705` (6)
- partition: `706..729` (24)
- calibration: `730..761` (32)
- seen transfer: `762..777` (16)
- protected validation: `778..793` (16)

No family may cross evidence roles.

## Truth-independent event strata

Partition, calibration, transfer, and validation families are allocated before generation to four equal intervention strata. The intervention is determined only by family identity and frame index; it may not inspect truth values, primary error, rescue error, confidence, severity, or future observations.

1. `bootstrap5`: suppress primary candidates at frames `0..4`.
2. `gap3`: suppress primary candidates at frames `12..14` and `42..44`.
3. `gap7`: suppress primary candidates at frames `12..18` and `42..48`.
4. `gap12`: suppress primary candidates at frames `12..23` and `42..53`.

Purpose:

- `bootstrap5` powers causal rescue of insufficient-anchor states;
- `gap3` powers h3 primary continuity;
- `gap7` powers h4–7 primary continuity;
- `gap12` powers the deliberate boundary where primary continuity must stop after h7 and independent evidence must take over.

All full trajectories are retained; no outcome-based row selection is allowed.

## Domains

### Partition + calibration domains

1. `edge+temporal_dropout`
2. `small_scale+temporal_dropout`
3. `oblique+temporal_dropout`
4. `dim+temporal_dropout`
5. `blur_noise+temporal_dropout`
6. `low_contrast+temporal_dropout`
7. `edge+small_scale+temporal_dropout`
8. `oblique+dim+temporal_dropout`

### Seen-transfer domains

1. `edge+blur_noise+temporal_dropout`
2. `small_scale+dim+low_contrast+temporal_dropout`
3. `oblique+blur_noise+temporal_dropout`
4. `edge+small_scale+dim+temporal_dropout`
5. `edge+oblique+low_contrast+temporal_dropout`
6. `small_scale+oblique+dim+blur_noise+temporal_dropout`
7. `edge+dim+blur_noise+low_contrast+temporal_dropout`
8. `edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout`

### Protected-validation domains

1. `edge+small_scale+low_contrast+temporal_dropout`
2. `small_scale+oblique+blur_noise+temporal_dropout`
3. `oblique+dim+low_contrast+temporal_dropout`
4. `edge+dim+blur_noise+temporal_dropout`
5. `small_scale+dim+blur_noise+low_contrast+temporal_dropout`
6. `edge+oblique+dim+blur_noise+temporal_dropout`
7. `edge+small_scale+oblique+low_contrast+temporal_dropout`
8. `edge+small_scale+oblique+dim+low_contrast+temporal_dropout`

Protected seed `748748` must not be generated until the exact frozen P14 candidate passes every preregistered seen-transfer primary gate.

## Independent rescue observation model

This is a **synthetic simulation observation process**, not a claim about any real sensor.

For each truth-visible frame, a dedicated RNG stream independent of the primary visual candidate RNG produces a potential coarse observation. Its probability and noise distribution do not depend on visual-domain labels, primary availability, primary error, controller state, or future frames.

Fixed parameters:

- rescue availability probability: `0.95`;
- lateral Gaussian sigma: `0.10 m`;
- altitude Gaussian sigma: `0.20 m`;
- independent rare-tail probability: `0.02`;
- on a rare-tail draw, both sigmas are multiplied by exactly `3.0`.

When available, the simulator produces:

`rescue_lateral = truth_lateral + independent_noise_lateral`

`rescue_altitude = truth_altitude + independent_noise_altitude`

Truth is used only inside the simulator to synthesize this noisy observation. The estimator sees only the resulting observation, its availability bit, and its source flag.

### Use rule

- If the unchanged primary stack is available, use the primary output and ignore rescue for the final estimate.
- If the primary stack is unavailable and rescue is available, output the rescue observation with source `independent_coarse_rescue`.
- Do not append rescue observations to primary anchor history.
- Do not recursively propagate rescue observations.
- If both are unavailable, remain unavailable.

## Five fixed output groups

1. `base_output`
2. `continuity_h3`
3. `continuity_h45`
4. `continuity_h67`
5. `independent_coarse_rescue`

Every group is further partitioned into fixed low / mid / high inference-visible severity regimes, yielding 15 Mondrian cells.

## Stage A — severity partition freeze

On seed `715715`, freeze 1/3 and 2/3 severity quantile cutpoints separately within each of the five groups. The partition split is disjoint from conformal calibration.

Minimum partition rows before cutpoints may be frozen:

- base: `>=1200`
- h3: `>=180`
- h45: `>=120`
- h67: `>=80`
- rescue: `>=300`

No residual/error information may be used to choose the cutpoints.

## Stage B — direct severity-Mondrian conformal freeze

On disjoint seed `726726`, freeze finite-sample absolute-error conformal radii in all 15 cells for each axis and each target `{0.50,0.68,0.80,0.90,0.95}` using order statistic `ceil((n+1)*q)` and monotone cumulative maxima over increasing q.

Minimum calibration rows **per severity cell**:

- base: `>=300`
- h3: `>=60`
- h45: `>=45`
- h67: `>=30`
- rescue: `>=60`

No pooled fallback radius is allowed if a cell is underpowered. If any minimum fails, P14 stops before transfer.

## Seen-transfer and protected-validation minimums

Per complete evaluation split, minimum rows per severity cell:

- base: `>=120`
- h3: `>=20`
- h45: `>=15`
- h67: `>=10`
- rescue: `>=20`

If any required cell is underpowered, the split cannot pass.

## Primary gates — unchanged P13 standards plus rescue-specific anti-triviality gates

### H1 useful availability

Truth-visible output availability `>=0.92`.

### H2 overall 95% coverage

Lateral and altitude empirical 95% coverage each in `[0.90, 0.98]`.

### H3 calibration curve

MACE across targets `{50,68,80,90,95}%` and both axes `<=0.06`.

### H4 overall interval efficiency

For each axis:

- median 95% half-width / all-available p95 absolute error `<=1.25`;
- p95 95% half-width / all-available p95 absolute error `<=2.25`.

### H5 primary-continuity honesty

Across h3/h45/h67 primary-continuity rows:

- 95% coverage each axis in `[0.88,0.99]`;
- p95 half-width / primary-continuity p95 error `<=2.75` each axis.

### H6 base-output honesty

- 95% coverage each axis in `[0.90,0.98]`;
- p95 half-width / base-output p95 error `<=2.25` each axis.

### H7 inherited severity discrimination — diagnostic

Trajectory-level inherited visual-severity AUROC `>=0.85` is reported but remains diagnostic, matching P13.

### H8 high-severity honesty

Across all high-severity available rows:

- 95% coverage each axis in `[0.88,0.99]`;
- p95 half-width / high-severity p95 error `<=2.75` each axis.

### H9 rescue-output honesty

On `independent_coarse_rescue` rows only:

- 95% coverage each axis in `[0.90,0.98]`;
- p95 half-width / rescue p95 error `<=2.25` each axis.

### H10 rescue accuracy floor

To prevent a trivial availability win from arbitrarily noisy outputs:

- rescue lateral MAE `<=0.15 m`;
- rescue altitude MAE `<=0.30 m`;
- rescue lateral p95 absolute error `<=0.35 m`;
- rescue altitude p95 absolute error `<=0.70 m`.

### H11 rescue effectiveness

Among truth-visible rows where the unchanged primary stack is unavailable, at least `85%` must be recovered by the independent rescue output.

P14 transfer/validation passes only if cell minimums and H1–H6 + H8–H11 all pass. H7 is diagnostic only.

## Secondary diagnostics

Report without candidate tuning:

- natural-stream availability with event interventions removed;
- primary-unavailable reason counts before rescue;
- rescue recovery by `insufficient_anchors` vs `gap_beyond_horizon`;
- output-source composition by domain;
- exact h3/h4/h5/h6/h7 primary-continuity coverage/error;
- rescue rare-tail realization frequency;
- rows still unavailable after rescue;
- sequences with zero primary candidates but one or more rescue outputs.

## Staging and exposure rules

1. Generate fit + partition evidence only; freeze severity cutpoints.
2. Generate separate calibration evidence only; freeze and hash the exact P14 candidate.
3. Evaluate seen transfer `737737` exactly once.
4. If any required transfer minimum or H1–H6/H8–H11 fails, stop. `748748` remains unexposed and P15 remains untouched.
5. If every required transfer gate passes, evaluate the exact candidate once on protected validation `748748`.
6. No scientific constant, rescue parameter, intervention schedule, cutpoint, group, conformal radius, threshold, or gate may change after transfer exposure.
7. If protected validation passes every required gate, the exact P14 candidate is eligible for the separately preregistered P15 final holdout. The user explicitly authorized that conditional P15 exposure in the conversation on 2026-08-16.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
- no claim that any real auxiliary sensor matches this synthetic rescue model
- negative/mixed outcomes remain permanent evidence
