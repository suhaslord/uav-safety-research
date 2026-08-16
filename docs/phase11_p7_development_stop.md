# Phase 11 P7 development stop — robust-anchor continuity

## Status

**DEVELOPMENT STOP — NO CANDIDATE FREEZE / PROTECTED VALIDATION NOT EXPOSED**

P7 preregistration: `docs/phase11_p7_robust_anchor_preregistration.md`

Failed freeze/invariant workflow:

- run: `31973592964`
- workflow head: `893009cc3294311a9f9dbea5a3f588b404824777`
- job: `95229663237`
- conclusion: failed during invariant tests, before the dedicated artifact-generation step

## Exposure ledger

The invariant tests invoked the P7 `freeze()` path before failing. That function generated all four development splits before candidate construction stopped.

Therefore the following P7 seeds are permanently **seen** even though no candidate artifact was emitted:

- fit: `297297`
- single-factor calibration: `308308`
- continuity adaptation: `319319`
- compositional transfer: `330330`

They may motivate later revisions but may never be reused as hidden/frozen evidence.

Protected validation seed `341341` was guarded by the test harness and **was not generated or exposed**. It is retired with P7 rather than recycled into a later revision.

## Preregistered development failure

P7 required at least `80` truth-visible available `robust_continuity` rows on the disjoint adaptation split before fitting the continuity correction model.

Observed adaptation continuity rows: **`38`**.

The candidate builder correctly stopped with:

`P7 adaptation continuity rows 38 < 80`

Because this preregistered minimum failed, P7 is not eligible for candidate freezing or protected validation.

## Method counterexample found before candidate freeze

A pure invariant test also exposed a conceptual weakness in the proposed three-anchor robust trend.

For anchors:

- `(t=0, y=0)`
- `(t=1, y=1)`
- `(t=2, y=10)`

the preregistered median-all-pairwise slope plus median-anchor-intercept construction returns a trend value of `10` at the newest-anchor time. In other words, with only three anchors, that Theil–Sen-style construction can still pass exactly through a badly inconsistent newest anchor.

This is not merely a test bug; it defeats the main P7 motivation of preventing a bad newest anchor from becoming the continuity state.

No P7 threshold or method constant was altered after observing this counterexample.

## Interpretation

P7 failed usefully before spending protected validation evidence:

1. the planned disjoint continuity-adaptation population was too small for the preregistered correction model;
2. the proposed three-anchor median-pairwise robust line is not sufficiently robust to the exact newest-anchor failure mode that motivated P7;
3. protected validation remained untouched, so no additional hidden evidence was wasted.

## Next revision

P8 should use completely fresh seeds and make the continuity state explicitly innovation-bounded rather than relying on three-point robust regression.

A principled P8 design is:

- use the two genuine anchors before the newest genuine anchor to predict the newest anchor;
- compute the newest-anchor innovation causally;
- clip that innovation to a **fit-frozen** per-axis innovation cap before constructing the continuity intercept/state;
- blend the prior-anchor slope with the slope implied by the clipped newest state using a fixed preregistered rule;
- retain genuine-anchor-only history and non-recursive continuity;
- retain a bounded horizon of at most seven frames;
- expose innovation magnitude, innovation-cap utilization, slope-cap utilization, and horizon to uncertainty calibration;
- enlarge the fresh adaptation and transfer trajectory-family counts enough to satisfy preregistered continuity sample-size requirements without lowering those requirements after exposure.

P8 must preregister before any P8 generation.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
