# Phase 11 P5 preregistration — calibrated perception continuity

## Status

**PREREGISTERED BEFORE P5 DATA GENERATION**

Branch: `phase11-p5-perception-continuity`

P4 is preserved exactly as frozen. Its protected validation seed `198198` is permanently seen and may be used only for read-only motivation. P5 may not tune on P0 `33033`, duplicate `63333`, P1 `77077`, P2 transfer `101101`, P3 transfer `143143`, P4 transfer `187187`, or P4 validation `198198`.

## Research question

**Can AegisLand raise simulation-only perception availability above 90% under unseen compositional shift by causally bridging short perception gaps, while preserving the honest and efficient uncertainty behavior demonstrated by P4?**

P5 changes only the perception-continuity layer and the calibration needed to describe the resulting estimates. It does not change controller behavior.

## Motivation

P4 passed its uncertainty gates under protected unseen compositions:

- 95% coverage: `93.98%` lateral / `92.73%` altitude;
- calibration-curve MACE: `0.01972`;
- p95 interval-efficiency ratio: `1.177x` lateral / `1.030x` altitude;
- trajectory shift AUROC: `0.94271`.

P4 failed only the preregistered availability floor: the inherited estimator plus two-frame bridge produced an estimate on `83.13%` of truth-visible frames, below the required `90%`.

P5 therefore preserves the P4 uncertainty architecture and tests a bounded causal continuity extension rather than retuning P4 uncertainty on seen evidence.

## New P5 evidence boundary

All seeds and trajectory families are new.

- fit seed: `209209`
- single-factor calibration seed: `220220`
- compositional transfer-calibration seed: `231231`
- protected validation seed: `242242`
- frames per sequence: `60`

Families are disjoint:

- fit: `72..77`
- calibration: `78..80`
- transfer calibration: `81..83`
- protected validation: `84..86`

The full sequence is the split unit.

### Fit / calibration domains

1. `nominal`
2. `edge`
3. `small_scale`
4. `oblique`
5. `dim`
6. `blur_noise`
7. `temporal_dropout`
8. `low_contrast`

### Seen transfer-calibration compositions

1. `edge+temporal_dropout`
2. `small_scale+dim`
3. `oblique+blur_noise`
4. `dim+low_contrast`
5. `edge+small_scale+temporal_dropout`
6. `oblique+blur_noise+low_contrast`
7. `edge+dim+blur_noise`
8. `small_scale+oblique+low_contrast`

### Protected validation compositions

1. `edge+blur_noise`
2. `small_scale+temporal_dropout`
3. `oblique+dim`
4. `blur_noise+low_contrast+temporal_dropout`
5. `edge+small_scale+oblique`
6. `small_scale+dim+blur_noise`
7. `edge+oblique+low_contrast+temporal_dropout`
8. `edge+small_scale+oblique+dim+blur_noise`

Protected validation seed `242242` must not be generated before the P5 candidate-freeze checkpoint.

## Frozen underlying perception layer

P5 inherits the P1/P4 synthetic perception generator and the existing non-recursive two-frame bridge unchanged for horizons `1` and `2`.

The new P5 method may act only when that inherited layer still has no estimate.

## P5 causal continuity extension

### Anchor policy

Only genuine perception outputs (`candidate_available = true`) are allowed to become motion-history anchors.

- inherited bridge estimates are never inserted into anchor history;
- P5 continuity estimates are never inserted into anchor history;
- no future frame, truth state, domain label, or future reacquisition event may be used.

This prevents recursive drift from silently becoming self-confirming evidence.

### Fit-frozen velocity caps

Before applying P5 continuity to calibration, transfer, or validation, estimate per-axis absolute anchor-to-anchor slope caps from the P5 fit split only.

For each sequence, use slopes between consecutive genuine anchors:

`v = (estimate_t2 - estimate_t1) / (frame_t2 - frame_t1)`

Freeze the empirical `99th` percentile of absolute slope independently for lateral and altitude.

Any continuity slope is clipped to those fit-frozen caps.

### Robust local slope

At a missing frame, use up to the three most recent genuine anchors.

- with at least three anchors, compute the two most recent anchor-to-anchor slopes and use their component-wise median;
- with exactly two anchors, use their single slope;
- fewer than two genuine anchors cannot create a P5 extension.

### Bounded horizon and damping

P5 may extend only gaps with inherited bridge horizon greater than `2` and total gap horizon at most `5` frames.

Fixed damping factor: `0.85` per future step.

For gap horizon `h`, after slope clipping, displacement from the latest genuine anchor is:

`v * sum(0.85^k for k = 0 .. h-1)`

This is a causal damped constant-velocity continuation, not a controller command or flight-dynamics model.

### P5 source label

New estimates use source category:

`continuity_extension`

The continuity horizon and the clipped absolute local slopes are inference-visible reliability features.

## P5 uncertainty model

P5 preserves the P4 design principles:

- separate lateral / altitude log-error scale models;
- standardized low-capacity basis;
- robust target winsorization at fit-split `2nd` / `98th` percentiles;
- ridge regression with fixed lambda `4.0`;
- fit-split prediction guard using fitted-log-scale q01/q99 expanded by `0.35`;
- single-factor finite-sample conformal calibration;
- second compositional transfer-calibration stage;
- nested intervals by cumulative maximum across target levels;
- no hard reliability accept/reject threshold.

### P5 continuous basis

1. eight P1 causal risk components;
2. scalar risk score;
3. normalized coactivation count;
4. largest primary risk component;
5. second-largest primary risk component;
6. P5 continuity horizon (`0..5`);
7. absolute clipped lateral local slope;
8. absolute clipped altitude local slope.

### Source one-hots

- partial-edge;
- center-regeometry;
- known-ArUco-refined;
- inherited temporal bridge;
- P5 continuity extension.

## Conformal calibration

Targets: `{0.50, 0.68, 0.80, 0.90, 0.95}`.

Single-factor stage:

`normalized_residual = abs_error / max(predicted_scale, 1e-9)`

with finite-sample order statistic `ceil((n+1)*q)`.

Seen transfer stage:

`R_single(axis,q) = predicted_scale * Q_single(axis,q)`

`transfer_ratio = abs_error / max(R_single, 1e-9)`

and `T(axis,q)` is the finite-sample q conformal quantile of the transfer ratios.

Final radius:

`R_P5(axis,q) = predicted_scale * Q_single(axis,q) * T(axis,q)`

Intervals are monotonized by cumulative maximum across increasing q.

## Primary gates

### H1 — useful availability

On truth-visible protected-validation frames, P5 output availability must be `>= 0.92`.

This is intentionally stricter than P4's failed `0.90` floor because the continuity extension exists specifically to solve availability.

### H2 — 95% coverage transfer

Across **all P5 available outputs**, 95% empirical coverage must be within `[0.90, 0.98]` on both axes.

### H3 — calibration curve quality

Mean absolute coverage error across `{50%,68%,80%,90%,95%}` over both axes must be `<= 0.06`.

### H4 — interval efficiency

Across all P5 available outputs:

- median 95% half-width / all-available p95 absolute error `<= 1.25` on each axis;
- p95 95% half-width / all-available p95 absolute error `<= 2.25` on each axis.

All four conditions must pass.

### H5 — continuity-specific honesty

On `continuity_extension` rows only:

- 95% coverage must be in `[0.88, 0.99]` on both axes;
- p95 95% half-width / continuity-only p95 absolute error must be `<= 2.75` on both axes.

This prevents overall coverage from hiding a badly calibrated gap-filling subpopulation.

### H6 — shift discrimination

Trajectory-level mean inherited severity must distinguish single-factor calibration from compositional validation with AUROC `>= 0.85`.

H6 remains diagnostic only.

## Candidate-freeze checkpoint

After this preregistration, P5 may generate only fit, calibration, and seen transfer data.

Freeze and archive:

- velocity caps;
- scale-model standardizer;
- target winsor bounds;
- prediction guard bounds;
- ridge coefficients;
- conformal quantiles;
- transfer multipliers;
- seen transfer gate metrics;
- exact code commit and artifact hashes.

If seen transfer fails H1, H2, H3, H4, or H5, protected validation seed `242242` should not be exposed.

If all development gates pass, the frozen P5 candidate may proceed to protected validation without changing any method constant.

## Validation exposure policy

Once seed `242242` is generated/evaluated, it becomes permanently seen. No P5 horizon, damping, anchor rule, velocity cap rule, model basis, ridge lambda, calibration rule, or gate may change and then be re-evaluated on `242242` as unseen evidence.

Passing P5 protected validation still does **not** authorize a final Phase 11 frozen holdout. Any final holdout requires a separate explicit user approval at an exact candidate-freeze checkpoint.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
- negative and mixed outcomes remain permanent evidence
