# UNM Crazyflie Webots resilience benchmark

This directory is a bounded simulation study following Seif Elsabagh's guidance:

1. generate one genuine Crazyflie Webots baseline;
2. keep that exact trajectory and estimator configuration fixed;
3. test **noise**, **bias**, and **dropout** separately;
4. sweep one severity variable at a time and compare estimator response.

## What is stock vs changed

The GitHub Actions run pins the official Bitcraze `crazyflie-simulation` repository
to commit `7e93752dbc803af2488c1db46bb79b3da55f5d8c` and runs the official
`crazyflie_world.wbt` model with Bitcraze's stock Python
`pid_velocity_fixed_height_controller`.

The experiment changes only two things around that stock model/controller:

- keyboard commands are replaced with a deterministic, documented body-frame
  velocity schedule so the same moving trajectory is reproducible headlessly;
- telemetry is logged to CSV.

No fault is injected into the flight controller. The position degradations are
applied **offline** to the saved Webots trajectory so every fault case uses the
same underlying flight.

## Deterministic trajectory

- 0–5 s: take off and settle at 1 m
- 5–10 s: +0.25 m/s forward
- 10–15 s: +0.25 m/s sideways
- 15–20 s: -0.25 m/s forward
- 20–25 s: -0.25 m/s sideways
- 25–32 s: hover and settle

This is intentionally simple enough to explain segment by segment.

## Estimator

`analyze_faults.py` uses one fixed 2D constant-velocity Kalman filter with state
`[x, y, vx, vy]`.

Each step does:

1. **predict** position/velocity forward using elapsed time `dt`;
2. grow uncertainty using a fixed acceleration-process-noise assumption;
3. if a position measurement exists, compute the measurement innovation;
4. perform the Kalman update;
5. if the position measurement is dropped, skip the update and predict only.

The Webots baseline x/y positions are the simulator reference trajectory. Faulty
position measurements are derived from that one trace.

## Fault matrix

### Noise only
Zero-mean Gaussian position noise:

`σ = 0.04, 0.08, 0.16, 0.32 m`

Each level uses 30 deterministic seeds.

### Bias only
A fixed +x position offset from 12–16 s:

`bias = 0.05, 0.10, 0.20, 0.40 m`

### Dropout only
No position update starting at 12 s:

`duration = 0.5, 1, 2, 4 s`

## Metrics

- measurement coverage
- measurement RMSE where a measurement exists
- estimator RMSE over the whole run
- estimator RMSE during the fault window
- maximum estimator position error
- recovery time after the fault

Recovery means the estimator error is at or below 0.10 m continuously for at
least 0.5 s after the fault ends.

## Run locally after obtaining a Webots log

```bash
python experiments/unm_crazyflie/test_analysis.py
python experiments/unm_crazyflie/analyze_faults.py \
  experiments/unm_crazyflie/results/webots_baseline.csv \
  --out-dir experiments/unm_crazyflie/results
```

## Interpretation limits

This is a **simulation-only** benchmark. It does not claim physical-flight
robustness. The injected faults are deliberately simple controlled measurement
faults used to understand estimator behavior before considering more realistic
failure models.
