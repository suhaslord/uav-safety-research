# Maneuver-aware uncertainty estimation under dropout

**Controlled follow-on experiment to PR #52**

## Research question

Can adaptive process noise that increases near detected maneuvers produce uncertainty estimates that better reflect actual estimation error during dropout?

## Background from PR #52

PR #52 established that identical 2.0 s dropouts produce dramatically different errors depending on timing:
- Steady motion (7–9 s): ~0.006 m max error
- Near direction change (10–12 s): ~0.526 m max error (~73× larger)

**Key weakness identified:** The constant-velocity filter's covariance grows identically for equal-duration dropouts regardless of when they occur. The uncertainty estimate knows measurements are missing but doesn't know the CV model is especially poor during commanded direction changes.

## Hypothesis

Adaptive process noise that temporarily increases near detected maneuvers will produce covariance that better correlates with actual error during dropout and provides better-calibrated uncertainty bounds.

## Controlled experimental design

### Frozen from PR #52 (no changes)
- Same saved Webots baseline trajectory (`webots_baseline.csv`)
- Same dropout timing sweep: 2.0 s dropouts from 6–23 s in 0.5 s steps
- Same initial covariance, measurement noise, evaluation metrics
- Same offline fault injection (never changes underlying flight)

### Single modification
- **Adaptive process noise:** Detect maneuvers from acceleration magnitude
  - When acceleration exceeds threshold → temporarily boost process noise by 5×
  - Exponential decay over ~2 s after maneuver
  - Goal: covariance should grow faster during/after maneuvers when CV model is poor

### Comparison
1. **Baseline CV filter** (frozen from PR #52): constant process noise
2. **Adaptive-Q filter** (this experiment): maneuver-triggered process noise boost

## Metrics

### Primary metrics
- **Pearson correlation** between predicted uncertainty (σ) and actual error during dropout
- **Spearman rank correlation** (does higher uncertainty correspond to higher error?)
- **Calibration:** fraction of dropout samples where actual error is within predicted 1σ and 2σ bounds
  - Ideal: 68% within 1σ, 95% within 2σ

### Secondary metrics
- Sigma-to-error ratio by dropout timing
- Stratified analysis: near maneuvers (<1 s) vs far from maneuvers (≥1 s)

## Preregistration

**Date:** 2026-08-22  
**Hypothesis:** Adaptive process noise will increase correlation by ≥0.10 and improve 1σ calibration toward 0.68 (from whatever baseline CV achieves)  
**Success criterion:** Statistically significant improvement in correlation OR calibration closer to ideal  
**Negative result handling:** If no improvement or worse, report honestly and discuss why simple adaptive noise is insufficient (may need full model switching like IMM)

## Running the experiment

```bash
# Using PR #52's saved Webots baseline
python experiments/maneuver_aware_dropout/analyze_adaptive_uncertainty.py \
  /tmp/pr52-artifacts/unm-crazyflie-webots-results/webots_baseline.csv \
  --out-dir experiments/maneuver_aware_dropout/results
```

## Outputs

- `baseline_dropout_timing.csv`: frozen CV filter results for each dropout window
- `adaptive_dropout_timing.csv`: adaptive-Q filter results for each dropout window
- `statistics.json`: correlation and calibration metrics, comparison
- `EXPERIMENT_NOTES.md`: generated scientific summary
- 4 plots:
  1. Trajectory with maneuver detection
  2. Baseline vs adaptive comparison (error, sigma, calibration ratio)
  3. Calibration analysis (scatter, coverage bars)
  4. Maneuver proximity stratification

## Interpretation boundary

This is a **simulation-only** controlled experiment. The Webots trajectory is genuine simulator output; faults are injected offline. Results characterize how two filter configurations behave on one trajectory under controlled dropout conditions. This is NOT a claim about real-world UAV safety.

## Relation to PR #52

- **PR #52:** Established reproducible baseline, identified maneuver-timing weakness
- **This experiment:** Controlled test of ONE modification to address that weakness
- **PR #52 status:** Remains draft, not merged; this experiment builds on its frozen artifacts
