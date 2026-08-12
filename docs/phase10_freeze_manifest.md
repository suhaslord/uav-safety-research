# Phase 10 freeze manifest — AegisT10

Status: **architecture frozen before Phase 10 holdout evidence generation**

Frozen implementation SHA: `fb928d5b0d1fbee7459d55120d5fd6b232a4f2c6`

Protected Phase 9 evidence head: `33c5c73768757b508f5c613b2fba73f94e3fd5a6`

Frozen development calibration SHA-256:
`8934d108de1e0fa99f6985e643bb3b81145cfd6d7f901e1dcc900bb84673b6e7`

## Pre-freeze validation

The frozen implementation passed both required exact-head gates before the holdout workflow was added:

- Phase 10 Development run `31565143173` — success
- repository CI run `31565143144` / CI #621 — success

The Phase 10 development workflow includes the complete legacy pytest regression suite plus the deterministic paired Phase 10 fixture.

## Frozen estimator

Model: `AegisT10-deterministic-temporal`

The following implementation/configuration files are frozen at `fb928d5b0d1fbee7459d55120d5fd6b232a4f2c6`:

- `src/uav_safety/phase10_metric.py`
- `src/uav_safety/phase10_calibration.py`
- `scripts/run_phase10_metric_benchmark.py`
- `results/phase10_development_seen/calibration.json`

Frozen key configuration:

- lateral alpha: `1.0`
- altitude alpha: `1.0`
- lateral beta: `0.65`
- altitude beta: `0.15`
- quad lateral innovation gate: `0.75 m`
- quad altitude innovation gate: `1.00 m`
- quad minimum detected area: `1000 px²`
- quad gated position gain: `0.20`
- quad gated velocity gain: `0.05`

No value above may be changed after holdout evidence is exposed without starting a new Phase 10 revision and declaring the existing holdout seen.

## Development evidence used before freeze

The already-inspected Phase 9 artifact was used only as `phase10_development_seen`.

Phase 9 artifact:
- workflow run `31523496671`
- artifact ID `9114281248`
- artifact digest `sha256:bd2387f9518c7feb0bb5b8d7d02ccc7cbf416a73cd13e150ebeab06551b041a6`

The development analysis identified the fixed quad fallback as the dominant Phase 9 metric-geometry failure. AegisT10 showed large paired improvements on that seen trace, but those values are explicitly not the Phase 10 final result.

## Frozen holdout

The first Phase 10 holdout is generated only after this freeze marker exists.

Evidence role: `phase10_holdout_unseen`

Simulator:
- PX4 `v1.17.0`
- `gz_x500_mono_cam_down`
- Gazebo world `aruco`
- same Phase 9 raw-camera collector and unchanged Phase 9 front-end analyzer

New holdout mission:
`phase10_frozen_holdout_trajectory_v1`

The trajectory is predeclared in `scripts/run_phase10_gazebo_camera_mission.py` and differs from Phase 9 in combined north/east offsets, altitude order, direction changes, and yaw. It contains 11 fixed segments. The exact frame evidence does not exist at the time of this freeze.

Lighting/world variation is not claimed: this first holdout changes camera trajectory/view geometry while retaining the pinned Phase 9 Gazebo world. That limitation must remain visible in the final interpretation.

## Evaluation policy

The frozen workflow must:

1. verify the four frozen implementation/calibration files are byte-unchanged from `fb928d5b0d1fbee7459d55120d5fd6b232a4f2c6`;
2. generate genuine new PX4/Gazebo camera evidence;
3. run the unchanged Phase 9 front-end on those frames;
4. run Phase 9, trivial causal smoothing, and AegisT10 on paired rows;
5. load the frozen development calibration rather than fitting on holdout;
6. record every minimum success-gate component without failing merely because the scientific hypothesis fails;
7. preserve raw camera capture, ULog, Phase 9 analysis, Phase 10 per-frame output, manifests, and hashes.

## Predeclared success gate

The Phase 10 minimum substantial-win gate remains the protocol gate:

- >=50% lateral MAE reduction vs paired Phase 9
- >=50% altitude MAE reduction
- >=35% lateral p95 reduction
- >=35% altitude p95 reduction
- <=2 percentage-point metric-availability loss
- no false-positive regression
- median normalized residual below 2.0 on both axes

Failure of one or more gates is a valid frozen result and must not cause post-hoc tuning.

## Scope

Simulation only.

`safety_acceptance = false`

`controller_tuning_allowed = false`

No physical flight is authorized or validated by this freeze.
