# Phase 11 preregistration draft — domain-shift-aware perception reliability

## Status

**NEXT PHASE DESIGN — NO PHASE 11 EVIDENCE GENERATED YET**

Phase 11 is opened because the frozen Phase 10R holdout showed a specific failure: average ambiguous-view geometry improved while p95 tail error, target availability, and development-frozen uncertainty coverage degraded under combined appearance + geometry shift.

Phase 10R is closed for result-driven retuning. Phase 11 must be treated as a new research phase with new development evidence and a new freeze boundary.

## Research question

**Can AegisLand detect when visual conditions have moved outside its calibrated reliability envelope and abstain or widen uncertainty enough to recover target coverage without making useful perception unavailable?**

## Frozen starting point

Phase 11 inherits, but does not rewrite:

- Phase 10R candidate SHA `e1d566f8baa47bf10f9bdf39dd5988724208be80`;
- frozen Phase 10R holdout verdict: mixed / failed overall;
- Phase 10R 95% coverage under final shift: `84.3%` lateral / `79.7%` altitude;
- Phase 10R truth-visible miss rate: `20.0%`;
- Phase 10R ambiguous-view MAE improvement: `79.2%` lateral / `73.7%` altitude;
- Phase 10R ambiguous-view p95 improvement: `-1.1%` lateral / `7.3%` altitude.

The Phase 10R frozen holdout is permanently seen and may be used only as motivation/diagnostic evidence, not for Phase 11 model selection.

## Phase 11 development factors

New development data should cross factors that are visible to the reliability layer at inference time:

- target edge margin / partial visibility;
- projected target scale;
- obliquity / projective distortion;
- brightness and contrast;
- blur/noise strength;
- detector source and corner quality;
- temporal innovation / reacquisition state;
- recent track stability.

At least one development split must contain combinations absent from fitting trajectories so conditional reliability is tested compositionally rather than by random frame split.

## Candidate methods to compare

1. **Frozen Phase 10R uncertainty** — unchanged reference.
2. **Global conformal calibration** — one calibration envelope with target empirical coverage.
3. **Context-conditioned conformal calibration** — low-capacity conditioning on predeclared geometric/appearance reliability features.
4. **Shift-aware abstention** — abstain when the inference-visible reliability state is outside the calibrated support region.

No learned image-to-pose replacement is required for Phase 11 P0; the first question is whether reliability can become more honest under shift.

## Primary endpoints

### H1 — coverage transfer
On held-out domain-shift trajectories, target 95% intervals should achieve empirical coverage between **90% and 98%** on both lateral and altitude axes.

### H2 — useful sharpness
At matched coverage, median interval width should be no more than **1.35×** the frozen Phase 10R development-calibration width. A trivial always-wide interval is not considered a win.

### H3 — selective reliability
Among accepted observations, p95 absolute error should improve by **≥25%** versus accepting all frozen Phase 10R observations, while truth-visible usable availability remains **≥70%**.

### H4 — shift discrimination
A preregistered reliability score should rank known shifted conditions above nominal conditions with trajectory-level AUROC **≥0.80** on validation. This is diagnostic and does not by itself establish safety.

## Split policy

- separation unit: entire trajectory/sequence;
- no random adjacent-frame split;
- fitting trajectories, calibration trajectories, and validation trajectories are disjoint;
- the Phase 10R final holdout is excluded from Phase 11 fitting/calibration/validation;
- any future Phase 11 frozen holdout requires a separate exact-freeze approval checkpoint.

## Evidence and claim boundaries

- simulation only;
- `safety_acceptance = false`;
- `controller_tuning_allowed = false`;
- no physical-flight validation claim;
- coverage claims apply only to the defined simulated distributions;
- a failed or mixed Phase 11 result must be preserved rather than tuned away.
