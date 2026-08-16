# Phase 10R preregistration — perception generalization

> **APPROVAL STATUS: APPROVED AS WRITTEN**
>
> Explicit approval was recorded from the user's 2026-08-15 request to finish the preregistered Phase 10R edge/partial-view generalization experiment.
>
> The P0 development/validation approval has been completed. A second explicit approval for the exact frozen-holdout checkpoint was recorded on 2026-08-15 and is documented in Section 10.

## 1. Research question

**Can AegisLand improve legitimate target availability and ambiguous planar-pose handling while preserving the centimeter-scale geometry already achieved on clean ArUco observations and maintaining calibrated uncertainty under trajectory and appearance shift?**

Phase 10R is a revision prompted by the frozen Phase 10 result. It does not rewrite or replace Phase 10.

## 2. Evidence roles and leakage boundary

- `phase10_holdout_unseen` is now permanently historical/seen evidence for Phase 10R purposes.
- P0 may perform read-only descriptive forensics on that holdout.
- Existing Phase 10 holdout frames, misses, residuals, and derived descriptors **must not** be used to select thresholds, detector parameters, model structure, calibration parameters, or evaluation strata.
- Phase 10R model selection must use newly generated `phase10r_development` and trajectory-held-out `phase10r_validation` evidence only.
- A new `phase10r_frozen_holdout` may be exposed exactly once after architecture/config/calibration freeze.

## 3. Primary hypotheses

### H1 — detector availability
On preregistered difficult but truth-visible conditions, the selected front end reduces visible-frame miss rate by **≥40% relative** to the unchanged Phase 9 front end while:
- false-positive rate when truth-not-visible ≤ **1%**;
- detected-center p95 ≤ **1.10×** unchanged baseline;
- no selection based on the historical Phase 10 holdout.

### H2 — ambiguous planar pose
Explicit multi-hypothesis planar pose with causal temporal selection reduces error in the preregistered ambiguous/partial-view stratum:
- lateral/altitude MAE improvement ≥ **40%** versus unchanged Phase 9;
- p95 absolute error improvement ≥ **30%**;
- clean-ArUco MAE regression ≤ **10%**;
- visible metric availability drop ≤ **2 percentage points**.

### H3 — uncertainty calibration
A low-capacity inference-visible uncertainty model improves calibration without becoming uninformatively wide:
- mean absolute coverage error across 50/68/80/90/95% targets ≤ **5 percentage points** on validation;
- 95% empirical coverage between **90% and 98%** on both axes;
- median interval width ≤ **1.20×** the source-only Phase 10 baseline at matched coverage.

## 4. Development challenge set — frozen design before generation

Proposed `phase10r_challenge_dev_v1` factorial design:

- **5 trajectory families**
- **2 geometry/obliquity bands**
  - nominal: target normal roughly <20° from camera axis
  - difficult: roughly 35–60°
- **3 appearance conditions**
  - nominal
  - low exposure / reduced contrast
  - blur + image noise
- **2 predeclared top-level seeds**

Total: **60 sequences**.

Dataset acceptance is based on physical/rendering conditions and truth metadata, **not detector outcomes**.

Target size:
- ≥ **1,000 truth-visible frames** total;
- ≥ **100 truth-visible frames** in each major stress stratum.

Raw-frame hashes, trajectory IDs, camera configuration, resolved seed tree, and generation commit must be preserved.

## 5. Train/development/validation policy

- No random frame split.
- Entire trajectories/sequences are the unit of separation.
- Fitting/tuning uses development trajectories.
- Final model selection uses distinct validation trajectories.
- Statistical resampling and uncertainty summaries operate at trajectory/sequence level when possible to avoid pseudo-replication from adjacent frames.

## 6. Predeclared implementation order

This order is methodological, not a commitment that each stage must replace the previous one:

1. unchanged Phase 9 front end / Phase 10 estimator baselines;
2. detector corner-quality and causal reacquisition ablations;
3. explicit multi-hypothesis planar pose candidate interface;
4. robust causal temporal-filter benchmark;
5. low-capacity conditional uncertainty calibration;
6. optional learned residual correction only if deterministic approaches remain inadequate and the data volume justifies it.

Phase 10R must always retain unchanged baselines in paired evaluation.

## 7. Final frozen-holdout gate

After validation and explicit user approval of the exact freeze commit/configuration, run one new protected holdout with:
- ≥ **250 truth-visible frames**;
- ≥ **10 trajectories**;
- at least two appearance conditions;
- predeclared geometry/scale ranges;
- no manual frame inspection before automated evaluation and artifact preservation.

The frozen result is considered a strong Phase 10R success only if all applicable gates pass:

- clean-ArUco MAE ≤ **1.10×** Phase 9 baseline;
- ambiguous/partial-view MAE improvement ≥ **30%**;
- ambiguous/partial-view p95 improvement ≥ **25%**;
- truth-visible miss rate ≤ **10%**;
- false-positive rate when truth-not-visible ≤ **1%**;
- 95% uncertainty coverage between **90% and 98%** on both axes;
- all legacy Phase 10 metrics and negative findings remain reported.

A failed hypothesis is archived as a valid frozen result; the workflow must not hide or retune it away.

## 8. Safety and claim boundaries

- simulation only;
- no physical-flight validation claim;
- no certification claim;
- `safety_acceptance = false`;
- `controller_tuning_allowed = false`;
- detector/perception improvements do not independently establish end-to-end landing safety.

## 9. P0 approval checkpoint

Approval of this document authorized only:
1. implementation of the predeclared challenge-development generator;
2. generation of `phase10r_development` evidence;
3. development/validation ablations under the rules above.

The development + trajectory-held-out validation milestone is complete and frozen as a mixed result. Validation seed `271828` is permanently seen and may not be used for further tuning.

### P0 approval

- [x] **APPROVED AS WRITTEN** — recorded 2026-08-15
- [ ] **APPROVED WITH CHANGES**
- [ ] **NOT APPROVED**

## 10. Final frozen-holdout approval checkpoint

The user explicitly approved the next-step plan to execute the protected Phase 10R frozen holdout with the instruction **"do all that"** on 2026-08-15.

The exact frozen candidate/configuration approved for exposure is:

- candidate implementation SHA: `e1d566f8baa47bf10f9bdf39dd5988724208be80`;
- `MIN_VISIBLE = 0.66`;
- development-frozen uncertainty calibration SHA-256: `3ffdf1e37c94361ac01d8175f902a0ae4fb8d831274bb7850c171e92d79c527b`;
- validation seed `271828` is seen evidence and is not used for post-validation tuning;
- frozen-holdout protocol: `docs/phase10r_frozen_holdout_protocol.md`;
- protected holdout top-level seed: `1618033`;
- one-time automated evaluation only; no manual frame inspection before result preservation.

### Frozen-holdout approval

- [x] **APPROVED FOR ONE-TIME FROZEN HOLDOUT EXPOSURE** — recorded 2026-08-15
- [ ] **APPROVED WITH CHANGES**
- [ ] **NOT APPROVED**

After this holdout runs, its outcome is permanently seen evidence. No result-driven retuning may be presented as part of the same frozen Phase 10R result.
