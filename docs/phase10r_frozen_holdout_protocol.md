# Phase 10R frozen-holdout protocol

## Status

**APPROVED FOR ONE-TIME EXECUTION — 2026-08-15**

The user explicitly approved the Phase 10R frozen-holdout checkpoint with the instruction to "do all that" after the exact next-step plan was presented. This approval authorizes one automated exposure of the holdout described below. It does not authorize post-holdout retuning.

## Frozen candidate

- candidate implementation SHA: `e1d566f8baa47bf10f9bdf39dd5988724208be80`
- candidate partial-view threshold: `MIN_VISIBLE = 0.66`
- historical Phase 10 holdout used for candidate selection: **false**
- Phase 10R validation seed `271828`: permanently seen; **must not** be used for further tuning
- development-frozen candidate uncertainty calibration SHA-256: `3ffdf1e37c94361ac01d8175f902a0ae4fb8d831274bb7850c171e92d79c527b`

The evaluation workflow reconstructs the candidate and unchanged Phase 9 detector source directly from the frozen candidate commit with `git show`. The current branch may add evaluation plumbing and reporting, but it may not modify the frozen candidate implementation.

## Protected holdout design

Evidence role: `phase10r_frozen_holdout`.

Top-level generation seed: `1618033`.

The holdout is generated only after this protocol and the exact evaluator are committed. No raw holdout frame may be manually inspected before automated evaluation and artifact preservation.

### Geometry

The holdout uses **12 previously unexposed trajectory IDs**. These are not the five development/validation trajectory equations.

Across the 12 trajectories:

- lateral image sweep reaches approximately `q ∈ [-1.06, +1.06]` relative to the image half-width, intentionally creating legitimate edge and partial-view intervals;
- truth altitude/depth is bounded to **1.60–3.25 m**;
- 4 trajectory IDs use nominal planar geometry;
- 8 trajectory IDs use difficult projective geometry with top/bottom half-width ratios and skew outside the nominal square case;
- target vertical position also varies causally with trajectory ID;
- dataset acceptance is based on generator truth, not detector output.

### Appearance

Each geometry trajectory is rendered under all three predeclared conditions:

1. `nominal`;
2. `dim_contrast` — lower exposure/contrast plus additive image noise;
3. `blur_noise` — Gaussian blur plus stronger additive image noise.

This creates **36 independent sequence IDs** (`12 trajectories × 3 appearances`).

Each sequence contains 48 frames. The target is truth-present for frames 4–43 inclusive, yielding **1,440 truth-visible frames** before any detector outcome is known. Truth-not-visible prefix/suffix frames are retained for false-positive evaluation.

Raw grayscale frame bytes and SHA-256 hashes are preserved in the workflow artifact.

## Paired systems

Every frame is evaluated with:

1. the unchanged Phase 9 detector source reconstructed from the frozen candidate SHA;
2. the exact frozen Phase 10R candidate reconstructed from the same SHA.

The frozen uncertainty calibration is read from the archived development calibration and verified by SHA-256 before evaluation.

## Preregistered final gates

A strong Phase 10R frozen-holdout success requires **all** of the following:

- clean-ArUco lateral MAE ≤ `1.10×` unchanged Phase 9 baseline;
- clean-ArUco altitude MAE ≤ `1.10×` unchanged Phase 9 baseline;
- ambiguous/partial lateral MAE improvement ≥ `30%`;
- ambiguous/partial altitude MAE improvement ≥ `30%`;
- ambiguous/partial lateral p95 improvement ≥ `25%`;
- ambiguous/partial altitude p95 improvement ≥ `25%`;
- overall truth-visible candidate miss rate ≤ `10%`;
- candidate false-positive rate when truth-not-visible ≤ `1%`;
- 95% lateral uncertainty coverage between `90%` and `98%`;
- 95% altitude uncertainty coverage between `90%` and `98%`.

A failed or mixed result is still frozen and published. No gate may be changed after exposure.

## One-time execution rule

The workflow is push-triggered only on the protected holdout branch and has no `workflow_dispatch` entrypoint. It runs when the frozen evaluator/workflow is first committed. Later result/README/dashboard commits do not match its trigger paths and therefore do not re-expose the holdout.

## Claim boundaries

- simulation only;
- `safety_acceptance = false`;
- `controller_tuning_allowed = false`;
- no physical-aircraft or flight validation;
- no certification claim;
- perception results do not independently establish end-to-end autonomous landing safety.
