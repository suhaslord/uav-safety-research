<div align="center">

# AegisLand

### Confidence-Aware Redundant Perception for Simulated Autonomous UAV Landing

> **When vision is internally consistent but wrong, can independent evidence reveal the error without making the system unusably conservative?**

[![CI](https://github.com/suhaslord/uav-safety-research/actions/workflows/ci.yml/badge.svg)](https://github.com/suhaslord/uav-safety-research/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Phase 6B](https://img.shields.io/badge/Phase%206B-frozen-success)
![Phase 8](https://img.shields.io/badge/Phase%208-external%20mismatch-orange)
![Phase 9](https://img.shields.io/badge/Phase%209-valid%20seen%20camera%20trace-blue)
![Scope](https://img.shields.io/badge/scope-simulation--only-blueviolet)
![License](https://img.shields.io/badge/license-MIT-green)

**A reproducible simulation study of persistent perception bias, calibrated abstention, redundant estimation, external-model mismatch, and the limits of those conclusions under distribution shift.**

</div>

---

## Current status

AegisLand is now an **audited research-prototype candidate**. The code, deterministic fixtures, raw-evidence provenance path, and the first valid PX4/Gazebo downward-camera analysis are working end to end. The scientific findings are intentionally mixed rather than optimized into one favorable number.

The key evidence chain is:

| Evidence layer | Status | What it supports |
|---|---|---|
| Phase 6B synthetic landing | **frozen held-out** | result for the defined synthetic benchmark |
| Phase 7 stress factorial | **audited development / seen** | failure discovery under stronger assumptions |
| Phase 8 PX4/Gazebo trace | **external simulator seen** | frozen resemblance diagnostic = `diagnostic_mismatch` |
| Phase 9 deterministic camera fixture | **pipeline validation only** | schema/hash/provenance software works |
| Phase 9 valid Gazebo camera trace | **external perception seen** | descriptive detection/localization/geometry evidence for one simulator trace |
| Physical aircraft | **not tested** | no claim |

**Nothing in this repository is a physical-flight safety acceptance.**

Start with:

- **[Phase 9 valid camera result](docs/phase9_gazebo_camera_seen_result.md)**
- **[Final prototype readiness](docs/final_prototype_readiness.md)**
- **[External review packet](docs/external_review_packet.md)**
- [Phase 9 preregistered protocol](docs/phase9_external_perception_protocol.md)
- [Research checkpoint / historical audit](docs/research_checkpoint_2026-08-10.md)

---

## What the project is testing

AegisLand asks whether an autonomous landing stack can recognize when a primary visual estimate is confidently wrong by combining:

- component-wise confidence rather than one global confidence score;
- selective rejection/abstention;
- an independent reference estimate;
- temporal and fault-stress testing;
- explicit external-simulator comparison;
- raw-camera evidence with provenance and hash verification.

The project evolved by preserving failures instead of deleting them when later evidence became less favorable.

| Stage | Main idea | Main lesson |
|---|---|---|
| Baseline | trust primary estimate | severe bias can remain dangerous |
| V1 | fixed confidence/risk thresholds | safety can improve mainly by becoming too conservative |
| V2 | temporal smoothing/persistence | availability improves, but persistent single-stream bias remains difficult |
| V3 | independent redundant estimate | independent error structure can expose persistent bias in abstract simulation |
| Phase 5 | robustness sweeps | reference quality and distribution shift matter |
| Phase 6 | synthetic pixel sequences | image perception adds tracking/calibration/observability failures |
| Phase 6B | component confidence + selective fusion | unreliable altitude can be rejected without discarding useful lateral information |
| Phase 7 | external-validity stress | timing, common-mode faults, and stronger dynamics expose weak cells |
| Phase 8 | frozen external-trace comparison | the internal surrogate does not closely resemble several PX4/Gazebo distributions |
| Phase 9 | genuine raw camera evidence | strong detection on one trace can coexist with poor metric geometry |

---

## Phase 6B — frozen synthetic result

Frozen head:

`b4e9838555e935a5ec42690495315473629b58f6`

Frozen component-confidence gates:

- lateral: `0.80`
- altitude: `0.80`

The held-out landing seed `868686` produced 1,500 paired simulated landing episodes across five image conditions and three architectures.

| Condition | Image-only success / unsafe | Original Phase 6 Aegis | Phase 6B success / unsafe | Phase 6B timeout |
|---|---:|---:|---:|---:|
| clean | 100% / 0% | 100% / 0% | **100% / 0%** | 0% |
| blur | 100% / 0% | 100% / 0% | **100% / 0%** | 0% |
| low light | 100% / 0% | 100% / 0% | **97% / 0%** | **3%** |
| occlusion | 86% / 14% | 93% / 7% | **96% / 4%** | 0% |
| mixed | 57% / 43% | 94% / 6% | **99% / 1%** | 0% |

A separate held-out selective-perception seed `878787` evaluated 10,000 synthetic frames at the unchanged `0.80 / 0.80` gates. The low-light timeout and mixed-condition lateral-selectivity weaknesses are retained.

This is evidence about the defined synthetic environment, not a real-aircraft rate.

---

## Phase 7 — attack the assumptions

Audited development head:

`7354eeda8b975f45b659ce4f3f86c82501e6321d`

Phase 7 added separated sensor roles, mismatched rates, latency, dropout, stale-state uncertainty growth, bias drift, common-mode faults, and stronger plant dynamics.

Its paired factorial contains 200 development episodes across 40 cells, only five episodes per cell. It is therefore **failure-discovery evidence**, not a precise safety-rate estimate. Several stronger-plant/common-mode cells remained weak, and those failures were preserved rather than used to retune the frozen Phase 6B gates.

The dependency-free Research Cockpit under [`dashboard/`](dashboard/) is an analysis interface for these results, not a vehicle-control UI.

---

## Phase 8 — genuine PX4/Gazebo model mismatch

Frozen comparison head:

`bd62e3b31431306fd9d897f560be7325d711d21a`

Audited PX4/Gazebo evidence head:

`b9df03e111f3a796e50df440becc587c48ee7643`

PX4 `v1.17.0` source SHA:

`d6f12ad1c4f70ad3230afd7d86e971421e02fef4`

The frozen trace-resemblance method compared empirical distributions and temporal structure without retuning after seeing the external trace. Its genuine PX4/Gazebo result was:

- overall: **`diagnostic_mismatch`**
- close: **1**
- watch: **2**
- mismatch: **9**
- insufficient: **14**
- `safety_acceptance = false`
- `controller_tuning_allowed = false`

The correct interpretation is negative but useful: several internal surrogate navigation/timing distributions did **not** closely reproduce the PX4/Gazebo evidence.

---

## Phase 9 — valid genuine camera trace

Earlier Phase 9 attempts were deliberately rejected before scientific interpretation. One failed the unchanged 20.0 s ground-truth completeness gate. A later audit discovered a separate provenance bug: a fixed local `camera_link` transform was being treated as though it were a moving world pose.

That implementation bug was corrected at:

`fae622cfa448e4945174e8c03982686c7b1b0e3a`

The detector, target-visibility definition, descriptive metrics, Phase 8 logic, and Phase 6B logic were **not** changed to make the rerun pass.

### Exact valid evidence

- evidence head: `33c5c73768757b508f5c613b2fba73f94e3fd5a6`
- workflow run: `31523496671`
- artifact ID: `9114281248`
- artifact digest: `sha256:bd2387f9518c7feb0bb5b8d7d02ccc7cbf416a73cd13e150ebeab06551b041a6`
- selected raw frames: **68**
- analyzed pose-linked frames: **67**
- independently reverified raw-frame hashes: **67 / 67**
- ULog ground-truth coverage: **1,237 samples / 24.684 s**
- trace duration: **21.78 s**
- evidence role: **`external_perception_seen`**
- Phase 9 acceptance threshold: **none declared**
- resemblance verdict: **none declared**
- safety acceptance: **false**

The frozen analyzer file is byte-identical between implementation head `353bf45bc8dcad5c7875570b91011d062014ab59` and the successful evidence head.

### Detection result

Under the preregistered truth-visibility definition:

- true positives: **25**
- false negatives: **0**
- false positives: **0**
- true negatives: **42**
- ArUco detections: **18**
- fixed quad-fallback detections: **7**

These are descriptive counts from one **seen** trace, not a general detector rate.

### The important negative result: geometry is weak

For the 25 paired truth-visible/detected frames:

- pixel-center MAE: **40.99 px**
- pixel-center p95 error: **113.80 px**
- lateral MAE: **0.998 m**
- lateral p95 absolute error: **5.087 m**
- altitude MAE: **1.520 m**
- altitude p95 absolute error: **6.597 m**
- median `|lateral residual| / sigma`: **8.11**
- median `|altitude residual| / sigma`: **5.89**

So the camera detector found the target reliably on this trace, but the PnP-derived metric geometry was not correspondingly accurate and its uncertainty proxies were under-dispersed. **Detection availability is not the same thing as accurate localization or safe landing.**

A direct Phase 7 KS/Wasserstein comparison is intentionally withheld because the Phase 7 state-level lateral axis and the Phase 9 camera optical-horizontal error are not directly compatible.

Full result and provenance: [`docs/phase9_gazebo_camera_seen_result.md`](docs/phase9_gazebo_camera_seen_result.md).

---

## Reproducibility

Local software/fixture verification:

```bash
git clone https://github.com/suhaslord/uav-safety-research.git
cd uav-safety-research
git checkout phase9-external-perception-validation
python -m venv .venv
pip install -e ".[dev]"
bash scripts/final_prototype_smoke.sh
```

The smoke test compiles Python sources, runs the full test suite, generates the deterministic non-authoritative Phase 9 fixture, verifies every raw fixture-frame SHA-256, and checks evidence-role boundaries.

A passing smoke test does not substitute for the genuine-camera artifact and does not establish physical safety.

The research audit trail includes deterministic seeds, separate development/calibration/held-out roles where applicable, frozen heads, machine-readable metadata, SHA-256 manifests, exact PX4 source identity, preserved negative results, and raw external-simulator evidence.

---

## Current limitations

- **Simulation only; no physical-flight validation.**
- No hardware-camera validation.
- Internal plant models remain simplified relative to a full aircraft.
- Synthetic image degradation is not a calibrated real-camera model.
- Phase 7 cells are small development samples, not safety-rate estimates.
- Phase 8 is one short external-simulator trace and produced a genuine `diagnostic_mismatch`.
- Phase 9 is one short **seen** downward-camera trace, not a hidden holdout.
- Only 25 paired truth-visible/detected samples drive the Phase 9 geometry metrics.
- The fiducial/quad task is simpler than broad real-world landing perception.
- Phase 9 pose association uses the latest received pose; measured median association offset was about 63 ms and p95 about 110 ms.
- Phase 9 geometric uncertainty proxies are not calibrated guarantees and were too small relative to observed residuals.
- Passing CI or simulator tests does not imply safety acceptance for a physical UAV.

---

## Evidence workspace

- [Phase 9 valid camera result](docs/phase9_gazebo_camera_seen_result.md)
- [Final prototype readiness](docs/final_prototype_readiness.md)
- [External review packet](docs/external_review_packet.md)
- [Research checkpoint — 2026-08-10](docs/research_checkpoint_2026-08-10.md)
- [Phase 6B results](docs/phase6b_results.md)
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
