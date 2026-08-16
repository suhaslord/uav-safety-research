# Phase 11 P1 preregistration — adaptive reliability under compositional shift

## Status

**PREREGISTERED BEFORE P1 DATA GENERATION**

Branch: `phase11-p1-adaptive-reliability`

P0 challenge seed `33033` is permanently seen and excluded from P1 fitting, calibration, validation, and any future hidden test.

The public site remains frozen at `site-v1-frozen` / `04f8586cff06abfb7f3729c1b1802c8aa77f9f03`.

## Research question

**Can a continuous, causally observable compound-severity score scale uncertainty enough to recover honest coverage under unseen multi-factor shift while retaining useful perception, using abstention only as a narrow last resort?**

P1 remains a controlled simulation-only reliability-layer development benchmark. It does not change the underlying Phase 10R perception candidate, controller, or any frozen historical evidence.

## Motivation from frozen P0

P0 showed that shift discrimination was strong (`AUROC 0.9097`) but the response was poor: context-bin 95% coverage transferred at only `53.55%` lateral / `52.67%` altitude, while q90 abstention reduced the tail but left only `27.50%` truth-visible availability.

P1 therefore replaces discrete low/medium/high strata with a continuous uncertainty envelope and evaluates abstention only after adaptive uncertainty has been applied.

## New P1 split boundary

All P1 seeds and trajectory families are new.

- fit seed: `41111`
- calibration seed: `52222`
- compositional challenge seed: `63333`
- frames per sequence: `60`

Trajectory families are disjoint:

- fit: families `12..17`
- calibration: families `18..20`
- challenge: families `21..23`

The separation unit is the complete sequence. Adjacent frames are never randomly split.

## Development domains

Fit and calibration use only nominal or single-factor conditions:

1. `nominal`
2. `edge`
3. `small_scale`
4. `oblique`
5. `dim`
6. `blur_noise`
7. `temporal_dropout`
8. `low_contrast`

## New compositional challenge domains

The P1 challenge contains combinations not used as P0 challenge rows and not present in P1 fit/calibration:

1. `edge+low_contrast`
2. `small_scale+dim`
3. `oblique+blur_noise`
4. `edge+temporal_dropout+low_contrast`
5. `small_scale+dim+blur_noise`
6. `edge+oblique+temporal_dropout`
7. `small_scale+oblique+low_contrast`
8. `edge+small_scale+dim+temporal_dropout`

Challenge seed `63333` becomes permanently seen immediately after first generation/evaluation.

## Inference-visible risk components

P1 uses the same six causal risk components from P0:

- edge / visibility risk
- small-scale risk
- obliquity risk
- appearance risk
- temporal innovation risk
- track-instability / reacquisition risk

No domain name, true error, truth geometry, trajectory family, future frame, or challenge label may enter the reliability method.

## Compound-severity score

Let the six normalized component risks be sorted descending as `r1 >= r2 >= r3 >= ...` and let `risk_score` be the frozen P0 weighted average.

Define:

`compound = 0.55*r1 + 0.30*r2 + 0.15*r3`

`severity = clip(0.55*risk_score + 0.45*compound, 0, 1)`

The formula and coefficients are fixed before P1 challenge generation.

## Adaptive envelope construction

For each axis independently:

1. On the **fit split only**, use available truth-visible observations.
2. Divide severity into fixed bins:
   - `[0.00,0.15)`
   - `[0.15,0.30)`
   - `[0.30,0.45)`
   - `[0.45,0.60)`
   - `[0.60,0.75)`
   - `[0.75,1.00]`
3. In each bin compute the empirical `75th` percentile absolute error. If a bin contains fewer than `50` observations, use the fit-global 75th percentile for that bin.
4. Enforce a nondecreasing envelope by cumulative maximum from low to high severity.
5. Use fixed bin centers `0.075, 0.225, 0.375, 0.525, 0.675, 0.875` and linear interpolation between centers.
6. Below the first center, use the first radius. Above the final center, linearly extrapolate using the final two anchors, capped at `2.5x` the final fitted anchor.

This fitted function is called `base_radius(axis, severity)`.

## Split-conformal correction

On the **calibration split only**, for every available truth-visible observation compute:

`ratio = absolute_error / max(base_radius(axis, severity), 1e-9)`

For every target `q in {0.50, 0.68, 0.80, 0.90, 0.95}`, freeze a finite-sample split-conformal multiplier using order statistic:

`ceil((n + 1) * q)`

The final adaptive interval radius is:

`adaptive_radius(axis, q) = base_radius(axis, severity) * gamma(axis, q)`

No challenge residual may affect the fitted envelope or `gamma` multipliers.

## Last-resort width-cap abstention

Adaptive intervals are evaluated first without abstention.

For the selective method only, compute the final 95% adaptive radius on available calibration observations and freeze per-axis caps at:

`1.25 * calibration 99th percentile adaptive radius`

A challenge observation is accepted only when the candidate is available and both axis radii are at or below their frozen caps.

No risk-score quantile threshold is used in P1.

## Methods compared

Exactly three methods are reported:

1. **Global conformal** — calibration-global residual radii, no context scaling.
2. **Adaptive severity conformal** — continuous severity envelope plus calibration conformal multiplier, no abstention.
3. **Adaptive severity + width-cap abstention** — method 2 plus the preregistered width caps.

No neural model, learned image model, arbitrary hyperparameter search, post-challenge threshold sweep, or challenge-dependent inflation is allowed.

## Primary gates

### H1 — honest 95% coverage transfer

Adaptive severity conformal on all available challenge observations must achieve 95% empirical coverage in `[0.90, 0.98]` on **both** lateral and altitude axes.

### H2 — useful sharpness

For adaptive severity conformal, challenge median full 95% interval width must be no more than `1.60x` the corresponding global-conformal median width on each axis.

Additionally, challenge p95 full interval width must be no more than `2.50x` the corresponding global-conformal p95 width on each axis.

All four width conditions must pass.

### H3 — last-resort selectivity without availability collapse

For adaptive severity + width-cap abstention:

- retain at least `90%` of candidate-available challenge observations;
- truth-visible usable availability must remain at least `63%`;
- accepted lateral p95 error must improve by at least `10%` versus accepting all candidate-available challenge observations;
- accepted altitude p95 error must improve by at least `10%` versus accepting all candidate-available challenge observations.

All four components must pass.

### H4 — shift severity discrimination

Trajectory-level mean compound severity must distinguish P1 calibration sequences from P1 compositional challenge sequences with AUROC `>=0.85`.

This is diagnostic and is not a safety claim.

### H5 — calibration curve quality

For adaptive severity conformal across targets `50%, 68%, 80%, 90%, 95%`, mean absolute coverage error over both axes must be `<=0.06` on the full available challenge set.

## Secondary diagnostics

Report:

- candidate availability before abstention;
- retained fraction conditional on candidate availability;
- MAE and p95 point error by axis;
- coverage at every target;
- median and p95 interval width;
- metrics by challenge domain;
- metrics by severity quintile;
- worst three challenge domains by 95% undercoverage;
- error conditional on the system reporting a 95% interval.

Secondary diagnostics cannot override a failed primary gate.

## Exposure policy

After challenge seed `63333` is generated or evaluated:

- it is permanently seen;
- P1 coefficients, bins, fit quantile, extrapolation cap, conformal rule, width caps, and gates cannot be changed and then reevaluated on `63333` as unseen evidence;
- any P1 follow-up method change requires another preregistered split with new seeds and trajectory families.

A protected Phase 11 frozen holdout remains **ungenerated and unexposed**. It requires a separate explicit approval checkpoint after a candidate is frozen.

## Required artifacts

P1 must emit:

- `fit_frames.csv`
- `calibration_frames.csv`
- `challenge_frames.csv`
- `adaptive_calibration.json`
- `benchmark_result.json`
- `benchmark_summary.md`
- `manifest.json`

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
- P1 coverage statements apply only to the defined controlled synthetic benchmark distributions
- mixed and negative results must be preserved
