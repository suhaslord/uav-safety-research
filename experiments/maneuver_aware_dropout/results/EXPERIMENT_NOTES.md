# Maneuver-aware uncertainty estimation experiment

## Hypothesis

Adaptive process noise that increases near detected maneuvers will produce
uncertainty estimates that better reflect actual estimation error during dropout
compared to the frozen constant-velocity baseline from PR #52.

## Method

### Frozen conditions (identical to PR #52)
- Same saved Webots baseline trajectory
- Same 2.0 s dropout timing sweep (6–23 s in 0.5 s increments)
- Same initial covariance and measurement noise assumptions
- Same evaluation metrics

### Single modification
- **Adaptive process noise:** Detect maneuvers from velocity acceleration
  - Acceleration threshold: 0.15 m/s²
  - Process noise boost factor: 5.0× near maneuvers
  - Exponential decay: 2.0 s time constant

### Comparison filters
1. **Baseline CV:** Frozen constant-velocity model with constant process noise (PR #52)
2. **Adaptive Q:** Same CV model with adaptive process noise near maneuvers

## Results

### Correlation between uncertainty and error

**Baseline CV:**
- Pearson correlation: -0.0253 (p=8.8522e-01)
- Spearman rank correlation: 0.1621 (p=3.5219e-01)

**Adaptive Q:**
- Pearson correlation: 0.9531 (p=1.0723e-18)
- Spearman rank correlation: 0.9728 (p=1.5217e-22)

**Improvement:** +0.9784 Pearson, +0.8107 Spearman

### Calibration: does uncertainty bound contain actual error?

**Baseline CV:**
- Fraction within 1σ: 0.724 (ideal: 0.68)
- Fraction within 2σ: 0.861 (ideal: 0.95)

**Adaptive Q:**
- Fraction within 1σ: 1.000 (ideal: 0.68)
- Fraction within 2σ: 1.000 (ideal: 0.95)

**Improvement:** calibration error reduction = -0.2761

## Interpretation

The adaptive process noise modification aims to address PR #52's identified weakness:
equal-duration dropouts produce similar covariance growth in the frozen CV filter
even though actual errors differ dramatically near maneuvers.

If correlation increases and calibration improves, the adaptive approach better
ranks dropout severity. If improvement is small or negative, the simple maneuver
detection heuristic may be insufficient, or the CV model's fundamental limitation
requires a different motion model (e.g., coordinated turn, IMM) rather than just
adaptive noise tuning.

## Limitations

- **Simulation only:** Webots trajectory, offline fault injection
- **Simple maneuver detection:** Acceleration threshold heuristic, not robust fault detection
- **Single trajectory:** Results specific to this commanded motion profile
- **Hyperparameters:** Boost factor and decay manually tuned, not optimized
- **No real-time test:** Implementation assumes offline batch processing

## Next steps if hypothesis supported

- Test on additional trajectories with different maneuver profiles
- Compare to coordinated-turn or IMM models
- Optimize adaptive parameters via cross-validation
- Add robust acceleration-based maneuver detector with false-positive control

## Next steps if hypothesis rejected

- The CV model's limitation may require switching to a better motion model
- Investigate IMM (interacting multiple models) or coordinated-turn filters
- Consider model-selection indicators beyond simple acceleration threshold
