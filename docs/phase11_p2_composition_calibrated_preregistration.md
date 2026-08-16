# Phase 11 P2 preregistration — composition-calibrated uncertainty budget

## Status

**PREREGISTERED BEFORE P2 DATA GENERATION**

Branch: `phase11-p2-uncertainty-budget`

P0 challenge seed `33033`, duplicate exploratory seed `63333`, and P1 validation seed `77077` are permanently seen and excluded from P2 fitting, calibration, candidate selection, validation, and any future hidden test.

The public site remains frozen at `site-v1-frozen` / `04f8586cff06abfb7f3729c1b1802c8aa77f9f03`.

## Research question

**Can a low-capacity transfer-calibration layer learned from some compositional shifts convert P1's strong shift signal into honest uncertainty on different unseen compositions while preserving nearly all available perception?**

P2 does not change the frozen Phase 10R image-to-pose candidate or any controller behavior. It retains the P1 factor-identifiable synthetic benchmark and short-horizon bridge, removes the P1 global severity accept/reject cutoff, and moves reliability adaptation into the uncertainty envelope.

## Motivation from frozen P1

P1 validation showed:

- preselection output availability: `89.24%`;
- trajectory-level shift AUROC: `0.9722`;
- accepted p95 improvement: `57.22%` lateral / `51.16%` altitude;
- 95% coverage: `87.68%` lateral / `88.94%` altitude;
- final usable availability: only `43.96%`.

The dominant failure was therefore the binary global severity threshold, not lack of estimates or inability to identify shift. P2 preserves continuous uncertainty for all available outputs and uses abstention only when the resulting interval exceeds a development-frozen uncertainty budget.

## New P2 exposure boundary

All seeds and trajectory families below are new.

- fit seed: `88088`
- single-factor calibration seed: `99099`
- compositional transfer-calibration seed: `101101`
- protected validation seed: `112112`
- frames per sequence: `60`

Trajectory families are disjoint:

- fit: `27..32`
- single-factor calibration: `33..35`
- transfer calibration: `36..38`
- protected validation: `39..41`

The complete sequence is the split unit. Adjacent frames are never randomly split.

## Domains

### Fit / single-factor calibration

1. `nominal`
2. `edge`
3. `small_scale`
4. `oblique`
5. `dim`
6. `blur_noise`
7. `temporal_dropout`
8. `low_contrast`

### Seen transfer-calibration compositions

These may be used to freeze P2 transfer multipliers and uncertainty budgets:

1. `edge+dim`
2. `small_scale+blur_noise`
3. `oblique+low_contrast`
4. `edge+temporal_dropout`
5. `dim+blur_noise`
6. `small_scale+oblique`
7. `edge+low_contrast+temporal_dropout`
8. `small_scale+dim+blur_noise`

### Protected validation compositions

These must not be generated before the P2 candidate-freeze checkpoint:

1. `edge+blur_noise`
2. `small_scale+dim`
3. `oblique+temporal_dropout`
4. `blur_noise+low_contrast`
5. `edge+small_scale+oblique`
6. `dim+low_contrast+temporal_dropout`
7. `edge+oblique+blur_noise+low_contrast`
8. `small_scale+oblique+dim+temporal_dropout`

The protected validation seed `112112` becomes permanently seen immediately after first generation/evaluation.

## Frozen estimator layer inherited from P1

P2 inherits unchanged:

- factor-identifiable dim / blur / contrast cues;
- the P1 short-horizon non-recursive temporal bridge with maximum horizon `2`;
- P1 inference-visible risk components;
- P1 low-capacity ridge error-scale basis and `lambda = 1.0`;
- P1 uncertainty multiplier form:
  `1 + 3*coactivation_count + 6*risk_score + 2*bridge_horizon`.

P2 explicitly **does not use** P1's global severity acceptance threshold.

## P2 calibration method

### Stage A — scale model

Fit separate lateral and altitude log-error scale models on every available truth-visible P2 fit observation using the unchanged P1 ridge basis.

### Stage B — single-factor normalized conformal

On every available truth-visible single-factor calibration observation, compute:

`normalized_residual = abs_error / (predicted_scale * P1_multiplier)`

For each axis and target `q in {0.50, 0.68, 0.80, 0.90, 0.95}`, compute the finite-sample conformal order statistic:

`ceil((n + 1) * q)`

This produces `Q_single(axis,q)`.

### Stage C — compositional transfer calibration

On every available truth-visible transfer-calibration observation, compute the provisional radius:

`R_single = Q_single(axis,q) * predicted_scale * P1_multiplier`

Then compute:

`transfer_ratio = abs_error / max(R_single, 1e-9)`

For each axis and target q, freeze:

`T(axis,q) = finite_sample_conformal_q(transfer_ratio)`

The final P2 radius is:

`R_P2(axis,q) = R_single * T(axis,q)`

To preserve nested intervals, the resulting final q radii are monotonized per observation by cumulative maximum in target order `0.50 -> 0.68 -> 0.80 -> 0.90 -> 0.95`.

No protected-validation residual enters `Q_single`, `T`, or the scale model.

## Last-resort uncertainty budget

Hard abstention is not based on severity.

On the seen transfer-calibration split, compute the final P2 95% half-widths. Freeze per-axis uncertainty budgets as:

`budget(axis) = 1.10 * empirical 99th percentile final P2 95% half-width`

At evaluation time an otherwise available output is accepted only if both lateral and altitude P2 95% half-widths are at or below their frozen budgets.

The budget is a utility bound on uncertainty size, not a truth-error threshold.

## Primary gates

### H1 — full-availability coverage transfer

Before uncertainty-budget abstention, final P2 95% intervals on all available protected-validation outputs must achieve empirical coverage in `[0.90, 0.98]` on both axes.

### H2 — calibration-curve quality

Before abstention, mean absolute coverage error across `{50%,68%,80%,90%,95%}` over both axes must be `<= 0.06`.

### H3 — interval efficiency

Before abstention:

- median 95% half-width / all-available p95 absolute error must be `<= 1.25` on each axis;
- p95 95% half-width / all-available p95 absolute error must be `<= 2.25` on each axis.

All four conditions must pass.

### H4 — uncertainty-budget availability

After the frozen uncertainty budget:

- retain at least `90%` of preselection-available outputs;
- truth-visible usable availability must be at least `80%`;
- accepted p95 error must not be worse than all-available p95 error on either axis.

All three conditions must pass.

### H5 — shift discrimination remains informative

Trajectory-level mean P1 severity must distinguish P2 single-factor calibration trajectories from protected compositional validation trajectories with AUROC `>= 0.85`.

H5 is diagnostic and is not a safety claim.

## Candidate-freeze rule

P2 has **no arbitrary hyperparameter search** after this preregistration. The scale model, two calibration stages, finite-sample quantile rule, monotonic nesting rule, and `1.10 x q99` uncertainty budget are fixed here.

After fit, single-factor calibration, and transfer-calibration are generated, their resulting coefficients, conformal values, transfer multipliers, and budgets must be archived in a candidate-freeze document before seed `112112` is generated.

## Validation exposure policy

Once protected validation seed `112112` is generated/evaluated:

- it is permanently seen;
- no P2 scale basis, ridge lambda, multiplier coefficient, conformal rule, transfer rule, target set, monotonic nesting rule, uncertainty-budget rule, bridge behavior, or gate may change and then be re-evaluated on `112112` as unseen;
- any follow-up requires P3 with completely new validation evidence.

## Required artifacts

- `fit_frames.csv`
- `calibration_frames.csv`
- `transfer_frames.csv`
- `validation_frames.csv` only after candidate freeze
- `p2_calibration.json`
- `candidate_freeze.json`
- `validation_result.json`
- `validation_summary.md`
- `manifest.json`
- workflow/artifact receipt for protected validation

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
- P2 remains controlled synthetic reliability-layer evidence
- negative or mixed validation outcomes must be preserved
