# Phase 6F perception replication protocol

## Scope

Phase 6F is a **perception-only, simulation-only** refinement. No landing controller, supervisor, or final held-out seed is used in this replication.

Phase 6E remains preserved as development evidence. Phase 6F changes only the rule that decides when the segmentation threshold should use p30 rather than the historical image median as its background statistic.

## Phase 6F rule fixed before replication

For each image, compute p30, median, and p90.

- use p30 as background only when `median > (p30 + p90) / 2`;
- otherwise use the historical median background;
- keep the same threshold formula, connected-component selection, geometry inversion, raw-confidence calculation, sharpness feature, component-confidence model class, 0.80 component selection threshold, and altitude observability cap.

The midpoint test has no fitted scalar threshold. It was introduced after the Phase 6E development residual showed that `median > 0.5*p90` could switch unnecessarily in a dark high-altitude frame.

## Development replication seeds

The following top-level static-image seeds were searched in the repository before this protocol was committed and returned no matches:

- `707431`
- `717431`
- `727431`

They become **seen development replication seeds** as soon as the replication workflow is executed.

Final replacement held-out seeds remain untouched:

- landing: `918271`
- selective perception: `928271`

## Frame matrix

For each replication seed:

- conditions: clean, blur, low light, occlusion, mixed;
- altitudes (m): `0.08, 0.12, 0.18, 0.25, 0.40, 0.60, 0.80, 1.20, 2, 3, 4, 5, 6, 7, 8`;
- 40 frames per condition/altitude cell;
- x offset sampled uniformly from `[-1.5, 1.5]`;
- identical rendered frame is evaluated by Phase 6E and Phase 6F;
- calibration seed remains `616161` and is independent of replication-frame seeds.

This yields 1,800 frames per condition across the three replication seeds, or 9,000 unique rendered frames total.

## Fixed definitions

- lateral-good target: `|x_hat - x| <= 0.30 m`;
- altitude-good target: `|z_hat - z| <= 0.85 m`;
- selected component: calibrated probability `>= 0.80`;
- near-ground audit: true altitude `<= 0.25 m`;
- high-altitude audit: true altitude `>= 6.0 m`;
- catastrophic altitude error: absolute altitude error `> 2.0 m`.

## Replication acceptance criteria

Phase 6F may proceed to landing-development integration only if **all** of the following pass on the pooled three-seed replication:

1. **Probability semantics:** for every condition and for each component (x and z), among frames selected at probability >=0.80, the 95% Wilson upper confidence bound on the bad-frame rate is <=0.20. This directly tests the operational meaning of the 0.80 gate rather than requiring zero errors.
2. **Coverage preservation:** for every condition and component, Phase 6F selected-frame coverage may not be more than 5 percentage points lower than Phase 6E on the identical pooled frames.
3. **Near-ground altitude recovery:** Phase 6F raw altitude-good rate must be >=0.95 in every condition for true altitude <=0.25 m.
4. **No accepted catastrophic altitude error:** among Phase 6F altitude-selected frames, there must be zero frames with absolute altitude error >2.0 m.
5. **High-altitude degraded-image honesty:** for blur and mixed frames at true altitude >=6.0 m whose altitude estimate is bad, Phase 6F must reject at least 95% of those bad altitude estimates at the 0.80 gate.
6. **No final-seed leakage:** seeds `918271` and `928271` must not appear in any replication input or metadata.
7. **No post-replication retuning:** if any criterion fails, Phase 6F is preserved as a failed development revision. Any subsequent estimator or calibration change must receive a new revision label before another evaluation.

These criteria are committed before any Phase 6F replication seed is executed.
