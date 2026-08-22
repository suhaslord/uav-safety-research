# UNM Crazyflie / Webots resilience benchmark

This directory contains the reproducible Webots baseline and offline resilient-estimation experiments being developed from Seif Elsabagh's suggested single-fault progression.

## Experimental order

1. Generate one genuine Webots Crazyflie trajectory.
2. Keep that exact trajectory fixed.
3. Keep one fixed 2D constant-velocity Kalman-filter configuration.
4. Inject **one** measurement degradation at a time: Gaussian position noise, fixed position bias, or position dropout.
5. Sweep severity without changing the underlying flight.
6. Analyze how dropout timing interacts with vehicle maneuvers.
7. Inspect normalized innovation and covariance as simple fault/reliability indicators.

## Webots baseline

CI pins the official `bitcraze/crazyflie-simulation` repository to commit `7e93752dbc803af2488c1db46bb79b3da55f5d8c`. The stock Crazyflie plant and Bitcraze velocity/fixed-height PID are kept. Keyboard commands are replaced by a deterministic command schedule so a headless CI run follows the same path each time, and a logging-only controller writes the simulator telemetry.

The current genuine Webots run produces 1,000 samples over 31.968 s and a 1.733 m lateral path extent.

## Deterministic trajectory

- 0–5 s: take off and settle at 1 m
- 5–10 s: +0.25 m/s forward
- 10–15 s: +0.25 m/s sideways
- 15–20 s: -0.25 m/s forward
- 20–25 s: -0.25 m/s sideways
- 25–32 s: hover and settle

This is intentionally simple enough to explain segment by segment.

## Estimator

`analyze_faults.py` uses one fixed 2D constant-velocity Kalman filter with state `[x, y, vx, vy]`.

Each step predicts forward using elapsed time, grows covariance with a fixed acceleration-process-noise model, and uses a position measurement update when one is available. During dropout the measurement update is skipped and the filter predicts only.

## Original isolated fault matrix

Run:

```bash
python experiments/unm_crazyflie/analyze_faults.py \
  experiments/unm_crazyflie/results/webots_baseline.csv \
  --out-dir experiments/unm_crazyflie/results
```

The original matrix tests:

- Gaussian position noise: 0.04, 0.08, 0.16, 0.32 m sigma, 30 deterministic trials each;
- fixed +x bias: 0.05, 0.10, 0.20, 0.40 m from 12–16 s;
- position dropout: 0.5, 1, 2, 4 s starting at 12 s.

## Extended diagnostics

Run:

```bash
python experiments/unm_crazyflie/analyze_extended.py \
  experiments/unm_crazyflie/results/webots_baseline.csv \
  --results-dir experiments/unm_crazyflie/results
```

This adds:

- Webots XY trajectory plot;
- estimator error time histories;
- severity-response plots for noise, bias, and dropout;
- a fixed 2 s dropout timing sweep in 0.5 s increments;
- 0.5 s rolling normalized-innovation-squared diagnostics;
- Kalman covariance growth during dropout;
- a generated extended-results note.

## Current strongest finding

Dropout duration alone is not enough to describe estimator risk. With the exact same 2.0 s dropout, a steady 7–9 s segment reaches only about 0.004 m maximum position error, while a 10–12 s dropout starting at a commanded direction change reaches about 0.526 m.

Representative maneuver-adjacent windows averaged about 0.446 m maximum error versus about 0.006 m for representative steady windows, roughly 73 times larger in this trajectory.

The reason is model mismatch: a constant-velocity predictor works well during steady motion but can be badly wrong immediately after the vehicle changes direction and no measurements are available to correct the velocity state.

## Reliability diagnostics

Residual/NIS behavior detects the high-noise and high-bias examples because measurements still arrive and disagree with prediction. During dropout, no innovation exists, so covariance growth provides the basic warning signal.

A limitation is important: equal-duration dropouts produce almost the same covariance growth even though their true errors differ greatly around maneuvers. The current covariance model knows that measurements are missing, but it does not fully encode the extra model mismatch caused by a commanded direction change.

## Metrics

- measurement coverage
- measurement RMSE where a measurement exists
- estimator RMSE over the whole run
- estimator RMSE during the fault window
- maximum estimator position error
- recovery time after the fault
- normalized innovation squared (extended diagnostics)
- radial position uncertainty from the filter covariance (extended diagnostics)

## Interpretation boundary

These are **simulation-only** results. The baseline trajectory is genuine Webots output. The measurement faults are injected offline afterward so every estimator case sees exactly the same flight. Synthetic telemetry is used only in unit tests of the analysis logic and is never reported as Webots evidence.

See `TECHNICAL_EXPLAINER.md` for the concepts behind the state, prediction/update cycle, innovations, NIS, covariance, and maneuver-timing result.
