# Phase 6E perception freeze

## Decision

Phase 6E is **frozen as the perception candidate** for the next landing-development revision.

This freeze applies only to the synthetic-image perception estimator and its component-confidence calibration. It is not a final landing result and does not use either replacement held-out seed.

Frozen implementation:

- `src/uav_safety/phase6e_perception.py`
- robust-background rule: use p30 when `median > 0.5 * p90`, otherwise use the historical median;
- same Phase 6 threshold equation, largest-component estimator, geometry inversion, raw-confidence formula, and sharpness statistic;
- Phase 6E component calibrator trained over altitude bands `0.08–0.50`, `0.50–2`, `2–4`, `4–6`, `6–8 m`;
- x-good tolerance: `0.30 m`;
- z-good tolerance: `0.85 m`;
- component selection threshold: `0.80`;
- historical altitude observability cap unchanged.

Any later change to these perception rules or constants must receive a new revision label.

## Evidence before freeze

### First Phase 6E validation

Development seed `697431`, static images only.

Phase 6E removed the historical catastrophic near-ground clean/occlusion alias class and substantially improved altitude accuracy while preserving the high-altitude blur limitation as low confidence rather than hiding it.

One selected-bad occlusion altitude frame remained in that first validation: true z `6.0 m`, estimated z about `5.004 m`, error about `0.996 m`. A targeted diagnostic showed that this was a borderline high-altitude scale error rather than the former near-ground multi-meter alias.

### Phase 6F negative ablation

Phase 6F attempted a different distribution-relative background switch. It was rejected after a preregistered three-seed replication because it lost low-light altitude coverage, degraded near-ground low-light/mixed accuracy, and produced seven accepted catastrophic altitude errors. Phase 6E therefore remained the stronger estimator rather than being retuned to the Phase 6F result.

### Dedicated Phase 6E confirmation

Protocol: `docs/phase6e_perception_confirmation.md`

Confirmation seeds, now permanently seen development seeds:

- `737431`
- `747432`
- `757432`

Total: 9,000 unique static synthetic frames. Full unit suite before confirmation: **76 passed**.

Pooled condition results:

| condition | x-good | z-good | x coverage | z coverage | selected-x bad rate | selected-z bad rate |
|---|---:|---:|---:|---:|---:|---:|
| blur | 0.9928 | 0.6667 | 0.7222 | 0.6000 | 0.0000 | 0.0000 |
| clean | 0.9189 | 1.0000 | 0.6667 | 0.8667 | 0.0000 | 0.0000 |
| low light | 0.9072 | 0.8506 | 0.6744 | 0.6594 | 0.0000 | 0.0042 |
| mixed | 0.6589 | 0.6222 | 0.5400 | 0.5417 | 0.0833 | 0.0021 |
| occlusion | 0.6817 | 0.9983 | 0.5339 | 0.8667 | 0.0676 | 0.0000 |

All preregistered confirmation criteria passed:

1. For every condition/component, the 95% Wilson upper bad-frame rate among p>=0.80 selected frames was <=0.20.
2. x and z selected-frame coverage were >=0.50 in every condition.
3. Near-ground (`z<=0.25 m`) altitude-good rate was:
   - blur: `1.0000`
   - clean: `1.0000`
   - low light: `0.9625`
   - mixed: `0.9958`
   - occlusion: `1.0000`
4. Accepted catastrophic (`|z error|>2 m`) altitude errors: `0`.
5. Bad high-altitude (`z>=6 m`) blur and mixed altitude estimates were rejected at `1.0000` recall.
6. The worst per-seed/condition 95% Wilson upper selected-risk bound was `0.1341` for x and `0.0221` for z, both below `0.20`.

GitHub Actions confirmation run: `31359809652`.
Artifact: `phase6e-perception-confirmation` (`9051958629`).

## What is and is not frozen

Frozen:

- Phase 6E image estimator behavior;
- Phase 6E component-confidence calibration procedure;
- 0.80 x/z component gate;
- perception tolerances and altitude-observability cap.

Not frozen:

- how the frozen perception is integrated with the temporal landing loop;
- landing-level fusion/supervision architecture;
- landing outcome claims.

## Next landing revision

The next landing-development architecture is labeled **Phase 6G**.

Its intended isolation is:

- inject the frozen Phase 6E estimator into the existing Phase 6 temporal tracker;
- use the frozen Phase 6E component-confidence model;
- retain the Phase 6 robust image-derived velocity filter;
- retain the independent reference estimator;
- use the Phase 6C component-fusion behavior: low-confidence lateral components may fall back to reference x/vx, while low-confidence altitude falls back in z only and preserves the established visual/temporal vz;
- do **not** use the Phase 6D 3-sigma hard-alias rule;
- keep the controller and frozen V3 supervisor unchanged.

Final replacement held-out seeds remain untouched:

- landing: `918271`
- selective perception: `928271`
