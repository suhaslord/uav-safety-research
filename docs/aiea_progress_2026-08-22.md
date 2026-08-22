# AIEA K-12 Research Progress Update — August 22, 2026

**Student:** Suhas Beemineni  
**Project:** AegisLand  
**Program:** UCSC AIEA Lab K-12 Research Foundations  
**Track:** Independent research  
**Evidence scope:** Simulation only

## What changed this week

AegisLand now has a new Webots/Crazyflie resilience baseline focused on a specific estimator weakness: **the same measurement dropout can be harmless during steady motion but much more damaging when it overlaps a maneuver**.

The experiment uses a genuine Webots Crazyflie trajectory and holds the flight and estimator configuration fixed while applying controlled measurement degradations offline to the same saved trajectory. This isolates the effect of measurement noise, fixed bias, and dropout timing instead of mixing those effects with changes in the underlying flight.

## Reproducible setup

- Official Bitcraze Crazyflie Webots simulation pinned to a fixed source revision.
- Stock Crazyflie Webots plant and Bitcraze Python velocity/fixed-height controller.
- 1,000 Webots samples over 31.968 seconds.
- One fixed 2D constant-velocity Kalman filter for every fault case.
- Faults applied to the same saved Webots position trace so the underlying flight does not change between cases.
- CI reproduces the Webots run, fault matrix, extended diagnostics, provenance, plots, and artifact generation.

## Main result

The nominal estimator RMSE is **0.0061 m** with a maximum nominal position error of **0.0230 m**.

For a fixed **2.0 second position dropout**, timing changed the outcome dramatically:

| Dropout window | Motion context | Maximum position error |
|---|---|---:|
| 7–9 s | steady segment | 0.0041 m |
| 12–14 s | steady segment | 0.0071 m |
| 9.5–11.5 s | spans direction change | 0.3590 m |
| 10–12 s | starts at direction change | 0.5260 m |
| 15–17 s | starts at direction change | 0.5369 m |
| 20–22 s | starts at direction change | 0.5372 m |

Representative maneuver-adjacent windows averaged **0.4461 m** maximum error versus **0.0061 m** for representative steady windows, about **73.5× larger**.

## Interpretation

The constant-velocity predictor behaves well when the vehicle is moving steadily. Around a commanded direction change, the stored velocity can become stale or still be adapting. If position measurements disappear at that moment, prediction-only propagation can diverge much faster.

This suggests that **dropout duration alone is not a sufficient difficulty measure**. The motion context at dropout onset matters.

## Uncertainty finding

The current covariance grows when measurements are missing, but equal-duration dropouts can produce very similar covariance growth even when the true position error is dramatically different around maneuvers.

That means the current uncertainty model captures the fact that measurements are absent, but does **not fully capture maneuver-induced model mismatch**. This is the most important open technical question from the experiment.

## Current status

The experiment is preserved in draft PR **#52 — `research: reproduce UNM Crazyflie Webots resilience baseline`**. The workflow is green through genuine Webots execution, the frozen fault matrix, extended diagnostics/plots, provenance generation, and artifact upload.

The PR remains a draft so the result can be reviewed before making any broader research claim.

## Next research step

1. Freeze this Webots baseline and its evidence bundle.
2. Treat motion context as an explicit experimental variable rather than only dropout duration.
3. Test whether maneuver-aware process uncertainty or a stronger motion model better reflects error growth during measurement loss.
4. Run the next challenge set under preregistered conditions before looking at its outcomes.
5. Preserve negative results and calibration failures instead of tuning them away after evaluation.

## Evidence boundary

These results are **simulation-only**. They do not establish physical-flight safety, controller safety, or real-world reliability. The contribution is a reproducible simulator result showing that estimator resilience to missing measurements depends strongly on *when* the dropout occurs relative to vehicle motion.

## Links

- Repository: https://github.com/suhaslord/uav-safety-research
- Current Webots research PR: https://github.com/suhaslord/uav-safety-research/pull/52
