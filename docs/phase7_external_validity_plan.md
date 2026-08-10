# Phase 7 — External-Validity Stress Program

## Status

Phase 7 is a **new post-frozen research phase**. It does not alter or reinterpret the frozen Phase 6B result.

Frozen Phase 6B remains tied to executable commit:

- `b4e9838555e935a5ec42690495315473629b58f6`

Phase 7 asks a different question:

> Do the Phase 6B conclusions survive when the independent-reference assumption, sensor timing, failure independence, and point-mass plant are made less favorable and less abstract?

All Phase 7 work remains simulation-only.

## Why Phase 7 is needed

Phase 6B has strong internal validity inside its synthetic setup, but several assumptions limit external validity:

1. the historical independent reference estimator samples simulator state directly and adds generic noise;
2. reference errors are mostly independent of the image stream;
3. the plant is a first-order planar point mass with instantaneous commanded acceleration;
4. synthetic camera degradation and the reference model are not tied to a higher-fidelity simulator or measured sensor logs;
5. no common-mode failure family tests the case where both perception streams agree because both are wrong.

Phase 7 attacks those assumptions instead of retuning Phase 6B thresholds.

## Phase 7A — Multi-sensor reference surrogate

Replace the direct noisy-state reference with a separated simulated sensing stack:

- GNSS-like lateral position and horizontal velocity;
- barometric-like altitude;
- lower-altitude range-like vertical measurement;
- mismatched update rates;
- fixed transport latency plus latency bursts;
- dropout;
- slowly varying sensor bias;
- uncertainty growth with stale data.

Ground truth is used only inside the sensor simulator to synthesize measurements. The Aegis fusion/supervisor receives the same `ReferenceObservation` interface as before.

The parameters are generic stress-model values, **not** calibrated claims about a named physical sensor.

### Transport semantics

Transport delay uses a **scheduled-delivery queue**, not a history-index shortcut. Each reference packet is tagged with its acquisition step and scheduled latency. A packet:

- cannot arrive before its scheduled delivery time;
- is marked fresh only when that acquisition is newly delivered;
- is never re-delivered as a fresh update;
- may be overtaken by a newer lower-latency packet, in which case the obsolete older packet is discarded;
- leaves the last delivered estimate available as stale information while no new packet arrives, with growing state age and uncertainty.

This prevents a latency burst from silently becoming an artificial sensor dropout or from replaying an old measurement as if it were new.

The benchmark reports both the **latency currently configured by the fault condition** and the **transport delay of the packet actually being used**, plus delivered-state age. These quantities are intentionally distinct during latency transitions.

### Sensor-channel RNG isolation

GNSS-like, barometric-like, and range-like sensors use separate deterministic child RNG streams. The range stream consumes its scheduled draws even while the vehicle is above the simulated range-sensor operating altitude.

This is important for the paired plant experiment. If the stronger plant reaches the range-sensor region at a different time from the legacy plant, that state-dependent activation must not shift the later GNSS or barometer random-number sequence. The isolated streams make the paired comparison more interpretable: plant trajectories can change sensor *values*, but one sensor's activation cannot change another sensor's noise sequence.

## Phase 7B — Correlated and common-mode faults

Predeclare explicit fault families rather than hiding them inside aggregate noise:

- `independent` — ordinary sensor noise/dropout only;
- `reference_drift` — the backup reference slowly becomes biased;
- `shared_lateral_bias` — camera and reference acquire the same lateral offset, representing a measurement-space proxy for a shared frame/map/geometry error;
- `shared_dropout` — both streams become intermittently unavailable during the same interval;
- `latency_burst` — reference delivery becomes temporarily stale.

The `shared_lateral_bias` condition is especially important because cross-estimator agreement is not evidence of correctness when both streams share the same error source.

For Phase 7, an image observation marked dropped is also forced to component-abstain: `p_x_good = 0` and `p_z_good = 0`. A simulated camera outage therefore cannot keep contributing trustworthy-looking component scores merely because the underlying synthetic frame still exists inside the renderer. The benchmark records the realized image-drop rate explicitly.

## Phase 7C — Stronger planar dynamics

The first bridge beyond the historical point mass adds:

- acceleration actuator lag;
- acceleration rate limits;
- linear and quadratic drag;
- colored disturbance memory;
- separate environment and dynamics RNG streams.

This remains a planar educational model. It is deliberately a bridge, not a claim of aircraft-identification fidelity.

### Factorial plant design

The new sensing/fault model and the stronger plant must not be changed as one inseparable treatment. Phase 7 therefore runs the same condition/fault episode seed on two plant models:

- `legacy` — the historical planar dynamics;
- `phase7` — lagged/rate-limited/nonlinear dynamics with colored disturbances.

This creates a paired plant comparison for each condition/fault/seed. It lets us distinguish a sensing/common-mode weakness from sensitivity introduced by the stronger plant model.

The image, reference, fault, and dynamics random streams are explicitly separated. Within the reference stack, GNSS/barometer/range streams are further isolated so plant-dependent range activation does not contaminate the paired comparison by shifting unrelated sensor noise.

Plant-model effects are reported separately rather than averaged into the main fault result.

## Phase 7D — Higher-fidelity backend

The preferred next simulator backend is **PX4 SITL + modern Gazebo**, initially as an offline/log-replay validation source rather than a physical-flight workflow.

Reasons:

- current PX4 documentation identifies modern Gazebo as the recommended simulator for new work and describes richer physics/rendering and sensor simulation;
- PX4 documents simulated camera, LiDAR/depth, IMU, GPS, barometer, and magnetometer support in Gazebo;
- PX4 SIH provides a faster deterministic physics/sensor path that can be useful as an intermediate estimator/sensor sanity check;
- PX4 documents simulator interfaces that preserve a separation between simulated ground truth and estimator outputs, which is useful for evaluating perception and state-estimation error.

Primary references:

- https://docs.px4.io/main/en/simulation/
- https://docs.px4.io/main/en/sim_sih/
- https://docs.px4.io/main/en/sensor/rangefinders
- https://docs.px4.io/main/en/sensor/barometer
- https://gazebosim.org/docs/latest/sensors/

AirSim remains a useful reference for multi-sensor simulation concepts (camera, barometer, IMU, GPS, magnetometer, distance sensor, LiDAR), but Phase 7 currently prioritizes the PX4/Gazebo path because it connects the perception study to an actively documented autopilot simulation stack without requiring physical hardware.

Reference:

- https://microsoft.github.io/AirSimExtensions/sensors/

## Higher-fidelity integration order

The integration order is intentionally conservative:

1. **offline trace schema** — define a neutral log format for truth, image estimates, reference estimates, and timestamps;
2. **Gazebo/PX4 replay import** — ingest simulator logs and evaluate Aegis decisions without sending control commands back;
3. **distribution comparison** — compare noise, latency, dropout, disagreement, and cross-sensor error correlation against Phase 7 surrogate assumptions;
4. **simulation-in-the-loop only** — if replay results are stable, connect the same research supervisor inside SITL for closed-loop simulation;
5. physical flight remains out of scope for this repository.

The repository now includes an offline external-trace schema and validator. In addition to basic trace integrity, it reports image/reference lateral MAE, their disagreement, and simultaneous lateral-error correlation so the independence assumption can be checked against higher-fidelity simulator logs. The bridge intentionally accepts logs for analysis only and does not provide a physical-flight control path.

## Development experiment

The Phase 7 development family uses:

- seed: `979797`;
- calibration seed: `616161` (historical image-calibration seed, already seen and used only for calibration);
- conditions: clean, low light, occlusion, mixed;
- fault families: all five Phase 7 fault scenarios;
- plant models: legacy and stronger Phase 7;
- paired episode seeds across the two plant models.

The first non-factorial development pass used 10 episodes per condition/fault cell. It is development evidence only and is not a frozen Phase 7 result.

A subsequent factorial pass uses 5 episodes per condition/fault/plant cell so the total run remains compact while each episode is paired across the two plant models. This pass is used to inspect attribution and experiment mechanics, not to make a final safety claim.

Several early Phase 7 development attempts are intentionally superseded for interpretation because interface audits found modeling-semantics problems before those outputs were accepted: delayed-new packets were initially marked non-fresh, the first latency implementation used history indexing instead of packet scheduling, and image-drop faults initially left component confidence available. The corrected architecture is rerun rather than retroactively treating those earlier outputs as evidence.

No Phase 7 held-out seed is declared yet.

## Primary outcomes

Per condition/fault/plant cell report:

- success rate and 95% Wilson interval;
- unsafe-touchdown rate and 95% Wilson interval;
- safe-abort rate and 95% Wilson interval;
- timeout rate and 95% Wilson interval;
- realized image-drop rate;
- reference availability and new-delivery rate;
- configured reference latency;
- delivered packet transport latency;
- mean and maximum delivered-state age;
- maximum simulated reference lateral bias;
- maximum shared visual lateral bias;
- lateral and altitude component abstention rates;
- intervention count;
- final lateral and touchdown-speed errors.

For every condition/fault pair also report paired legacy-vs-Phase 7 plant deltas and paired outcome transitions.

## Result provenance

Every Phase 7 result bundle records the complete default configuration used for:

- sensor stack;
- scheduled-delivery transport model;
- channel-isolated sensor RNG model;
- fault model;
- stronger dynamics;
- frozen Phase 6B component gates;
- frozen V3 supervisor.

The runner writes the exact executable Git commit into `git_sha.txt`, `run_metadata.json`, and the dashboard bundle. It also writes `result_manifest.json` with file sizes and SHA-256 hashes for the episode table, aggregate summary, paired plant effects, commit marker, metadata, Markdown summary, and dashboard bundle. The development seed is explicitly marked as seen.

The companion manifest validator detects missing files, size changes, hash changes, and unsafe relative paths.

This prevents a later result directory from being treated as equivalent merely because it has the same filename.

## Research cockpit

`dashboard/` provides a dependency-free local analysis interface for Phase 7 result bundles. The preferred input is the runner-generated `dashboard_bundle.json`; CSV fallback mode remains available.

The cockpit can:

- filter by condition, fault, and plant;
- show success, unsafe touchdown, abort, and reference-availability confidence intervals;
- expose reference delivery, configured latency, delivered transport delay, and state age;
- compare the paired legacy and stronger plants;
- render the unsafe-touchdown condition × fault matrix;
- rank the highest observed unsafe-touchdown cells first without inventing a weighted score;
- display run role, exact commit, development-seed status, and sample count.

The cockpit deliberately labels Phase 7 as development evidence and simulation-only. It is not a vehicle-control interface. It uses no external JavaScript libraries, services, or telemetry.

Run it with:

```bash
python scripts/serve_dashboard.py
```

## Interpretation rules

1. Phase 7 does not overwrite frozen Phase 6B.
2. A worse Phase 7 result is informative evidence of an external-validity weakness, not a reason to hide the run.
3. Do not tune Phase 6B's frozen `0.80 / 0.80` component thresholds against Phase 7 failures.
4. Any Phase 7 algorithm change motivated by development results must be recorded before a future held-out seed is declared.
5. Common-mode failures must be reported separately; do not average them into an easy-condition headline.
6. Plant-model effects must be reported separately so sensing/fault failures are not conflated with dynamics sensitivity.
7. The higher-fidelity simulator stage should first be used for log replay and distribution checks before closed-loop SITL claims.
8. A zero observed unsafe-touchdown rate in a small development cell is not evidence of zero real risk.
9. Superseded development attempts remain part of the audit trail but are not mixed into the accepted development result.
10. A paired plant result is interpreted as plant sensitivity only after verifying that state-dependent sensor activation cannot shift unrelated RNG streams.

## Success criterion for this phase

Phase 7 is successful as research if it tells us **where the Phase 6B conclusion stops generalizing**.

A scientifically useful outcome may therefore be:

- strong robustness under independent sensor realism;
- degraded performance under correlated faults;
- a clear common-mode failure boundary;
- plant-model sensitivity that changes the interpretation of a sensing result;
- or evidence that the current controller/supervisor needs a new architecture before higher-fidelity simulation.

The goal is not to preserve a high success percentage. The goal is to make the claim more defensible.

## Safety scope

Phase 7 is simulation-only research. It does not provide real-aircraft operating guidance, hardware integration instructions, or physical-flight validation.
