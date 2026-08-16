# Phase 11 preregistration — domain-shift-aware perception reliability

## Status

**PREREGISTERED BEFORE PHASE 11 DATA GENERATION**

Preregistration branch: `phase11-domain-shift-development`

Public-site freeze point: `site-v1-frozen` at commit `04f8586cff06abfb7f3729c1b1802c8aa77f9f03`.

This preregistration is the exact development protocol authorized before any Phase 11 benchmark rows are generated. Phase 10R remains closed for result-driven retuning.

## Research question

**Can AegisLand detect when visual conditions move outside its calibrated reliability envelope and either widen uncertainty or abstain enough to recover honest coverage without making useful perception unavailable?**

Phase 11 is not a new image-to-pose model. P0 isolates the reliability layer around the frozen Phase 10R perception candidate.

## Frozen starting point

Phase 11 inherits without rewriting:

- Phase 10R candidate SHA `e1d566f8baa47bf10f9bdf39dd5988724208be80`;
- Phase 10R frozen-holdout verdict: mixed / failed overall;
- final Phase 10R 95% coverage: `84.3%` lateral / `79.7%` altitude;
- final Phase 10R truth-visible miss rate: `20.0%`;
- final Phase 10R ambiguous-view MAE improvement: `79.2%` lateral / `73.7%` altitude;
- final Phase 10R ambiguous-view p95 improvement: `-1.1%` lateral / `7.3%` altitude.

The Phase 10R validation seed `271828`, the final Phase 10R holdout, and all other exposed Phase 10R evidence are **permanently seen**. They may motivate Phase 11 but may not be used for fitting, calibration, threshold selection, validation, or any future hidden test.

## Phase 11 P0 benchmark scope

P0 is a new simulation-only controlled domain-shift benchmark around the frozen Phase 10R candidate. It evaluates uncertainty and abstention, not controller behavior.

### Sequence unit

- `60` frames per sequence;
- full trajectories/sequences are the separation unit;
- no random adjacent-frame splitting;
- all benchmark seeds below are new to Phase 11.

### Fixed split seeds

- fit: `11011`;
- calibration: `22022`;
- compositional challenge validation: `33033`.

These seeds are fixed before generation. Changing them after exposure constitutes a new benchmark version and must be documented as such.

### Split families

- fit trajectories: families `0..5`;
- calibration trajectories: families `6..8`;
- challenge-validation trajectories: families `9..11`.

Families are disjoint by construction.

## Domain design

### Fit/calibration domains

The fitting and calibration splits contain nominal conditions plus **single-factor shifts only**:

1. `nominal`
2. `edge`
3. `small_scale`
4. `oblique`
5. `dim`
6. `blur_noise`
7. `temporal_dropout`
8. `low_contrast`

No multi-factor challenge composition listed below may appear in fit or calibration.

### Compositional challenge domains

Validation contains unseen combinations of individually familiar factors:

1. `edge+dim`
2. `edge+blur_noise`
3. `small_scale+oblique`
4. `dim+blur_noise`
5. `edge+small_scale+oblique`
6. `small_scale+blur_noise+temporal_dropout`
7. `oblique+dim+temporal_dropout`
8. `edge+oblique+dim+blur_noise`

The purpose is compositional transfer, not random frame generalization.

## Inference-visible reliability features

Only features available causally at inference time may be used by the reliability layer:

- estimated edge-margin ratio;
- estimated visible-fraction proxy;
- projected target scale in pixels;
- projective/obliquity proxy;
- frame brightness mean;
- frame contrast standard deviation;
- blur proxy from Laplacian variance;
- temporal innovation magnitude;
- recent track-stability score;
- detector/candidate source category;
- reacquisition flag.

Truth labels, true error, domain name, trajectory family, and future frames are forbidden as inputs to the reliability score.

## Candidate methods

Exactly four methods are compared in P0:

1. **Frozen reference** — frozen Phase 10R point estimate with a source-independent development reference interval; no Phase 11 adaptation.
2. **Global conformal** — one split-conformal absolute-residual radius per axis fitted only on the Phase 11 calibration split.
3. **Context-conditioned conformal** — predeclared low-capacity risk strata from inference-visible reliability features; one conformal radius per stratum with global fallback when a stratum has fewer than `40` calibration observations.
4. **Shift-aware abstention** — context-conditioned conformal plus abstention above a calibration-frozen reliability-risk threshold.

No learned image model, learned residual regressor, neural calibrator, or post-validation threshold tuning is allowed in P0.

## Predeclared context score

A scalar reliability-risk score in `[0,1]` is formed from six normalized components:

- edge/visibility risk: weight `0.25`;
- small-scale risk: `0.15`;
- obliquity risk: `0.15`;
- appearance risk (brightness/contrast/blur): `0.20`;
- temporal innovation risk: `0.15`;
- track-instability/reacquisition risk: `0.10`.

The score is a fixed weighted average. Weights may not be changed after the challenge split is exposed.

Context strata are fixed as:

- `low`: score `<0.30`;
- `medium`: `0.30 <= score < 0.60`;
- `high`: score `>=0.60`.

The abstention threshold is the empirical `90th` percentile of the calibration-split risk score, frozen before challenge validation.

## Conformal rule

For target coverage `q=0.95`, the split-conformal absolute-residual radius uses the finite-sample order statistic

`ceil((n + 1) * q)`

clipped to the available sorted residuals.

Calibration uses accepted, truth-visible calibration observations only. Challenge labels are not used to derive radii or thresholds.

## Primary hypotheses and gates

### H1 — coverage transfer

On the full compositional challenge split, accepted 95% intervals must achieve empirical coverage between **90% and 98%** on both lateral and altitude axes.

**Pass requires both axes.**

### H2 — useful sharpness

For context-conditioned conformal, median full interval width on accepted challenge observations must be no more than **1.35x** the corresponding global-conformal median width on each axis.

**Pass requires both axes.**

### H3 — selective reliability

For shift-aware abstention, compared with accepting all available frozen-candidate challenge observations:

- accepted-observation lateral p95 absolute error improves by **>=25%**;
- accepted-observation altitude p95 absolute error improves by **>=25%**;
- truth-visible usable availability remains **>=70%**.

**Pass requires all three.**

### H4 — shift discrimination

The fixed reliability-risk score must distinguish nominal/single-factor calibration sequences from compositional challenge sequences at trajectory level with AUROC **>=0.80**.

This is diagnostic only; it does not establish safety.

## Secondary diagnostics

Report without using them as tuning objectives:

- coverage at 50%, 68%, 80%, 90%, and 95%;
- mean absolute coverage error across those levels;
- median and p95 interval width;
- MAE and p95 absolute point error;
- availability and false-positive rate;
- metrics by domain, risk stratum, detector source, and reacquisition state;
- worst three challenge domains by accepted p95 error;
- error conditional on the system saying an observation is trustworthy.

## Candidate selection rule

P0 is not allowed to search arbitrary variants. The four methods above are evaluated exactly as specified. If multiple methods pass all applicable gates, prefer in order:

1. higher minimum-axis 95% coverage closeness to `0.95`;
2. smaller worst-axis median interval width;
3. higher availability;
4. simpler method (`global` before `context` before `abstention`) if still tied.

A method that fails a preregistered gate cannot be described as passing because another secondary metric improved.

## Exposure and retuning policy

After challenge seed `33033` is generated or evaluated:

- it becomes permanently seen evidence;
- no P0 weight, stratum, conformal rule, abstention quantile, or detector logic may be changed and then re-evaluated on the same challenge split as if it were unseen;
- any follow-up model change requires a newly preregistered development/challenge split.

A future protected Phase 11 frozen holdout is **not generated or exposed by this milestone**. It requires a separate exact-freeze approval after a candidate is frozen.

## Required artifacts

The benchmark run must emit:

- `fit_frames.csv`;
- `calibration_frames.csv`;
- `challenge_frames.csv`;
- `calibration.json`;
- `benchmark_result.json`;
- `benchmark_summary.md`;
- `manifest.json` with SHA-256 hashes;
- the exact benchmark config and code commit.

Raw rendered frame bytes are optional for P0 because the benchmark is a reliability-layer development benchmark; if raw imagery is emitted, hashes must be preserved.

## Claim boundaries

- `simulation_only = true`;
- `safety_acceptance = false`;
- `controller_tuning_allowed = false`;
- no physical-flight validation claim;
- no controller-performance claim;
- coverage statements apply only to the defined simulated benchmark distributions;
- negative and mixed results must be preserved;
- a future protected holdout cannot be exposed without a new explicit approval checkpoint.
