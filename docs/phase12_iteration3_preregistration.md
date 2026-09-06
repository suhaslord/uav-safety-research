# Phase 12 iteration 3 preregistration — innovation-residual normalized conformal

## Status

**PREREGISTERED BEFORE ITERATION-3 DEVELOPMENT EVALUATION AND BEFORE ANY PHASE 12 TRANSFER / PROTECTED / FINAL EVIDENCE IS EXPOSED.**

This document defines a distinct Phase 12 development iteration. It does not modify or erase iterations 1 or 2.

The scientific motivation is the permanently-seen forensic analysis in `docs/phase12_width_tail_forensics.md`. That analysis used only Phase 12 scale-fit, calibration A, calibration B, and debugging-only development evidence.

## Hypothesis

Iteration 2 allocates lateral continuity width too strongly according to severity / horizon and too weakly according to the estimator state that actually predicts large lateral error.

The specific hypothesis is:

> A single continuity-only, inference-visible residual reliability coordinate based on normalized lateral anchor innovation can reduce heteroscedasticity left after the iteration-2 severity scale, allowing conformal calibration to move width away from easy long-horizon continuity rows and toward genuinely unstable anchor states without changing the point estimator or sacrificing coverage/honesty.

## Frozen scope of scientific change

Iteration 3 changes **only lateral uncertainty scaling for primary continuity rows**.

Unchanged from iteration 2:

- P14R point estimates
- P9 bounded soft-update continuity behavior
- continuity availability decisions
- independent coarse rescue generation and selection
- velocity caps
- fitted P9 innovation scales
- output-group assignment (`base_output`, `continuity_h3`, `continuity_h45`, `continuity_h67`, `independent_coarse_rescue`)
- iteration-2 clipped-linear severity scale and its `0.5` continuity contrast shrinkage
- all altitude uncertainty behavior
- all base-output uncertainty behavior
- all rescue uncertainty behavior
- Phase 12 scale-fit/calibration families and domains
- finite-sample conformal order statistic
- targets `{0.50, 0.68, 0.80, 0.90, 0.95}`
- interval nesting by cumulative maximum
- separate calibration A and calibration B normalized residuals
- pointwise maximum of calibration A/B radii
- high-severity thresholds
- H1-H11 calculations and all locked thresholds
- evidence roles and progression rules

No gate is relaxed.

## Allowed inference feature

For lateral continuity rows only, define

`r = p9_anchor_innovation_lateral_abs / frozen_lateral_innovation_scale`

where:

- `p9_anchor_innovation_lateral_abs` is produced by the unchanged P9 estimator from recent genuine anchors before truth error is calculated;
- `frozen_lateral_innovation_scale` is the already-frozen P9 fit-derived innovation scale inherited from the closed Phase 11 predecessor candidate.

Then define a robust monotone coordinate:

`u = log1p(max(r, 0))`.

No truth quantity enters `r` or `u` at inference.

The feature is allowed only when the row belongs to one of the three primary continuity groups. Base and rescue rows ignore it.

## Forbidden features

The iteration-3 uncertainty model may not use:

- true lateral position
- true altitude
- lateral or altitude truth error
- any future observation
- protected/final labels or outcomes
- whether the current prediction happened to be accurate
- transfer/protected/final domain outcomes
- Phase 11 protected (`858858`) outcomes
- retired Phase 11 P15-v2 (`869869`) outcomes

Truth-derived lateral error is allowed only on the **Phase 12 scale-fit role** to fit the residual reliability scale, and on calibration/evaluation roles to calculate conformal scores/metrics. It is never an inference input.

## Exact iteration-3 scale formula

Let `b_i` be the exact iteration-2 lateral scale for row `i`, including the frozen `0.5` continuity contrast rule.

For each primary continuity group independently, on Phase 12 scale-fit evidence only:

1. Compute `u_i = log1p(max(anchor_innovation_lateral_abs_i / frozen_lateral_innovation_scale, 0))`.
2. Compute residual magnitude `z_i = lateral_abs_error_i / b_i`.
3. Freeze `u10` and `u90` as the 10th and 90th percentiles of finite `u_i` in that group.
4. Freeze `u33` and `u67` as the 1/3 and 2/3 quantiles of finite `u_i`.
5. Freeze `low = median(z_i | u_i <= u33)`.
6. Freeze `high_raw = median(z_i | u_i >= u67)`.
7. Set `high = max(high_raw, low)` so the reliability factor cannot decrease as innovation rises.
8. Require positive finite anchors and at least 10 rows in each fitting tail. If those conditions fail, iteration 3 fails construction rather than silently falling back.
9. Define

   `t_i = clip((u_i - u10) / (u90 - u10), 0, 1)`

   `raw_factor_i = low + t_i * (high - low)`

10. Normalize only for interpretability with the geometric center

   `center = sqrt(low * high)`

   `reliability_factor_i = raw_factor_i / center`.

11. The iteration-3 lateral scale is

   `scale_v3_i = b_i * reliability_factor_i`.

The geometric-center normalization contains no tunable coefficient and does not change the fitted contrast. Any uniform factor would cancel under normalized conformal calibration; the scientific content is the scale *ratio* allocated across innovation states.

For base, rescue, and every altitude row:

`scale_v3_i = scale_v2_i` exactly.

## Parameter rule

There is **no development-selected coefficient** and no parameter sweep.

All iteration-3 parameters (`u10`, `u90`, `low`, `high`) are deterministic robust summaries of Phase 12 scale-fit evidence only. The development split `907907` is not used to fit, select, or tune these values.

The `log1p` transform is frozen analytically to reduce leverage from very large innovation ratios while preserving order and monotonicity. It is not selected by comparing development H4 outcomes.

## Calibration rule

After fitting the frozen iteration-3 scale:

1. Generate the already-frozen Phase 12 calibration A and calibration B environments.
2. For each output group, axis, and target `q`, compute `score = absolute_error / scale_v3`.
3. Apply the existing finite-sample `ceil((n+1)q)` conformal order statistic.
4. Apply cumulative maxima across increasing targets for nested intervals.
5. Take the pointwise maximum of calibration A and calibration B normalized radii.
6. At evaluation, return `half_width = scale_v3 * frozen_robust_normalized_radius`.

The A/B maximum remains unchanged because permanently-seen diagnostics showed only approximately `1.0%–6.7%` disagreement at lateral 95%; there is no scientific basis to weaken this robustness rule in iteration 3.

## Grouping and power

No group boundary changes.

Scale-fit/calibration minimums remain:

- base `>=900`
- H3 `>=180`
- H4-5 `>=135`
- H6-7 `>=90`
- rescue `>=180`

Development/transfer/protected minimums remain:

- base `>=360`
- H3 `>=60`
- H4-5 `>=45`
- H6-7 `>=30`
- rescue `>=60`

Final minimums remain those already frozen by Phase 12 / P14R.

## Locked primary gates

Iteration 3 is a viable development freeze candidate only if the existing primary gate set passes together:

- H1 useful availability
- H2 overall lateral and altitude 95% coverage
- H3 calibration MACE
- H4 overall lateral/altitude median and p95 efficiency
- H5 primary-continuity honesty
- H6 base-output honesty
- H8 high-severity honesty
- H9 rescue honesty
- H10 rescue accuracy
- H11 rescue effectiveness
- group minimums

H7 remains diagnostic exactly as before.

No H4 improvement is accepted if another required gate fails.

## Evidence ledger before iteration-3 development

Permanently seen and allowed for this development lineage:

- scale fit `880880`
- calibration A `891891`
- calibration B `902902`
- development-only `907907`

Still forbidden/unexposed for iteration-3 construction and development:

- Phase 11 protected `858858`
- retired Phase 11 P15-v2 `869869`
- Phase 12 transfer `913913`
- Phase 12 protected validation `924924`
- Phase 12 final holdout `935935`

## Development reuse policy

Seed `907907` was permanently designated debugging/development-only before its first exposure. It may be rerun once this preregistered iteration-3 implementation and tests are in place.

It may never become transfer, protected, or final evidence.

The development result answers only whether this architecture behaves sensibly enough to freeze. It is not a hidden leaderboard and cannot be used to tune the factor formula or select a coefficient.

## Progression rule

If all required gates and group minimums pass on iteration-3 development and software/invariant QA passes, the candidate may be frozen with an exact candidate SHA-256 and scientific Git SHA. Only then may a dedicated transfer workflow be created and seed `913913` exposed once for that exact frozen candidate.

Protected `924924` remains unauthorized unless transfer passes every required primary gate. Final `935935` remains unauthorized unless protected validation passes every required primary gate.

## Stop rule

If iteration 3 fails any required primary gate:

1. record the result permanently;
2. classify the failure;
3. do not expose transfer;
4. do not tune a coefficient or formula against `907907` merely to cross the H4 boundary.

A further iteration is permitted only if the failure reveals a qualitatively new, inference-visible scientific mechanism that supports a separately preregistered low-capacity architecture. Repeated threshold chasing is not permitted.

## Claim boundary

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`

Iteration 3 is simulation research on uncertainty allocation. It does not establish physical-flight safety, certification relevance, controller improvement, production readiness, or operational reliability.
