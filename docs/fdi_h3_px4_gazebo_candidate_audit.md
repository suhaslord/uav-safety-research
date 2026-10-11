# H3 candidate assessment — existing PX4/Gazebo Phase 8 pathway

**Reviewed:** 2026-10-11 · **Outcome:** **NOT_ADMITTED / engineering preflight only.** No H3 fault-isolation data or independent motor-failure metrics exist.

## What the repository already supports

- [scripts/run_px4_gazebo_mission.py](../scripts/run_px4_gazebo_mission.py) drives an independent PX4 SITL + Gazebo simulated mission using MAVSDK offboard position commands. It records deterministic local-NED segments and waits for simulated local-position/armability readiness. This uses a **different simulator/vehicle pathway** from the Bitcraze Crazyflie Webots pilot and therefore is a plausible *candidate* for an independent-dynamics study.
- [scripts/px4_ulog_to_phase8_trace.py](../scripts/px4_ulog_to_phase8_trace.py) converts PX4 ULog records for the existing Phase 8 *perception/local-position* trace. It reads position-groundtruth, local reference and optional visual odometry. It also explicitly marks unobserved external vision as dropped rather than fabricating visual data.

These are real repo capabilities, but **neither script establishes a four-motor actuator-failure detection experiment.**

## Blockers to H3 admission

| Requirement | Existing Phase 8 status | Action before any protected trial |
|---|---|---|
| Second plant source & runtime digest | PX4/Gazebo pathway exists, but no pinned H3 source/digest manifest | Pin PX4 revision, Gazebo image, exact model and physical inertia/motor configuration |
| Angular-rate channels p/q | Existing Phase 8 export centers on position, not a frozen gyro p/q motor-fault contract | Identify and verify PX4 ULog angular-velocity topic, body axes, units and timing; convert with no leakage |
| Four motor-class labels | Phase 8 mission has no injected single-motor failures | Define independent simulated motor actuator-loss injection with logged actual application and motor ID |
| Motor index/quadrant mapping | Webots' motor order/sign map cannot be assumed on PX4/Gazebo | Freeze motor indexing and physical coordinate conventions via engineering model review before holdout results |
| Causal online noise | No H3 online noisy gyro/controller contract | Document simulator-side sensor perturbation and whether it affects estimation and closed-loop control |
| Healthy maneuver challenges | Existing Phase 8 mission uses a fixed local-NED hold sequence | Freeze a fresh set of varying command trajectories with healthy maneuvers and prospective fault times |
| Protected independence | Phase 8 is a different topic, not a frozen H3 validation set | Reserve >=12 new independent command-seed clusters distinct from all H1/H2 seeds |
| Contact/stability gate | Phase 8 tracks landing/dismount, not H3 pre-impact event detection | Define independently measurable contact/censor events and bounded pre-impact state validation |

## Implemented: read-only ULog signal inventory

The new `scripts/fdi_h3_px4_ulog_preflight.py` does not run Gazebo, arm a vehicle or modify a PX4 setting. Given an **existing recorded PX4 ULog**, it checks the presence and integrity of `vehicle_angular_velocity` (`xyz[0]`, `xyz[1]`, `xyz[2]`) and `actuator_motors` (`control[0]` through `control[3]`). It checks finite values, timestamp order, recording span and overlap, records a SHA-256 digest of the log, and writes a structured status.

```bash
python scripts/fdi_h3_px4_ulog_preflight.py \\
  path/to/existing_px4_recording.ulg \\
  --output results/fdi_h3_preflight/example_local_report.json
```

The tool is intentionally read-only and refuses to infer actual **applied** motor thrust or index-to-quadrant parity from commanded actuator outputs alone. Even a complete result says **READY_FOR_MANUAL_SIGNAL_MAPPING**, never **ADMITTED** or **H3_PASS**. The existing Phase 8 logs may lack an `actuator_motors` stream or suitable angular-rate topic; in that case the preflight should fail, and this absence is evidence of incomplete instrumentation rather than something to impute. Synthetic-only unit tests are at `tests/test_fdi_h3_px4_ulog_preflight.py`.

**What has not happened:** no PX4 H3 .ulg recording has been inspected as part of this branch, no simulated motor-fault injection was performed, and no comparative H3 detector score exists.

## Candidate decision

**Do not run the frozen H1/H2 classifier on arbitrary converted Phase 8 position traces and call that H3.** There is no defensible p/q motor-label target there. First build and audit the simulator-to-telemetry interface using **development-only** runs. A separate reviewer should verify independence and unit/sign mappings, freeze the candidate manifest, and only then admit a new protected test.

Current evidence: **candidate simulation stack available; motor-fault instrumentation, sensor interface and independent protected evaluation absent**.

Follow the frozen [H3 protocol](fdi_h3_independent_dynamics_preflight.md) and enforce the [manifest gate](../scripts/fdi_h3_admission.py). The automatic gate can establish completeness of *documentation*, not scientific independence or flight safety.

## Additional H3 telemetry continuity gate (2026-10-11)

A logged gyroscope topic and a motor-command topic can overlap for several seconds on paper while containing too few **simultaneously observed** samples or a large data-recording gap. That would make a timing-sensitive 0.70-second detector evaluation unreliable.

The read-only preflight now checks **each topic inside the same shared time window**: at least 50 raw observations per topic and no gap longer than 0.20 seconds, including the window boundaries. It reports `overlap_samples` and `overlap_max_unobserved_s` per topic. It **rejects incomplete telemetry** rather than interpolating or filling missing motor commands. This is a conservative research instrumentation screen; a passing check still requires documented unit/sign conventions, control-to-actuator mapping, independent plant provenance, and evidence of actual simulated fault injection before H3 admission.

Four additional synthetic regression tests cover clean overlap, missing interior motor-command measurements, falsely dense data outside the overlap, and genuinely short overlap. No protected test results are generated by these checks.
