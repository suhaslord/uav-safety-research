<div align="center">

<img src="docs/assets/readme/banner.svg" alt="AegisLand research banner" width="100%"/>

### When vision looks right — and still is wrong

[![CI](https://github.com/suhaslord/uav-safety-research/actions/workflows/ci.yml/badge.svg)](https://github.com/suhaslord/uav-safety-research/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Frontier](https://img.shields.io/badge/frontier-Phase%2010R%20P0-0A7A72)
![Phase 10](https://img.shields.io/badge/Phase%2010-frozen%20mixed%20result-1F4E79)
![Scope](https://img.shields.io/badge/scope-simulation%20only-5B4B8A)
![Safety](https://img.shields.io/badge/safety%20acceptance-false-B42318)
![License](https://img.shields.io/badge/license-MIT-2F6F4E)

**A simulation research program on perception overconfidence, calibrated abstention, redundant estimation, and the limits of those ideas under real simulator evidence.**

> If visual perception is internally consistent but systematically wrong, can independent evidence expose the error without making landing unusably conservative?

<br/>

[![Open live archive](https://img.shields.io/badge/Live%20archive-aegisland--research--cockpit-2DD4BF?style=for-the-badge&logo=vercel&logoColor=white)](https://aegisland-research-cockpit.vercel.app/)

[Protocol](docs/phase10_temporal_metric_perception_protocol.md)
·
[Frozen Phase 10 result](docs/phase10_frozen_holdout_result.md)
·
[Phase 10R gate](docs/phase10r_preregistration.md)
·
[Forensics](docs/phase10r_holdout_forensics.md)

</div>

---

## Visual tour

| | |
|:---:|:---:|
| <img src="docs/assets/readme/aruco_motif.svg" alt="ArUco landing target motif" width="420"/> | <img src="docs/assets/readme/perception_stack.svg" alt="Perception stack diagram" width="520"/> |
| **Landing-target motif** used across the Gazebo camera path | **Current stack** from raw camera → freeze gates |

<img src="docs/assets/readme/evidence_ladder.svg" alt="Evidence ladder from Phase 6B through Phase 10R" width="100%"/>

---

## Headline result — Phase 10 frozen holdout

Phase 10 froze a **mixed** Gazebo-camera result and left it alone.

<img src="docs/assets/readme/phase10_uncertainty_honesty.png" alt="Uncertainty honesty chart comparing Phase 9 and AegisT10" width="100%"/>

<img src="docs/assets/readme/phase10_point_estimates.png" alt="Point estimate errors in centimeters" width="100%"/>

<img src="docs/assets/readme/phase10_gate_scorecard.svg" alt="Phase 10 passed and failed gate scorecard" width="100%"/>

| Metric | Phase 9 | AegisT10 | Gate |
|---|---:|---:|:---|
| Lateral MAE | **2.77 cm** | **2.77 cm** | point-error win **failed** |
| Altitude MAE | **1.57 cm** | **1.57 cm** | point-error win **failed** |
| Median \|residual\| / σ (lateral) | 13.17 | **0.65** | uncertainty honesty **improved** |
| Median \|residual\| / σ (altitude) | 5.11 | **0.52** | uncertainty honesty **improved** |
| 2σ coverage | — | **93% / 100%** | calibrated uncertainty held |

### Why the temporal point-error win did not transfer

<img src="docs/assets/readme/phase10_holdout_composition.png" alt="Holdout composition pie and detector mix" width="100%"/>

The holdout produced **15/15 ArUco** observations and **0** quad-fallback cases. Phase 9 geometry was already centimeter-accurate there, so temporal filtering had nothing catastrophic to rescue. The development win did not transfer — and that finding stayed in the record.

<img src="docs/assets/readme/phase10_coverage.png" alt="Uncertainty coverage bars for AegisT10" width="100%"/>

<details>
<summary><strong>Holdout provenance</strong></summary>

<br/>

- Evidence role: `phase10_holdout_unseen` → now historical for Phase 10R
- 65 raw frames · 20 truth-visible · 15 observations · 5 misses · 0 false positives
- Frozen implementation: `fb928d5b0d1fbee7459d55120d5fd6b232a4f2c6`
- Artifact digest: `sha256:ca47dd023ebb295c7318d5907ad725a88d3721c8f6d855d4490af9b77c7ee88d`
- Full write-up: [`docs/phase10_frozen_holdout_result.md`](docs/phase10_frozen_holdout_result.md)

</details>

---

## Phase 10R P0 — forensics without retuning

<img src="docs/assets/readme/miss_forensics.svg" alt="Read-only miss forensics visualization" width="100%"/>

```mermaid
flowchart LR
  A["Phase 10 frozen<br/>mixed holdout"] --> B["P0 read-only<br/>forensics"]
  B --> C["Preregistration draft"]
  C --> D{"User approval?"}
  D -->|no| E["Stop · no data gen<br/>no tuning"]
  D -->|yes| F["New challenge set<br/>development / validation"]
  F --> G["Later freeze gate<br/>new holdout once"]
  style A fill:#0B1220,stroke:#2DD4BF,color:#E8EEF7
  style B fill:#0B1220,stroke:#F59E0B,color:#E8EEF7
  style C fill:#0B1220,stroke:#38BDF8,color:#E8EEF7
  style E fill:#0B1220,stroke:#FB7185,color:#E8EEF7
  style G fill:#0B1220,stroke:#34D399,color:#E8EEF7
```

Until [`docs/phase10r_preregistration.md`](docs/phase10r_preregistration.md) is explicitly approved:

- no detector / pose / filter / calibration selection from miss frames `27, 35, 36, 46, 47`
- no challenge-development data generation
- no Phase 10R model selection

| Start here | Role |
|---|---|
| [Phase 10R preregistration](docs/phase10r_preregistration.md) | approval gate |
| [Holdout forensics](docs/phase10r_holdout_forensics.md) | read-only analysis |
| [Forensic analyzer](scripts/analyze_phase10_frozen_holdout.py) | hash-verified replay |
| [Live archive](https://aegisland-research-cockpit.vercel.app/) | visual case studies |

Current research branch: `phase10r1-p0-forensics-infrastructure`

---

## Earlier frozen milestones

### Phase 6B — selective confidence on synthetic landings

<img src="docs/assets/readme/phase6b_mixed_stack.png" alt="Phase 6B mixed success versus unsafe stacked bars" width="100%"/>

```mermaid
flowchart LR
  I["Synthetic camera"] --> P["Pixel estimator"]
  P --> T["Temporal track"]
  P --> C["Component confidence"]
  C --> X["p_x_good"]
  C --> Z["p_z_good + observability"]
  R["Surrogate reference"] --> F["Selective fusion"]
  X --> F
  Z --> F
  T --> F
  F --> S["Frozen supervisor"]
  S --> L["Landing controller"]
```

On mixed degradation (held-out): image-only **57% / 43%** unsafe → Phase 6B **99% / 1%** unsafe. Low-light kept a deliberate **3% timeout** cost.

### V3 — abstract redundant perception

<img src="docs/assets/readme/v3_mixed_unsafe.png" alt="V3 mixed unsafe touchdown rate comparison" width="100%"/>

<p align="center">
  <img src="results/v3_frozen/unsafe_touchdown_rate.png" alt="V3 frozen unsafe touchdown rates by profile" width="48%"/>
  <img src="results/v3_frozen/success_rate.png" alt="V3 frozen success rates by profile" width="48%"/>
</p>

<p align="center">
  <img src="results/threshold_sweep/safety_availability_frontier.png" alt="Safety availability frontier from threshold sweep" width="70%"/>
</p>

---

## Evidence chain

| Layer | Status | Supports |
|---|---|---|
| Phase 6B synthetic landing | **frozen held-out** | selective confidence on the defined synthetic benchmark |
| Phase 7 external-validity stress | **audited / seen** | where redundancy assumptions break |
| Phase 8 PX4/Gazebo traces | **external seen** | surrogate resemblance = `diagnostic_mismatch` |
| Phase 9 Gazebo camera | **external perception seen** | detection can look strong while metric geometry fails |
| Phase 10 temporal metric | **frozen holdout** | uncertainty improved; point-error gate failed |
| Phase 10R P0 | **forensics only** | miss decomposition + preregistration draft |
| Physical aircraft | **not tested** | no claim |

**Nothing here is a physical-flight safety acceptance.**  
`safety_acceptance = false` · `controller_tuning_allowed = false` · simulation only.

---

## Research lineage

| Stage | Idea | Lesson |
|---|---|---|
| V1 | fixed risk thresholds | safety via over-abort |
| V2 | temporal persistence | availability returns; single-stream bias remains |
| V3 | imperfect independent reference | independent error structure can expose persistent bias |
| Phase 5 | robustness sweeps | reference quality matters |
| Phase 6 / 6B | synthetic pixels + component confidence | reject bad altitude without discarding useful lateral cues |
| Phase 7–8 | assumption stress + external traces | common-mode faults and surrogate mismatch are first-class findings |
| Phase 9 | raw Gazebo camera | strong detection ≠ trustworthy metric geometry |
| Phase 10 | temporal metric + calibrated σ | honesty improved; preregistered point-error win failed |
| Phase 10R | generalization revision | forensics first, then new preregistered evidence |

---

## Quickstart

```bash
git clone https://github.com/suhaslord/uav-safety-research.git
cd uav-safety-research
git checkout phase10r1-p0-forensics-infrastructure
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

```bash
python scripts/serve_dashboard.py
# → http://127.0.0.1:8765
```

Or open the hosted archive: [aegisland-research-cockpit.vercel.app](https://aegisland-research-cockpit.vercel.app/)

---

## Limitations

- Simulation only — **no** hardware-camera or physical-flight validation
- Phase 10 holdout is small: **20** truth-visible frames, **15** paired observations
- That holdout is now **seen** and cannot be a hidden Phase 10R test
- Phase 7 cells are development samples, not safety-rate estimates
- Phase 8 produced a genuine `diagnostic_mismatch` on a short external trace
- Passing CI does not imply UAV safety acceptance

---

## Safety scope

**AegisLand is not validated flight-control software.**

It is an educational, simulation-only research project. It must not be used to operate a physical aircraft.

---

<div align="center">

**Suhas Beemineni** · River Islands High School

Aerospace · autonomous systems · AI reliability · reproducible research

Technical criticism and methodology review are welcome.

</div>
