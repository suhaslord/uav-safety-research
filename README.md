<div align="center">

# AegisLand

### Confidence-Aware Redundant Perception for Simulated Autonomous UAV Landing

> **When vision is internally consistent but wrong, can independent evidence reveal the error without making the system unusably conservative?**

[![CI](https://github.com/suhaslord/uav-safety-research/actions/workflows/ci.yml/badge.svg)](https://github.com/suhaslord/uav-safety-research/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Phase 6B](https://img.shields.io/badge/Phase%206B-frozen-success)
![Phase 8](https://img.shields.io/badge/Phase%208-external%20mismatch-orange)
![Phase 9](https://img.shields.io/badge/Phase%209-revalidation%20pending-yellow)
![Scope](https://img.shields.io/badge/scope-simulation--only-blueviolet)
![License](https://img.shields.io/badge/license-MIT-green)

**A reproducible simulation study of persistent perception bias, calibrated abstention, redundant estimation, external-model mismatch, and the limits of those conclusions under distribution shift.**

</div>

---

## Current research status

AegisLand is in final-prototype refinement while its scientific boundaries remain frozen.

The strongest synthetic result remains the frozen **Phase 6B** evaluation. Later phases were designed to attack that result rather than keep tuning the same simulator. **Phase 8 produced a genuine PX4/Gazebo external-simulator trace and the frozen resemblance method classified it as `diagnostic_mismatch`.** That negative result is preserved.

**Phase 9 does not yet have a valid scientific external-perception result.** Its schema, deterministic fixtures, hashing, raw Gazebo image capture, tests, and descriptive-analysis machinery are implemented. Earlier genuine-camera attempts stopped before scientific analysis at a predeclared evidence-completeness gate; one preserved ULog ground-truth stream spanned about **19.248 s**, below the required **20.0 s**.

A later audit also found a separate provenance defect: the camera collector had been recording Gazebo's fixed local `camera_link` transform as though it were the camera's moving world pose. That would have made projected-truth geometry invalid if analysis had proceeded. The collector has now been corrected to compose the moving model world pose with the camera-link transform. **Fresh genuine-camera evidence is required before any Phase 9 scientific result is claimed.** Neither the detector nor the preregistered visibility/analysis rules were changed to make that correction.

So the defensible current summary is:

| Evidence layer | Status | What it supports |
|---|---|---|
| Phase 6B held-out synthetic landing | **frozen** | result for the defined synthetic benchmark |
| Phase 7 external-validity factorial | **audited development / seen** | failure discovery, not precise safety-rate estimation |
| Phase 8 deterministic fixture | **pipeline validation only** | trace/provenance machinery works |
| Phase 8 genuine PX4/Gazebo trace | **external simulator seen** | frozen model-resemblance diagnostic = `diagnostic_mismatch` |
| Phase 9 deterministic camera fixture | **pipeline validation only** | raw-frame schema/hash machinery works |
| Phase 9 genuine Gazebo camera evidence | **revalidation pending** | raw capture demonstrated; corrected world-pose provenance still requires a fresh artifact |
| Physical aircraft | **not tested** | no claim |

For the full audit trail, exact commits, run IDs, evidence hashes, limitations, and review questions, start with:

- **[Final prototype readiness](docs/final_prototype_readiness.md)**
- **[Research checkpoint — 2026-08-10](docs/research_checkpoint_2026-08-10.md)**
- **[External review packet](docs/external_review_packet.md)**
- [Phase 8 trace-validation protocol](docs/phase8_trace_validation.md)
- [Phase 9 external-perception protocol](docs/phase9_external_perception_protocol.md)

---

## Research progression

AegisLand was built by preserving measured failures rather than deleting old results when later evidence became less favorable.

| Stage | Main idea | What it taught us |
|---|---|---|
| **Baseline** | trust the primary estimate | easy cases are fine; severe bias can cause unsafe touchdowns |
| **V1** | static confidence/risk thresholds | safety can improve mainly by becoming unusably conservative |
| **V2** | temporal smoothing + persistence | availability returns, but persistent single-stream bias remains hard to detect |
| **V3** | independent redundant estimate + bias-aware fusion | independent error structure can expose persistent visual bias in abstract simulation |
| **Phase 5** | robustness sweeps | reference quality and distribution shift matter |
| **Phase 6** | synthetic pixel sequences | image perception introduces tracking, calibration, velocity, and observability failures |
| **Phase 6B** | component confidence + selective fusion | unreliable altitude can be rejected without discarding useful lateral image information |
| **Phase 7** | external-validity stress program | timing, common-mode faults, and stronger plant dynamics expose new weak cells |
| **Phase 8** | frozen higher-fidelity trace comparison | several internal surrogate distributions do not closely reproduce PX4/Gazebo evidence |
| **Phase 9** | raw external-perception evidence | raw camera evidence exposed both completeness and pose-provenance problems that must be resolved before interpretation |

---

## Frozen Phase 6B result

Phase 6B was frozen before held-out evaluation at:

`b4e9838555e935a5ec42690495315473629b58f6`

Frozen component-confidence gates:

- lateral: `0.80`
- altitude: `0.80`

The held-out landing seed `868686` produced **1,500 paired simulated landing episodes** across five image conditions and three architectures.

| Condition | Image-only success / unsafe | Original Phase 6 Aegis | **Phase 6B success / unsafe** | Phase 6B timeout |
|---|---:|---:|---:|---:|
| clean | 100% / 0% | 100% / 0% | **100% / 0%** | 0% |
| blur | 100% / 0% | 100% / 0% | **100% / 0%** | 0% |
| low light | 100% / 0% | 100% / 0% | **97% / 0%** | **3%** |
| occlusion | 86% / 14% | 93% / 7% | **96% / 4%** | 0% |
| **mixed** | **57% / 43%** | **94% / 6%** | **99% / 1%** | 0% |

A separate held-out selective-perception seed, `878787`, evaluated **10,000 synthetic frames** at the unchanged `0.80 / 0.80` gates. Altitude confidence became strongly selective in several degraded conditions, while mixed-condition lateral confidence remained a measured weakness.

The low-light timeout and mixed lateral-selectivity limitations are retained. Phase 6B is a result about this synthetic environment, not a physical-UAV claim.

Detailed result: [docs/phase6b_results.md](docs/phase6b_results.md)

---

## Phase 7: attack external validity

**Audited development head:** `7354eeda8b975f45b659ce4f3f86c82501e6321d`

**Development seed:** `979797` — already seen

**Calibration seed:** `616161`

Instead of tuning Phase 6B again, Phase 7 changed the assumptions around it. The stress program added separated reference-sensor roles, mismatched rates, transport latency, dropout, stale-state uncertainty growth, bias drift, common-mode fault families, and a stronger plant model.

The audited paired factorial contains **200 development episodes across 40 cells, only five episodes per cell**. It is therefore interpreted as **failure-discovery evidence**, not as a precise estimate of a safety rate.

Some stronger-plant/common-mode cells remained weak. Those failures motivated higher-fidelity comparison and did not trigger retuning of the frozen Phase 6B gates.

Phase 7 includes the dependency-free Research Cockpit under [`dashboard/`](dashboard/) for result inspection. It is an analysis interface, not a vehicle-control UI.

---

## Phase 8: higher-fidelity trace validation

**Frozen comparison head:** `bd62e3b31431306fd9d897f560be7325d711d21a`

Phase 8 froze a simulator-agnostic comparison method before evaluating genuine external-simulator evidence. The method compares empirical distributions and temporal structure using metrics including KS distance, Wasserstein-1 distance, normalized Wasserstein distance, quantiles, rates, correlations, lag-1 autocorrelation, and dropout/unavailability behavior.

Measurements are classified as:

- `close`
- `watch`
- `mismatch`
- `insufficient`

Missing optional measurements remain `insufficient`; they are not silently replaced by favorable values.

### Genuine PX4/Gazebo evidence

**Audited evidence head:** `b9df03e111f3a796e50df440becc587c48ee7643`

**PX4:** `v1.17.0` at `d6f12ad1c4f70ad3230afd7d86e971421e02fef4`

**Evidence role:** `external_simulator_seen`

The completed PX4/Gazebo run was processed through the unchanged Phase 8 comparison and produced:

- overall: **`diagnostic_mismatch`**
- `close`: 1
- `watch`: 2
- `mismatch`: 9
- `insufficient`: 14
- `safety_acceptance = false`
- `controller_tuning_allowed = false`

The correct interpretation is that several internal surrogate navigation/timing distributions did **not** closely reproduce the PX4/Gazebo trace. This is a useful negative result, not a failed attempt that should be tuned away.

That run had no populated visual-odometry stream, so camera/perception resemblance remained unavailable and motivated Phase 9.

---

## Phase 9: external perception evidence

Phase 9 adds:

- canonical `aegisland.phase9.perception-trace.v1` records;
- raw-frame paths and per-frame SHA-256;
- monotonic frame timestamps and indices;
- explicit target visibility and truth geometry;
- explicit observation availability rather than synthetic zero-fill;
- frame-path traversal protection and hash verification;
- deterministic non-authoritative fixtures;
- raw Gazebo camera capture;
- explicit camera world-pose provenance;
- tests and CI evidence-role assertions;
- descriptive analysis machinery with no Phase 9 resemblance threshold declared yet.

The software/fixture path is green in CI. Genuine-camera evidence remains a revalidation target because two independent issues were found before a scientific Phase 9 result was accepted:

1. a predeclared ULog completeness requirement was not met by an earlier preserved run;
2. a later provenance audit showed the collector was treating a fixed local camera-link transform as a world pose.

The second issue is corrected in the implementation by composing the model world pose with the link transform and failing closed when either component is unavailable. A fresh artifact must demonstrate the corrected behavior before the unchanged preregistered analyzer is interpreted.

No Phase 9 scientific resemblance or safety result is claimed from the rejected attempts.

---

## Reproducibility and research integrity

The project uses or records, depending on phase:

- deterministic top-level seeds;
- paired architecture and paired-plant comparisons;
- isolated environment/image/reference/fault/dynamics RNG streams;
- separate calibration, development, and held-out seeds;
- explicit freeze protocols before held-out evaluation;
- 95% Wilson intervals and paired rescue/regression counts;
- retained negative and intermediate results;
- permanent compressed archives of frozen Phase 6B raw evidence;
- exact Git SHAs for audited/frozen boundaries;
- machine-readable configuration metadata;
- SHA-256 result manifests;
- raw external-simulator evidence;
- exact PX4 version/source SHA;
- raw camera bytes and per-frame hashes in Phase 9;
- CI checks protecting historical/frozen paths.

The main rule is simple: a favorable number is less valuable than an evidence trail that another person can inspect and reproduce.

### Local software verification

```bash
git clone https://github.com/suhaslord/uav-safety-research.git
cd uav-safety-research
git checkout phase9-external-perception-validation
python -m venv .venv
pip install -e ".[dev]"
bash scripts/final_prototype_smoke.sh
```

The final-prototype smoke test compiles the Python sources, runs the full regression suite, generates the deterministic non-authoritative Phase 9 fixture, verifies every raw fixture-frame SHA-256, and checks the fixture evidence-role boundaries. It does **not** substitute for genuine-camera evidence or physical validation.

Historical experiment commands and frozen protocols are kept in the phase-specific documentation rather than presented as current safety guidance.

---

## Current limitations

The project should be read with these constraints in mind:

- **simulation only; no physical-flight validation**;
- internal plant models remain simplified relative to a full aircraft;
- synthetic image degradation is not a calibrated real-camera model;
- Phase 7 cells are small development samples and not safety-rate estimates;
- Phase 8 is one short PX4/Gazebo external-simulator comparison, not broad multi-scenario validation;
- Phase 8 produced a genuine overall `diagnostic_mismatch`;
- the Phase 8 run did not provide image/visual-odometry evidence;
- an earlier Phase 9 genuine-camera attempt failed its predeclared evidence-completeness gate before analysis;
- a separate Phase 9 camera-pose provenance defect was found and corrected, but the correction still requires fresh genuine-camera evidence before scientific interpretation;
- the first valid Phase 9 external camera trace will be seen evidence, not a hidden holdout;
- PX4 local-position outputs are estimator products and are not statistically independent of every aiding source;
- passing CI or a simulator test does not imply safety acceptance for a physical UAV.

---

## Evidence and paper workspace

- [Final prototype readiness](docs/final_prototype_readiness.md)
- [Research checkpoint — 2026-08-10](docs/research_checkpoint_2026-08-10.md)
- [External review packet](docs/external_review_packet.md)
- [Phase 6B results](docs/phase6b_results.md)
- [Phase 6B calibration revision](docs/phase6b_calibration_revision.md)
- [Phase 6B evaluation protocol](docs/phase6b_evaluation_protocol.md)
- [Phase 6B freeze manifest](docs/phase6b_freeze_manifest.md)
- [Phase 7 external-validity plan](docs/phase7_external_validity_plan.md)
- [Phase 8 trace-validation protocol](docs/phase8_trace_validation.md)
- [Phase 9 external-perception protocol](docs/phase9_external_perception_protocol.md)
- [Paper abstract workspace](paper/abstract.md)

---

## Safety scope

**AegisLand is not validated flight-control software.**

It is a simulation-only research project. It has not been validated for physical aircraft and should not be used to operate one.

---

## Author

**Suhas Beemineni**  
River Islands High School

Interested in aerospace engineering, autonomous systems, AI reliability, computational engineering, and research.

Technical criticism, methodology review, and reproducibility feedback are welcome.
