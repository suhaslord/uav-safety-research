<div align="center">

# AegisLand

### Confidence-Aware Redundant Perception for Simulated Autonomous UAV Landing

> **When vision is internally consistent but wrong, can independent evidence expose the error without making the system unusably conservative?**

[![CI](https://github.com/suhaslord/uav-safety-research/actions/workflows/ci.yml/badge.svg)](https://github.com/suhaslord/uav-safety-research/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Phase 10](https://img.shields.io/badge/Phase%2010-frozen%20mixed%20result-blue)
![Phase 10R](https://img.shields.io/badge/Phase%2010R-P0%20forensics-orange)
![Scope](https://img.shields.io/badge/scope-simulation--only-blueviolet)
![Safety](https://img.shields.io/badge/safety%20acceptance-false-red)
![License](https://img.shields.io/badge/license-MIT-green)

**A reproducible simulation research program on perception bias, calibrated abstention, redundant estimation, external-model mismatch, raw-camera geometry, temporal metric estimation, uncertainty calibration, and distribution shift.**

**Live research archive:** https://aegisland-research-cockpit.vercel.app/

</div>

---

## Current frontier

AegisLand has reached **Phase 10R P0**. The frozen Phase 10 result is preserved exactly as a mixed result, and the next revision begins with read-only forensic analysis and responsive-archive hardening rather than post-hoc tuning.

Current research branch:

`phase10r1-p0-forensics-infrastructure`

Current Phase 10R P0 head before this documentation update:

`908623d38e500a238097c1af31c8558e34dc606a`

That head passed the repository CI workflow. Phase 10R remains **simulation only**, `safety_acceptance = false`, and `controller_tuning_allowed = false`.

### Evidence chain

| Evidence layer | Status | What it supports |
|---|---|---|
| Phase 6B synthetic landing | **frozen held-out** | result for the defined synthetic benchmark |
| Phase 7 stress factorial | **audited development / seen** | failure discovery under stronger assumptions |
| Phase 8 PX4/Gazebo trace | **external simulator seen** | frozen resemblance diagnostic = `diagnostic_mismatch` |
| Phase 9 valid Gazebo camera trace | **external perception seen** | descriptive camera detection and geometry evidence |
| Phase 10 frozen challenge | **frozen holdout complete** | temporal metric estimator + calibrated uncertainty result |
| Phase 10R P0 | **seen-history forensics only** | failure decomposition, archive refactor, preregistration draft |
| Physical aircraft | **not tested** | no claim |

**Nothing in this repository is a physical-flight safety acceptance.**

---

## Phase 10 — frozen temporal metric perception

Phase 10 is developed on top of the Phase 9 camera evidence path and is intentionally preserved as a frozen scientific result.

Frozen Phase 10 branch:

`phase10-temporal-metric-perception`

Current public Phase 10 archive commit:

`51ecc8cb12892714e2ba81c6028b62aea93dd7a7`

Frozen implementation:

`fb928d5b0d1fbee7459d55120d5fd6b232a4f2c6`

Frozen evaluation:

- workflow run: `31565714654`
- artifact ID: `9129527772`
- artifact digest: `sha256:ca47dd023ebb295c7318d5907ad725a88d3721c8f6d855d4490af9b77c7ee88d`
- evidence role: `phase10_holdout_unseen`
- 65 raw camera frames
- 20 truth-visible frames
- 15 front-end observations on visible frames
- 5 missed truth-visible frames
- 0 false-positive observations
- 15 ArUco / 0 accepted quad-fallback observations

### Frozen point-estimate result

The preregistered substantial point-error improvement gate **did not pass**.

On the paired holdout observations, Phase 9 was already centimeter-accurate on the ArUco-only geometry, so AegisT10 matched rather than materially improved the point estimates:

| Metric | Phase 9 | AegisT10 |
|---|---:|---:|
| lateral MAE | 0.0277 m | 0.0277 m |
| altitude MAE | 0.0157 m | 0.0157 m |
| lateral p95 | 0.0559 m | 0.0559 m |
| altitude p95 | 0.0293 m | 0.0293 m |

### Frozen uncertainty result

The uncertainty behavior improved substantially on the same paired rows:

- Phase 9 median `|lateral residual| / sigma`: **13.17**
- AegisT10 median normalized lateral residual: **0.646**
- Phase 9 median `|altitude residual| / sigma`: **5.11**
- AegisT10 median normalized altitude residual: **0.521**
- AegisT10 2-sigma coverage: **93.3% lateral / 100% altitude**

The negative/mixed result remains part of the record. No estimator threshold, model parameter, calibration value, or holdout definition was retuned after exposure.

Primary Phase 10 documents:

- [Phase 10 protocol](docs/phase10_temporal_metric_protocol.md)
- [Phase 10 frozen result](docs/phase10_frozen_result.md)
- [Phase 10 freeze manifest](docs/phase10_freeze_manifest.json)
- [Research archive](dashboard/phases/phase.html)

---

## Phase 10R P0 — read-only forensics and research infrastructure

Phase 10R does **not** rewrite frozen Phase 10. The existing Phase 10 holdout is now permanently treated as **seen historical evidence** for the revision.

Draft PR: **#18 — Phase 10R P0: holdout forensics, archive refactor, preregistration**

P0 adds:

- a read-only forensic analyzer for the already-exposed frozen Phase 10 holdout;
- a truth-visible per-frame forensic table and report;
- a canonical responsive archive layer replacing stacked compatibility CSS patches;
- regression tests for the responsive archive architecture;
- a Phase 10R preregistration draft.

### Descriptive finding only

The five truth-visible misses are frames **27, 35, 36, 46, and 47**. Four of the five have a descriptive projected-footprint edge-margin ratio below 1.0 and the fifth is near-boundary.

That observation is **not a tuning rule**. It only motivates preregistering edge/partial-view conditions in new development evidence.

### Hard boundary before the next experiment

The Phase 10R preregistration remains pending approval. Until that gate is recorded:

- no detector threshold selection from the five misses;
- no pose-parameter selection from the five misses;
- no temporal-filter tuning from the five misses;
- no calibration fitting from the five misses;
- no challenge-development data generation;
- no Phase 10R model selection.

Start here:

- [Phase 10R preregistration draft](docs/phase10r_preregistration.md)
- [Phase 10 frozen-holdout forensic report](docs/phase10_frozen_holdout_forensics.md)
- [Phase 10R P0 analyzer](scripts/analyze_phase10_frozen_holdout.py)

---

## Research lineage

| Stage | Main idea | Main lesson |
|---|---|---|
| Baseline | trust primary estimate | severe bias can remain dangerous |
| V1 / Phase 1 | fixed confidence/risk thresholds | safety can improve mainly by becoming too conservative |
| V2 / Phase 2 | temporal smoothing/persistence | availability improves, but persistent single-stream bias remains difficult |
| V3 / Phase 3 | independent redundant estimate | independent error structure can expose persistent bias in abstract simulation |
| Phase 4 | intentional archive gap | no distinct experimental Phase 4 is invented |
| Phase 5 | robustness sweeps | reference quality and distribution shift matter |
| Phase 6 | synthetic pixel sequences | image perception adds tracking, calibration, and observability failures |
| Phase 6B | component confidence + selective fusion | unreliable altitude can be rejected without discarding useful lateral information |
| Phase 7 | external-validity stress | timing, common-mode faults, and stronger dynamics expose weak cells |
| Phase 8 | frozen external-trace comparison | the internal surrogate mismatched several PX4/Gazebo distributions |
| Phase 9 | genuine raw camera evidence | strong detection on one trace can coexist with poor metric geometry |
| Phase 10 | temporal metric estimator + uncertainty calibration | uncertainty improved while the preregistered point-error win did not materialize |
| Phase 10R | perception-generalization revision | analyze seen failures read-only, then test new preregistered evidence |

---

## Reproducibility

For the current Phase 10R P0 branch:

```bash
git clone https://github.com/suhaslord/uav-safety-research.git
cd uav-safety-research
git checkout phase10r1-p0-forensics-infrastructure
python -m venv .venv
pip install -e ".[dev]"
pytest
```

The repository preserves deterministic seeds, frozen heads, evidence roles, machine-readable metadata, SHA-256 manifests, raw-simulator provenance, and unfavorable outcomes rather than silently tuning them away.

---

## Current limitations

- **Simulation only; no physical-flight validation.**
- No hardware-camera validation.
- Internal plant models remain simplified relative to a full aircraft.
- Synthetic image degradation is not a calibrated real-camera model.
- Phase 7 cells are small development samples, not safety-rate estimates.
- Phase 8 is one short external-simulator trace and produced a genuine `diagnostic_mismatch`.
- Phase 9 is one short seen downward-camera trace.
- Phase 10 frozen holdout contains only 20 truth-visible frames and 15 paired observations.
- The current Phase 10 holdout is now seen evidence and cannot be reused as a new hidden test for Phase 10R.
- Passing CI or simulator tests does not imply safety acceptance for a physical UAV.

---

## AIEA research pathway

AegisLand is also connected to an AIEA/UCSC research-pathway package on `main`, including a simulator-onboarding deliverable and research-track proposal. That documentation is organizational/research-planning material and does not change the frozen Phase 10 scientific result.

---

## Safety scope

**AegisLand is not validated flight-control software.**

It is a simulation-only research project. It has not been validated for physical aircraft and should not be used to operate one.

---

## Author

**Suhas Beemineni**  
River Islands High School

Interested in aerospace engineering, autonomous systems, AI reliability, computational engineering, and reproducible research.

Technical criticism, methodology review, and reproducibility feedback are welcome.
