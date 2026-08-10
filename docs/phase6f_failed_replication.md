# Phase 6F failed perception replication

## Decision

Phase 6F is **rejected as a development revision** and will not be connected to the landing loop.

The failure is preserved rather than weakening the preregistered criteria or retuning the background switch after seeing the replication outcome.

## What Phase 6F changed

Phase 6F refined the Phase 6E robust-background switch from:

`median > 0.5 * p90`

to the distribution-relative midpoint rule:

`median > (p30 + p90) / 2`

The intent was to prevent unnecessary p30 switching in dark, low-dynamic-range high-altitude frames while retaining the near-ground foreground-dominance correction.

## Preregistered replication

Protocol: `docs/phase6f_perception_replication.md`

Replication seeds, searched before execution and now permanently seen development seeds:

- `707431`
- `717431`
- `727431`

The experiment used 40 static frames per condition/altitude cell across 15 altitudes and five degradation conditions, for 9,000 unique rendered frames. Phase 6E and Phase 6F evaluated identical frames. No landing controller, supervisor, or final held-out seed was used.

The full unit suite passed 76 tests before the replication matrix.

## Outcome

Phase 6F failed the preregistered gate.

Key pooled condition metrics:

| condition | Phase 6E z-good | Phase 6F z-good | Phase 6E z coverage | Phase 6F z coverage |
|---|---:|---:|---:|---:|
| clean | 1.0000 | 1.0000 | 0.8667 | 0.8667 |
| blur | 0.6667 | 0.6667 | 0.6000 | 0.6000 |
| low light | 0.8528 | 0.7828 | 0.6550 | 0.5867 |
| mixed | 0.6267 | 0.6022 | 0.5428 | 0.5594 |
| occlusion | 0.9983 | 0.9994 | 0.8667 | 0.8667 |

Phase 6F still satisfied the 0.80 probability-semantics criterion: the 95% Wilson upper bad-frame rate stayed below 20% for every selected x/z component and condition. However, that was not sufficient to pass the full protocol.

### Failed criteria

1. **Low-light altitude coverage preservation failed.** Phase 6F altitude coverage was 0.5867 versus 0.6550 for Phase 6E, a 6.83 percentage-point loss, exceeding the preregistered 5-point limit.
2. **Near-ground low-light accuracy failed.** Phase 6F altitude-good rate for true altitude <=0.25 m was 0.6896, below the required 0.95.
3. **Near-ground mixed accuracy failed.** Phase 6F altitude-good rate for true altitude <=0.25 m was 0.9083, below 0.95.
4. **Accepted catastrophic-error criterion failed.** Phase 6F produced 7 altitude-selected frames with absolute altitude error >2.0 m; the preregistered limit was zero.

The high-altitude degraded-image honesty checks still passed: blur and mixed bad altitude estimates at >=6 m were rejected at 100% recall.

## Interpretation

The midpoint rule fixed the isolated Phase 6E dark high-altitude residual used to motivate the revision, but it generalized poorly to low-light and mixed near-ground imagery. This is a classic example of why a one-frame diagnostic must not be treated as sufficient evidence for a global estimator rule.

Phase 6F is therefore preserved as a negative ablation. The project returns to Phase 6E as the stronger perception candidate rather than tuning Phase 6F against the failed replication table.

## Next step

Run a dedicated Phase 6E perception confirmation on new development-only seed families with acceptance criteria locked before execution. If Phase 6E confirms, connect the frozen Phase 6E estimator to the existing temporal tracker and the simpler Phase 6C component-fusion policy for landing development.

Final replacement held-out seeds remain untouched:

- landing: `918271`
- selective perception: `928271`
