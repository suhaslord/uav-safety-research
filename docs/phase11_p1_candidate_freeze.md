# Phase 11 P1 candidate freeze — adaptive reliability under compositional shift

## Status

**CANDIDATE FROZEN BEFORE P1 VALIDATION EXPOSURE**

Phase 11 P0 is preserved as a mixed/failed result. P1 is a new simulation-only benchmark revision motivated by two P0 findings:

1. the P0 reliability score separated shifted from nominal trajectories well, but the fixed context bins did not transfer coverage;
2. the P0 synthetic generator collapsed `dim`, `blur_noise`, and `low_contrast` into one appearance latent while still increasing hidden interaction error with factor count. That creates an identifiability failure: two appearance factors can raise error without creating two distinguishable inference-visible cues.

P1 does **not** rewrite P0. It makes the new benchmark factor-identifiable by giving dimness, blur, and contrast separate inference-visible proxies.

## Exposure ledger

The following P1 design/pilot splits have already been generated during candidate development and are permanently **seen**:

- fit seed: `44044`, families `12..17`;
- calibration seed: `55055`, families `18..20`;
- exploratory development seed: `66066`, families `21..23`.

They may be used for P1 candidate selection but may never be described as hidden validation.

The protected P1 validation split is frozen here **before generation**:

- validation seed: `77077`;
- families: `24..26`;
- `60` frames per sequence;
- validation seed `77077` is ungenerated/unseen at this freeze checkpoint.

## P1 benchmark generator

Fit/calibration domains remain nominal plus single-factor shifts:

1. `nominal`
2. `edge`
3. `small_scale`
4. `oblique`
5. `dim`
6. `blur_noise`
7. `temporal_dropout`
8. `low_contrast`

Exploratory development domains already seen during candidate selection:

1. `edge+dim`
2. `small_scale+blur_noise`
3. `oblique+low_contrast`
4. `edge+temporal_dropout`
5. `dim+blur_noise`
6. `small_scale+oblique`
7. `edge+low_contrast+temporal_dropout`
8. `small_scale+dim+blur_noise`

Frozen P1 validation domains, not generated before this checkpoint:

1. `edge+blur_noise`
2. `small_scale+dim`
3. `oblique+temporal_dropout`
4. `blur_noise+low_contrast`
5. `edge+small_scale+oblique`
6. `dim+low_contrast+temporal_dropout`
7. `edge+oblique+blur_noise+low_contrast`
8. `small_scale+oblique+dim+temporal_dropout`

### Factor-identifiable appearance cues

P1 separates the synthetic appearance factors into causal proxies available to the reliability layer:

- `dim` primarily lowers `brightness_mean`;
- `blur_noise` primarily lowers `laplacian_var` and mildly reduces contrast;
- `low_contrast` primarily lowers `contrast_std` and mildly reduces sharpness.

The error model retains compositional interaction/tail stress, but those interactions are no longer driven by completely hidden appearance-factor multiplicity.

## Frozen inference-visible reliability components

Eight components are computed causally from the current/past observation state:

- edge visibility risk;
- small-scale risk;
- obliquity risk;
- dimness risk;
- blur risk;
- contrast risk;
- temporal innovation risk;
- track/reacquisition risk.

Weights for the scalar risk score are frozen as:

- edge: `0.18`
- scale: `0.12`
- obliquity: `0.12`
- dim: `0.12`
- blur: `0.12`
- contrast: `0.10`
- temporal: `0.14`
- track: `0.10`

A coactivation count is the number of the seven primary cues (all except track) above `0.45`.

## Frozen P1 candidate

### 1. Short-horizon temporal bridge

When the frozen candidate has no observation, P1 may produce a non-recursive constant-velocity bridge for at most `2` frames using the two most recent genuine candidate estimates.

- bridged estimates are **not** fed back into the bridge history;
- bridge horizon is exposed to the reliability layer;
- the bridge changes availability only, not controller behavior.

### 2. Continuous severity / selection score

`severity = risk_score + 0.75 * (coactivation_count / 7) + 0.25 * bridge_horizon`

Frozen acceptance threshold:

`severity <= 0.40078671864763`

This threshold was selected on the seen P1 exploratory development split. It may not change after validation exposure.

### 3. Low-capacity error-scale model

Separate lateral and altitude log-error scale models use ridge regression with `lambda = 1.0` on the seen P1 fit split.

Inputs are limited to inference-visible quantities:

- the eight reliability components;
- risk score and risk score squared;
- bridge horizon and bridge-horizon × risk interaction;
- source one-hots for known ArUco, regeometry, partial-edge, and temporal-bridge outputs.

Truth error is used only as the training target on the seen fit split.

### 4. Normalized conformal calibration

On accepted rows of the seen calibration split, the method conformalizes absolute residual divided by the predicted scale and the fixed compositional multiplier below.

For each row:

`multiplier = 1 + 3 * coactivation_count + 6 * risk_score + 2 * bridge_horizon`

The 95% half-width is:

`Q95(normalized calibration residual) × predicted_scale × multiplier`

The finite-sample conformal order statistic remains `ceil((n + 1) * q)` clipped to the available residuals.

## Seen exploratory-development checkpoint

Before validation exposure, the frozen candidate produced on seen development seed `66066`:

- usable availability: `70.0%`;
- accepted lateral p95 improvement versus all P1 outputs: `46.8%`;
- accepted altitude p95 improvement: `42.1%`;
- lateral 95% coverage: `93.65%`;
- altitude 95% coverage: `94.54%`;
- median half-width / accepted p95 error: `1.10x` lateral / `1.29x` altitude;
- trajectory-level severity AUROC versus calibration: `0.953`.

These are **seen development metrics**, not validation claims.

## P1 validation gates

### H1 — selective coverage transfer

On accepted P1 validation outputs, 95% empirical coverage must be between **90% and 98%** on both lateral and altitude axes.

### H2 — interval efficiency

For each axis:

`median 95% half-width / accepted p95 absolute error <= 1.50`

This prevents a trivial always-wide interval while allowing honest widening under compositional shift.

### H3 — useful selective reliability

Compared with accepting every available P1 output before the severity gate:

- accepted lateral p95 absolute error improves by **>=25%**;
- accepted altitude p95 absolute error improves by **>=25%**;
- truth-visible usable availability remains **>=70%**.

All three are required.

### H4 — shift discrimination

Trajectory-level mean severity must distinguish single-factor calibration trajectories from compositional validation trajectories with AUROC **>=0.85**.

### Overall P1 verdict

P1 passes only if H1, H2, H3, and H4 all pass. Mixed or failed outcomes are frozen as observed.

## Validation exposure rule

Once seed `77077` is generated or evaluated:

- it is permanently seen;
- no risk weight, cue threshold, bridge horizon, severity coefficient, acceptance threshold, ridge basis, ridge lambda, conformal rule, or multiplier coefficient may change and then be re-evaluated on `77077` as if unseen;
- any follow-up method change requires a new benchmark revision with a new validation seed.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- P1 remains a synthetic reliability-layer benchmark, not new raw-camera evidence
