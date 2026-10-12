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

## Development-only observed-signal export (2026-10-11)

`scripts/fdi_h3_px4_development_trace.py` now prepares a **read-only raw-log development trace**, not a fault trial. It runs the stricter ULog preflight before exporting anything. For each *observed* gyro sample in the shared window, it joins only the latest actuator command with a timestamp **at or before** that gyro sample. If the command is older than 100 ms, export fails instead of silently filling a gap. No gyro interpolation or retrospective borrowing of future motor commands is permitted.

The CSV preserves the three logged angular-velocity channels, four *commanded* actuator outputs, original ULog topic timestamps, and command age. Channel names carry an explicit `unmapped` suffix: motor numbers and axis signs are not assumed to match H1. A SHA-256 source digest and explicit `DEVELOPMENT_ONLY_UNMAPPED` status are stored in the metadata; no fault labels, detector decisions, performance values or independent-simulator admission are generated.

From a repository checkout with `pyulog` installed, run this **on an existing recorded ULog only**:

```bash
python -m scripts.fdi_h3_px4_ulog_preflight path/to/recording.ulg --output local-h3-preflight.json
python -m scripts.fdi_h3_px4_development_trace path/to/recording.ulg \
  --csv local-h3-unmapped.csv --metadata local-h3-unmapped.json
```

Keep development traces separate from future protected H3 evidence. The exporter deliberately does not claim physical actuator response, measurement timestamps (`timestamp_sample`), alignment accuracy, simulator independence, motor fault injection, or any validated fault-isolation result. New synthetic regression tests specifically reject future-command borrowing, stale actuator data and non-finite telemetry.

## Fresh independent-simulator development telemetry attempt

The earlier successful Phase 8 PX4/Gazebo jobs [31451880394](https://github.com/suhaslord/uav-safety-research/actions/runs/31451880394) and [31451862547](https://github.com/suhaslord/uav-safety-research/actions/runs/31451862547) ran on 2026-08-11. Both currently return **no downloadable workflow artifacts**, so those raw .ulg files could not be audited for H3.

The separate GitHub Actions workflow `.github/workflows/fdi-h3-px4-development-capture.yml` is restricted to a dedicated H3 development branch and manual dispatch. It reruns the **existing, non-fault** PX4/Gazebo mission to collect a fresh raw ULog, pins the PX4 release and commit and the declared Gazebo model, runs the read-only H3 telemetry preflight, then attempts a strictly **unmapped development CSV export**. It preserves a provenance receipt and the raw file as a short-lived GitHub Actions artifact, including failures if the requested motor/gyro topics were absent.

This capture **does not introduce motor failures**, does not evaluate the H1/H2 classifier, does not access H3 protected seeds, and cannot admit H3 or establish independent fault-isolation accuracy. Source-level plant independence, motor ordering, applied actuation, measurement timestamps, online sensor/noise configuration, actual simulation-side fault conditions, and a separately frozen holdout still require independent review. An incomplete recording must be recorded as a blocker, never converted into a successful H3 result.

## Development capture failure and dependency correction (2026-10-11)

The first independent PX4/Gazebo development capture [run 38142829434](https://github.com/suhaslord/uav-safety-research/actions/runs/38142829434) built and started headless PX4 successfully but **did not fly the development mission**. Python failed while importing `mavsdk.offboard` because the unbounded dependency resolved to MAVSDK 4.0.6, whose native API is incompatible with the legacy mission script. The archived raw `.ulg` is a startup/debug recording, **not** a successful mission or H3 fault trial. Neither the ULog signal preflight nor the development CSV export ran, and no detector metrics can be inferred.

The capture workflow now installs `mavsdk<4`, tests the legacy `mavsdk.offboard` import **before** the costly SITL setup, and preserves the installed package metadata in the run artifact. The original failure remains preserved, and any replacement capture must demonstrate a completed simulated mission and passing signal checks before progressing to manual motor-map review. This change corrects a software API mismatch; it does **not** admit independent H3 trials or establish simulated flight safety.


## First completed PX4 development capture — independently reconciled (2026-10-11)

The [corrected PX4/Gazebo capture run 38143526133](https://github.com/suhaslord/uav-safety-research/actions/runs/38143526133) passed after pinning the legacy MAVSDK API generation. Its [development artifact 11704047252](https://github.com/suhaslord/uav-safety-research/actions/runs/38143526133/artifacts/11704047252) contains the source revision, completed eight-segment mission receipt, unmodified ULog, preflight, unmapped CSV, and source SHA-256. The artifact from this run was configured for **14-day retention**; newer workflow revisions request **90 days**.

**Recorded observations (development only):**

| Check | Observed |
| --- | --- |
| PX4 release / pinned source | `v1.17.0` / `d6f12ad1c4f70ad3230afd7d86e971421e02fef4` |
| Model | Gazebo `gz_x500` |
| Installed MAVSDK in successful run | `3.17.4` (legacy gRPC API) |
| Simulated mission metadata | `completed: true`, eight maneuver segments |
| Shared gyro/actuator window | 41.8 seconds |
| `vehicle_angular_velocity` overlap observations | 4,182 |
| `actuator_motors` overlap observations | 420 |
| Exported causal/unmapped paired CSV rows | 4,182 |
| Greatest age of associated actuator command | 96 ms (limit: 100 ms) |
| Raw ULog SHA-256 | `727503330869b1e787b1bb571f5ab1fa1d921c7e5e927b7b117f06dfb85cc37b` |
| Preflight | `READY_FOR_MANUAL_SIGNAL_MAPPING` — zero errors |
| Development export | `DEVELOPMENT_ONLY_UNMAPPED` — no motor labels or predictions |

The archived ZIP was additionally checked by a separate read-only, standard-library auditor: `scripts/fdi_h3_development_bundle_audit.py`. It reconciles the raw recording checksum with all receipts and preflight/export metadata, checks mission completion, CSV row counts, causal command time alignment, finite channels and age bounds, and **rejects any claim of H3 fault results**. The 4,182-row source ZIP passed the bundle-consistency check with zero reported errors. The auditor's result is `CONSISTENT_DEVELOPMENT_ONLY`, **not independent-dynamics admission**; it does not independently parse the ULog to reproduce every exported numeric channel, establish physical motor mappings, or verify fault injection.

To audit a downloaded artifact ZIP locally, without a simulator:

```bash
python -m scripts.fdi_h3_development_bundle_audit fdi-h3-px4-development-only.zip \
  --output development_audit.json
```

The GitHub Actions workflow now performs this audit before upload, pins `mavsdk==3.17.4`, and requests 90-day retention for new artifacts. Regression tests deliberately reject falsified checksums, missing missions, future/stale actuator associations, nonfinite gyro data, row-count discrepancies, and any claim of protected H3 scoring.

**Next scientific gate:** source-review the pin-to-Gazebo motor/joint mapping and gyro units, sign, timestamp basis; establish simulator-applied actuator fault observability and independently review its implementation, then freeze a new protected-seed set **before** attempting motor fault scores. No motor fault was injected or scored in this capture.


## Pinned PX4 / Gazebo source-level motor and gyro path review

The successful capture identified PX4 commit `d6f12ad1c4f70ad3230afd7d86e971421e02fef4`. At that exact commit, `Tools/simulation/gz` references model-source submodule `b6127f4ec20de867e215fb5f78ae88b80f371909` (not an unpinned latest model). The capture workflow now records and checks the submodule SHA as well as the PX4 SHA in future run receipts.

| Evidence | What the pinned source actually shows |
| --- | --- |
| [PX4 Gazebo x500 airframe](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/ROMFS/px4fmu_common/init.d-posix/airframes/4001_gz_x500) | Four configured control-allocation rotors, simulated output functions 101–104, and rotor position/moment-arm declarations in PX4's vehicle coordinate convention. |
| [Gazebo x500 motor plugins](https://github.com/PX4/PX4-gazebo-models/blob/b6127f4ec20de867e215fb5f78ae88b80f371909/models/x500/model.sdf) | Four explicit `MulticopterMotorModel` plugins: `motorNumber` 0, 1, 2, 3 target `rotor_0_joint` through `rotor_3_joint`, respectively; their rotations are CCW, CCW, CW, CW. |
| [Gazebo x500 base links](https://github.com/PX4/PX4-gazebo-models/blob/b6127f4ec20de867e215fb5f78ae88b80f371909/models/x500_base/model.sdf) | Rotor link poses in Gazebo coordinates: index 0 (`+0.174,-0.174`), 1 (`-0.174,+0.174`), 2 (`+0.174,+0.174`), 3 (`-0.174,-0.174`), meters. |
| [PX4 Gazebo ESC mixing bridge](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/simulation/gz_bridge/GZMixingInterfaceESC.cpp) | Publishes indexed `gz::msgs::Actuators.velocity(i)` entries to the model motor-speed command topic; this is a **command**, not independently measured thrust or rotor RPM. |
| [PX4 Gazebo IMU bridge](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/simulation/gz_bridge/GZBridge.cpp) | Rotates Gazebo IMU angular velocity from body FLU to body FRD before publishing `sensor_gyro`. The logged `vehicle_angular_velocity` topic is a downstream PX4 representation and still needs an explicit source-to-log sample/timestamp verification. |

**Important mapping caveat:** the airframe allocator's planar `CA_ROTOR*_PX/PY` values and the Gazebo SDF rotor poses are not numerically identical and are expressed in different coordinate conventions. Neither numeric index agreement nor a signed-axis guess suffices to declare H1 motor-class equivalence. A runtime engineering check must confirm model-joint identity, actual simulated actuation, frame conversion, and which downstream `vehicle_angular_velocity` data correspond to the sensor measurements.

This investigation narrows the remaining mapping task, but has **not** injected motor faults, verified physical rotor failure, checked online sensor-noise propagation, opened protected H3 seeds, or established independence/admission. Continue to report `NOT_ADMITTED`.


## Second development run: independent numeric ULog replay (2026-10-11)

[PX4/Gazebo workflow run 38154840182](https://github.com/suhaslord/uav-safety-research/actions/runs/38154840182) completed the non-fault mission, preflight, development export, independent receipt/bundle audit, and a new **raw ULog → exported CSV numerical replay**. Its preserved [90-day evidence artifact 11708446869](https://github.com/suhaslord/uav-safety-research/actions/runs/38154840182/artifacts/11708446869) includes the original raw ULog and the replay audit JSON.

| Observation | Run result |
| --- | --- |
| Replay status | `ULOG_CSV_REPLAY_MATCH` |
| Logged gyro samples replayed against CSV | **4,162 / 4,162** |
| Reported replay errors | **0** |
| Independently reconciled bundle status | `CONSISTENT_DEVELOPMENT_ONLY` |
| Raw ULog SHA-256 | `ec2af29f81863e7a6b66403cbc724676762e279f618e45ff7f0c46322b33e614` |
| Scientific admission | **NOT_ADMITTED** |

This is a **different recorded development run** from the 4,182-row first capture documented above; their counts and source-file hashes must not be conflated. The replay verifies original gyro values, four **commanded** actuator channels, nearest preceding command association and logged timestamps. It does not turn actuator commands into measurements of applied motor RPM or infer physical motor identity.

The replay CLI now **fails closed** on empty recorded topics, invalid or nonincreasing timestamp sequences, absent shared observations, and development archives rejected by the existing independent bundle auditor. This matters because a CSV containing only a header previously could pass when the two source topics had no overlapping samples. Dedicated synthetic tests cover those failure modes.

Re-run the independent development-only checks on the **downloaded run artifact** (not on protected H3 data):

```bash
python -m scripts.fdi_h3_development_bundle_audit path/to/development-bundle.zip
python -m scripts.fdi_h3_px4_ulog_csv_replay path/to/development-bundle.zip
```

**Remaining requirements before any motor-fault claim:** verify Gazebo joint-to-PX4 index and actual applied actuation at runtime, independently validate gyro axis/timestamp semantics, freeze an admissible fault-injection protocol and independent holdout seeds, then evaluate genuinely injected simulated failures. No H3 classification metrics are reported here.


## Automated frozen x500 model-source check (2026-10-12)

The initial PX4/Gazebo motor-source review above is now executable in a **read-only development gate**: `scripts/fdi_h3_px4_source_motor_gate.py`. After cloning the pinned PX4 source and model submodule, and **before starting the expensive simulator**, the H3 development capture workflow checks the exact `x500/model.sdf` and `x500_base/model.sdf` files.

The check rejects changes to the four motor plugin indices 0–3, joint/link references, expected source-space rotor XY positions, spin directions, model include, and `command/motor_speed` topic. It also ensures that the corresponding structural rotor joints exist and have the expected parent and child. An accepted report includes both input-file SHA-256 hashes, source index-to-joint descriptions, and `STATIC_SOURCE_MAP_VERIFIED` status. The new capture stores this report alongside the raw ULog and includes it in the independent evidence ZIP. The bundle auditor compares it with the provenance receipt; missing or inconsistent claimed evidence is rejected. Older already-preserved development bundles without a source report remain independently auditable.

For the **pinned candidate source checkout only**:

```bash
python -m scripts.fdi_h3_px4_source_motor_gate \
  --model-sdf /path/to/PX4-Autopilot/Tools/simulation/gz/models/x500/model.sdf \
  --base-sdf /path/to/PX4-Autopilot/Tools/simulation/gz/models/x500_base/model.sdf \
  --output source_motor_map_audit.json
```

Synthetic tests deliberately alter motor indices, joint names, coordinates, spin and command topics to prove that source drift fails the gate. **This is a source-code structural check, not a runtime fault trial**: it cannot establish applied RPM/thrust, PX4 log-to-Gazebo motor equivalence, H1 class mapping, accurate gyro axes, runtime fault injection, or independent-dynamics scientific admission. Those evidence gates and a new protected holdout are still mandatory.


## Sample-time vs publish-time review of the verified source capture (2026-10-12)

The [fully successful development capture run 38194770306](https://github.com/suhaslord/uav-safety-research/actions/runs/38194770306) produced [artifact 11723151763](https://github.com/suhaslord/uav-safety-research/actions/runs/38194770306/artifacts/11723151763). This includes a passing frozen x500 source gate, a completed non-fault PX4/Gazebo mission, 4,162 exact development CSV/ULog replay matches, and an independently accepted evidence bundle. The raw `.ulg` file SHA-256 is `c78fa8c95c8f00a56e43661f388d4df57b4890cc011e990eb19528179f032274`.

The frozen PX4 v1.17.0 [`VehicleAngularVelocity.msg`](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleAngularVelocity.msg) defines `timestamp_sample` as the time of the contributing sample and `timestamp` as the message publication timestamp. They are distinct *fields*, but should not be assumed to be independently observed clocks.

To check this, the new `scripts/fdi_h3_px4_sample_clock_audit.py` inspects the **entire existing raw ULog only**, without re-running the simulator. It checks for missing, duplicated, noninteger, negative or nonmonotonic time fields; never joins a later actuator command to an earlier gyro sample; and records descriptive sample-to-command ages. Run it as:

```bash
python -m scripts.fdi_h3_px4_sample_clock_audit path/to/px4_gazebo_raw.ulg \
  --output h3-sample-clock-audit.json
```

[Read-only audit run 38199734215](https://github.com/suhaslord/uav-safety-research/actions/runs/38199734215) passed 10 synthetic tests and the real source-ULog audit, preserving [artifact 11724718878](https://github.com/suhaslord/uav-safety-research/actions/runs/38199734215/artifacts/11724718878). Its measurements were:

| Development-only observation | Value |
| --- | ---: |
| All gyro observations inspected | 4,164 |
| Actuator command observations | 418 |
| Gyro samples with a preceding logged command | 4,164 |
| Median associated command age at `timestamp_sample` | 44 ms |
| 95th-percentile age, nearest rank | 92 ms |
| Maximum age | 96 ms |
| Commands older than the declared 100-ms limit | 0 |
| Gyro rows with identical `timestamp_sample` and `timestamp` | **4,164 / 4,164** |
| Observed sample-to-publication timestamp difference | **0 μs** |

The **4,164** whole-topic sample-clock observations are distinct from the **4,162** rows exported inside the shared gyro/command CSV time window; these denominators are not interchangeable. The source ULog reports identical sample and publish timestamps in all 4,164 gyro messages. This is a meaningful *measurement limitation*: **zero logged separation is not independent proof that actual sensing and publication have zero latency**, nor does it verify PX4-to-Gazebo synchronization. Future work must independently trace the simulation IMU sample through the PX4 estimator and verify motor-command-to-rotor behavior at runtime before mapping H1 class labels.

This remains `SAMPLE_CLOCK_OBSERVED_DEVELOPMENT_ONLY`; it is **not** a demonstrated applied fault, physical motor map, independent H3 holdout, or flight-safety result.
