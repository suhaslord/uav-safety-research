# AegisLand research checkpoint — 2026-08-10

## Why this checkpoint exists

This document freezes the current research story before more feature development. Its purpose is to make the project auditable by someone who has not followed the implementation history: what was built, which results are frozen, which evidence is development-only, what external-simulator evidence actually showed, what remains unresolved, and what claims are explicitly out of scope.

AegisLand is a **simulation-only research project** studying whether confidence-aware, redundant perception can expose persistent perception errors in an autonomous landing task without making the system unusably conservative. It is not a physical-flight validation project and it is not evidence that a real aircraft is safe.

## Core research question

The project asks a narrow question:

> When a primary perception stream is internally consistent but wrong, can an independent source of state evidence reveal that error, and can the system abstain selectively rather than either trusting everything or rejecting everything?

The project deliberately evolved by preserving failures and testing assumptions around earlier results rather than repeatedly tuning one simulator until the numbers looked favorable.

## Research-integrity rules used throughout

1. Frozen or held-out evidence is not reused as unseen evidence later.
2. Development seeds are labeled as seen development evidence.
3. A negative external result is preserved rather than tuned away.
4. Fixture data is labeled non-authoritative and is used only to test the pipeline.
5. Missing measurements are represented as missing/insufficient, not silently replaced with favorable values.
6. Evidence bundles record exact code/configuration provenance and hashes where implemented.
7. Simulation evidence is never described as physical-flight validation.
8. Safety acceptance and controller tuning are disabled for external diagnostic evidence unless a future protocol explicitly justifies otherwise.

---

# Phase-by-phase progression

## Earlier baseline through V3

The early project established the central failure mode. A primary estimate can look temporally smooth and self-consistent while carrying persistent bias. Static confidence/risk thresholds improved safety mainly by becoming very conservative. Temporal smoothing restored availability but did not make persistent single-stream bias observable. V3 therefore introduced an independent redundant estimate and bias-aware fusion so disagreement could carry information that was unavailable from the primary stream alone.

The earlier frozen V3 benchmark comprised 10,000 simulated episodes. The strongest gains occurred in the difficult occlusion and mixed profiles, but these results still came from an abstract/synthetic perception and dynamics environment and were never treated as evidence about physical aircraft.

## Phase 5 — robustness and image transition

Phase 5 attacked the frozen V3 result with unseen seed families, degradation-strength sweeps, weaker/noisier reference estimation, reference dropout, persistent-bias sweeps, and an initial synthetic image renderer. This phase helped separate the abstract-estimator result from later image-specific questions and established a pattern of paired comparisons, uncertainty intervals, and retained failure modes.

## Phase 6 — temporal image perception

Phase 6 replaced the abstract primary observation with an end-to-end synthetic grayscale image path. It added a pixel estimator, temporal tracking/reacquisition, image-derived velocity, empirical confidence calibration, explicit abstention, and direct image observations into the Aegis fusion/supervision path.

This exposed an important new problem: a frame should not necessarily receive one global good/bad decision. Lateral position can still be useful while altitude inferred from apparent marker scale is unreliable.

## Phase 6B — component-selective perception, frozen result

**Frozen executable commit:** `b4e9838555e935a5ec42690495315473629b58f6`

**Frozen component gates:** lateral `0.80`, altitude `0.80`

**Held-out landing seed:** `868686`

**Held-out selective-perception seed:** `878787`

Phase 6B made confidence component-wise. Lateral image information can be retained while altitude is rejected, or vice versa, with the independent reference substituting only for the untrusted component.

The frozen held-out landing evaluation used 1,500 paired simulated landing episodes. Key Phase 6B outcomes were:

| Image condition | Phase 6B success | Phase 6B unsafe touchdown | Timeout |
|---|---:|---:|---:|
| clean | 100% | 0% | 0% |
| blur | 100% | 0% | 0% |
| low light | 97% | 0% | 3% |
| occlusion | 96% | 4% | 0% |
| mixed | 99% | 1% | 0% |

The separate held-out selective audit contained 10,000 synthetic frames. It showed strong altitude selectivity under several degradations at the frozen gate, while mixed-condition lateral selectivity remained a measured weakness. That limitation was retained rather than hidden.

**What Phase 6B supports:** a frozen result about this synthetic image/dynamics environment and this defined evaluation protocol.

**What it does not support:** real-camera, 6-DOF aircraft, hardware, or physical-flight safety claims.

## Phase 7 — external-validity stress program

**Audited development head:** `7354eeda8b975f45b659ce4f3f86c82501e6321d`

**Development seed:** `979797` (`development_seen`)

**Calibration seed:** `616161`

Phase 7 intentionally stopped trying to improve the Phase 6B percentage and instead attacked the assumptions surrounding it. It introduced separated GNSS-like lateral and barometric/range-like vertical sensing, mismatched update rates, latency, dropout, stale-state uncertainty growth, bias random walk, common-mode fault families, and a stronger plant with actuator lag, acceleration-rate limits, nonlinear drag, and colored disturbance.

Its audited development factorial contained 200 paired episodes across 40 cells, with only five episodes per cell. The correct interpretation is therefore **failure-discovery development evidence**, not a precise safety-rate estimate.

The factorial exposed sensitivity in some stronger-plant and common-mode-fault cells, especially combinations involving occlusion/mixed imagery and shared lateral bias. Those cells motivated higher-fidelity validation. They were not used to retune the frozen Phase 6B gates.

## Phase 8 — frozen higher-fidelity trace-validation method

**Frozen comparison head:** `bd62e3b31431306fd9d897f560be7325d711d21a`

Phase 8 created a simulator-agnostic trace comparison layer rather than immediately changing the controller. The frozen comparison computes empirical distribution and temporal diagnostics including KS distance, Wasserstein-1 distance, scale-normalized Wasserstein-1, quantiles, rates, correlations, lag-1 autocorrelation, timing behavior, dropout/unavailability runs, and optional transport/state-age measurements.

Each comparison is classified as `close`, `watch`, `mismatch`, or `insufficient`. Optional measurements that do not exist are marked insufficient rather than filled with zeros.

Deterministic CI fixtures are explicitly labeled:

- `external_evidence_status = fixture_non_authoritative`
- `claim_level = pipeline_validation_only`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`

The fixtures prove the pipeline executes and preserves discrepancies. They do not prove the surrogate resembles an external simulator.

## Phase 8 — genuine PX4/Gazebo evidence

**Audited evidence head:** `b9df03e111f3a796e50df440becc587c48ee7643`

**PX4 release:** `v1.17.0`

**Exact PX4 SHA:** `d6f12ad1c4f70ad3230afd7d86e971421e02fef4`

**Gazebo model:** `gz_x500`

**Evidence role:** `external_simulator_seen`

A completed PX4 SITL + Gazebo simulation produced a genuine ULog and was converted through the unchanged Phase 8 comparison pipeline. The evidence bundle retained simulator/configuration provenance and input/output hashes.

The frozen Phase 8 model-resemblance diagnostic classified the PX4/Gazebo trace as:

- overall: **`diagnostic_mismatch`**
- `close`: 1
- `watch`: 2
- `mismatch`: 9
- `insufficient`: 14
- `safety_acceptance = false`
- `controller_tuning_allowed = false`

This is an important negative result. Several Phase 7 surrogate navigation/timing distributions did not closely reproduce the independently executed PX4/Gazebo trace. The comparison thresholds and frozen safety system were not changed in response.

The standard `gz_x500` run contained no populated `vehicle_visual_odometry` stream, so the run could assess only the available navigation/reference behavior. It could not validate the AegisLand camera/perception surrogate.

**Correct statement:** “The frozen Phase 8 model-resemblance diagnostic classified this PX4/Gazebo trace as `diagnostic_mismatch`.”

**Incorrect statement:** “AegisLand passed external validation.”

---

# Phase 9 — external perception evidence

## Purpose

Phase 9 addresses the major unresolved Phase 8 limitation: genuine raw-camera/perception evidence. It adds a canonical perception-trace schema, raw-frame preservation and per-frame hashing, explicit target-visibility/truth geometry, observation-missing semantics, a deterministic non-authoritative fixture generator, a validator, tests, a Gazebo camera capture path, and a descriptive analysis path.

The first genuine camera trace is intentionally labeled `external_perception_seen`. No Phase 9 held-out/unseen result has been declared.

## Current branch state at this checkpoint

**PR:** #13 — `Phase 9: external perception validation foundation`

**Branch:** `phase9-external-perception-validation`

**Checkpoint implementation head before these documentation commits:** `353bf45bc8dcad5c7875570b91011d062014ab59`

**Base:** main at `babd4d9849c4792ff1cc002c51cc5dbbc6ed0221`

The PR remains a draft and is intentionally unmerged during review.

## What is green

On implementation head `353bf45bc8dcad5c7875570b91011d062014ab59`:

- CI push run `31456353375`: **success**
- CI pull-request run `31456355851`: **success**
- Phase 9 Perception Validation run `31456353391`: **success**

These paths cover compilation/tests, historical regression paths, the Phase 9 perception-trace machinery, deterministic raw fixture generation, frame hashing, and evidence-role assertions.

## Genuine Gazebo camera run: current blocker

Phase 9 Gazebo Camera Evidence run `31456353385` is **failed**, and that failure is intentionally part of this checkpoint rather than being hidden.

The run successfully:

- launched the pinned PX4/Gazebo environment;
- discovered the live camera topic rather than hard-coding an assumed transport path;
- captured genuine Gazebo image payloads;
- matched camera pose to the `camera_link` entity;
- completed the simulation mission according to mission metadata;
- uploaded a diagnostic evidence artifact even after the gate failed.

Artifact:

- name: `phase9-gazebo-camera-evidence-seen`
- artifact id: `9088349585`
- GitHub digest: `sha256:7d3a48d0f6d2e699b29bd15c2f30c39696e3473355f2cb212658f8d4f89f9a49`

Camera capture sanity:

- selected raw frames: **56**
- frames with matched camera pose: **55**
- image dimensions: **1280 × 960**
- raw payload bytes/frame: **3,686,400**
- image message index span: `0…550`
- matched pose entity: `camera_link`

Discovered camera transport:

`/world/aruco/model/x500_mono_cam_down_0/link/camera_link/sensor/imager/image`

Discovered pose transport:

`/world/aruco/pose/info`

The run did **not** reach the frozen Phase 9 scientific analysis. It stopped at a strict completed-ULog sanity gate. The predeclared gate requires at least 20.0 seconds of `vehicle_local_position_groundtruth` timestamp span; the uploaded raw ULog contains approximately **19.248 seconds** for that stream.

This means the current failure is best described as an **evidence-completeness/timing blocker**, not a successful or failed perception-resemblance result. No scientific Phase 9 verdict exists yet.

We are not weakening the 20-second gate after seeing 19.248 seconds. A later implementation pass, if undertaken, should make evidence duration reproducible relative to simulator time and then generate a fresh seen trace. The current artifact remains diagnostic evidence of the failed attempt.

---

# Verification matrix at the checkpoint

| Layer | Status | Interpretation |
|---|---|---|
| Python/unit/regression CI | PASS | software regression paths are green on the implementation head |
| Phase 9 fixture/perception validation | PASS | trace schema, raw-frame hashing, fixture role and validators work |
| Genuine Gazebo camera transport | PASS within failed run | real simulator image payloads and matched camera pose were captured |
| Genuine run mission metadata | PASS within failed run | mission metadata records completion |
| Genuine ULog completeness gate | **FAIL** | groundtruth stream spans ~19.248 s, below predeclared 20.0 s |
| Frozen Phase 9 scientific analysis | NOT RUN | no Phase 9 resemblance/acceptance conclusion exists |
| Physical-flight validation | OUT OF SCOPE | no hardware/real-flight claim |

A reviewer should therefore treat the project as **well-instrumented simulation research with a completed Phase 8 negative external-model result and an in-progress Phase 9 external-perception evidence path**, not as a validated UAV safety system.

---

# Reproducibility and provenance practices

Across the later phases, the repository increasingly records:

- exact Git SHAs for frozen/audited boundaries;
- explicit development/seen/unseen/fixture evidence roles;
- isolated random-number streams in paired simulation studies;
- calibration and evaluation seed separation;
- machine-readable metadata and configuration;
- SHA-256 result manifests;
- raw external-simulator evidence artifacts;
- simulator version and exact PX4 source SHA;
- raw frame files plus per-frame hashes in Phase 9;
- evidence receipts tying input and output hashes to the run;
- CI gates that verify protected historical paths remain unchanged.

The guiding principle is that a favorable number is less valuable than a result that another person can trace back to the exact code, configuration, and raw evidence that produced it.

# Important limitations

1. **Simulation only.** There is no physical-flight validation.
2. The historical and stronger internal plants are still simplified relative to a full aircraft.
3. Synthetic image degradation is not a calibrated real-camera model.
4. The Phase 7 200-episode factorial has only five episodes per cell and is failure-discovery evidence, not a safety-rate estimate.
5. The Phase 8 PX4/Gazebo evidence is one short external-simulator run, not broad multi-scenario external validation.
6. Phase 8 produced an overall diagnostic mismatch, showing important surrogate-to-PX4 distribution gaps.
7. Standard Phase 8 `gz_x500` evidence did not provide visual odometry, so camera/perception resemblance was unavailable there.
8. Phase 9 has captured genuine raw Gazebo camera frames, but the current genuine evidence run did not pass its predeclared ULog-duration completeness gate.
9. The first Phase 9 genuine trace is seen development/external evidence, not a hidden holdout.
10. No controller or threshold should be tuned on this same seen external trace and then evaluated on it as if it were unseen.
11. PX4 local-position outputs are estimator products and are not statistically independent of all aiding sources.
12. Passing software tests or fixture validation does not imply safety acceptance.

# What has gone well

The strongest part of the project is not a single percentage. It is the progression from a favorable synthetic result to increasingly difficult attempts to falsify it:

- component-selective confidence was frozen before held-out evaluation;
- later work attacked external validity rather than changing the frozen result;
- common-mode failure cases were introduced explicitly;
- higher-fidelity comparison produced a mismatch and the mismatch was preserved;
- missing image evidence in Phase 8 was recorded as insufficient rather than fabricated;
- Phase 9 preserves raw camera bytes and hashes;
- the current 19.248-second run is being kept as a failed completeness attempt rather than passing it by moving the gate.

That is the research story an external reviewer should evaluate.

# Questions for external reviewers

1. Is the separation between frozen, development-seen, external-seen, and fixture evidence scientifically clear and defensible?
2. Are the Phase 8 distribution/temporal resemblance diagnostics a reasonable first external-validity layer, or are important diagnostics missing?
3. Is preserving the Phase 8 `diagnostic_mismatch` without retuning the right interpretation?
4. Is Phase 9 raw-frame + timestamp + pose + SHA-256 provenance sufficient for a first external-perception evidence layer?
5. Are any claims in the README/docs stronger than the evidence justifies?
6. What would be the most informative next external perception dataset or simulator condition after the current completeness blocker is resolved?
7. Before any future frozen/unseen Phase 9 evaluation, what should be preregistered that is not already preregistered?

# Pause / freeze statement

At this checkpoint, feature development is intentionally paused. The open Phase 9 branch should remain draft/unmerged while the current documentation is reviewed. The existing failed genuine-camera run remains part of the audit trail. No threshold, controller, or scientific acceptance rule should be changed merely to make the current evidence pass.
