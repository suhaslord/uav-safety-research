# Phase 10 development checkpoint — AegisT10

Status: **seen development evidence only; not the frozen holdout result**

Implementation branch: `phase10-temporal-metric-perception`

Protected Phase 9 evidence head: `33c5c73768757b508f5c613b2fba73f94e3fd5a6`

## Failure mode isolated

The audited Phase 9 seen trace contains 25 truth-visible observations:

- 18 ArUco measurements
- 7 quad-fallback measurements

On those same frames, the Phase 9 ArUco subset already has low metric error:

- lateral MAE: **0.0264 m**
- altitude MAE: **0.0231 m**

The quad-fallback subset is the dominant geometry failure:

- lateral MAE: **3.4951 m**
- altitude MAE: **5.3700 m**
- maximum lateral absolute error: **7.3439 m**
- maximum altitude absolute error: **10.2943 m**

This makes the Phase 10 design target concrete: preserve the strong ArUco geometry and prevent ambiguous fallback geometry from catastrophically overwriting a plausible causal track.

## Deterministic AegisT10 development result

AegisT10 uses a causal alpha-beta state estimator, explicit innovation gating, and prediction through rejected fallback observations. A predicted-through quad is never labelled as a fresh geometry update.

Paired on the already-inspected Phase 9 trace:

| Metric | Phase 9 | Simple causal smoothing | AegisT10 | Reduction vs Phase 9 |
|---|---:|---:|---:|---:|
| lateral MAE | 0.9976 m | 0.6736 m | **0.1362 m** | **86.3%** |
| altitude MAE | 1.5203 m | 1.5239 m | **0.0881 m** | **94.2%** |
| lateral p95 abs. error | 5.0874 m | 1.6868 m | **0.6500 m** | **87.2%** |
| altitude p95 abs. error | 6.5968 m | 4.1885 m | **0.1752 m** | **97.3%** |

Visible-frame metric availability is 25/25 on this development trace. The first clipped quad is retained as an explicitly untrusted bootstrap so availability is not silently improved by deleting a hard frame.

## Development uncertainty calibration

A small empirical source-aware calibrator is fitted only from the seen development residuals. On the same development evidence:

- median normalized lateral residual: **0.855**
- median normalized altitude residual: **0.724**
- lateral 2-sigma coverage: **100%**
- altitude 2-sigma coverage: **100%**

These values are development diagnostics, not evidence that the uncertainty model is calibrated on unseen data.

## What this does and does not establish

This checkpoint shows that the Phase 10 architecture attacks the measured Phase 9 failure mode and substantially outperforms both the unchanged Phase 9 estimator and trivial causal smoothing on already-seen evidence.

It does **not** establish the final Phase 10 claim. The architecture, configuration, and calibration must be frozen before a new Gazebo camera trajectory is generated and evaluated.

Simulation only. `safety_acceptance = false`. `controller_tuning_allowed = false`.
