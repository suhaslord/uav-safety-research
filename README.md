<div align="center">

# AegisLand

**External perception evidence you can inspect — not just trust.**

[![CI](https://github.com/suhaslord/uav-safety-research/actions/workflows/ci.yml/badge.svg)](https://github.com/suhaslord/uav-safety-research/actions/workflows/ci.yml)
![Frontier](https://img.shields.io/badge/frontier-Phase%2010R%20P0-2F6FED)
![Phase 10](https://img.shields.io/badge/Phase%2010-frozen%20mixed%20result-111111)
![Safety](https://img.shields.io/badge/safety%20acceptance-false-C2410C)
![Scope](https://img.shields.io/badge/simulation%20only-6B7280)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)

Simulation research on perception overconfidence, calibrated abstention, redundant estimation, and what those claims mean after PX4/Gazebo camera evidence.

<br/>

[![Open the live research archive](https://img.shields.io/badge/Open%20live%20archive-aegisland--research--cockpit-2F6FED?style=for-the-badge&logo=vercel&logoColor=white)](https://aegisland-research-cockpit.vercel.app/)

</div>

<br/>

<a href="https://aegisland-research-cockpit.vercel.app/">
  <img src="docs/assets/readme/frame_home.png" alt="AegisLand research cockpit homepage" width="100%"/>
</a>

<p align="center"><sub>Live cockpit · Phase 9/10 evidence path · <code>safety_acceptance = false</code></sub></p>

---

## The product is the archive

AegisLand is not a “landing demo.” It is a **phase-by-phase research archive** with frozen results, mismatches, and negative findings kept visible.

<a href="https://aegisland-research-cockpit.vercel.app/phases/">
  <img src="docs/assets/readme/frame_phases.png" alt="Complete research lineage archive page" width="100%"/>
</a>

<p align="center"><sub>Every phase. Nothing rewritten.</sub></p>

<p align="center">
  <img src="docs/assets/readme/collage_desktop_mobile.png" alt="Desktop and mobile archive views" width="100%"/>
</p>

<p align="center"><sub>Desktop cockpit + mobile archive shell</sub></p>

---

## Current frontier — Phase 10 / 10R

<a href="https://aegisland-research-cockpit.vercel.app/phases/phase10/">
  <img src="docs/assets/readme/frame_phase10.png" alt="Phase 10 AegisT10 case study hero" width="100%"/>
</a>

**Research question**

> If visual perception is internally consistent but systematically wrong, can independent evidence expose the error without making landing unusably conservative?

### Frozen mixed result

AegisT10 **did not beat** Phase 9 point estimates on the holdout — because every usable observation was already clean ArUco geometry at centimeter scale. Uncertainty honesty improved sharply on the same rows.

<img src="docs/assets/readme/chart_uncertainty_light.png" alt="Uncertainty honesty: Phase 9 vs AegisT10" width="100%"/>

| | Phase 9 | AegisT10 |
|---|---:|---:|
| Lateral MAE | 2.77 cm | 2.77 cm |
| Altitude MAE | 1.57 cm | 1.57 cm |
| Median \|residual\| / σ (lateral) | 13.17 | **0.65** |
| Median \|residual\| / σ (altitude) | 5.11 | **0.52** |
| 2σ coverage | — | **93% / 100%** |

Holdout: 65 raw frames · 20 truth-visible · 15 observations · **15 ArUco / 0 quad-fallback** · 5 misses · 0 false positives.

Phase 10R P0 starts with **read-only forensics** and a preregistration draft. No tuning from the five miss frames until approval.

[Phase 10 result](docs/phase10_frozen_holdout_result.md) · [10R preregistration](docs/phase10r_preregistration.md) · [Forensics](docs/phase10r_holdout_forensics.md)

---

## Case studies in the archive

<table>
  <tr>
    <td width="50%">
      <a href="https://aegisland-research-cockpit.vercel.app/phases/phase9/">
        <img src="docs/assets/readme/frame_phase9.png" alt="Phase 9 case study"/>
      </a>
      <p align="center"><b>Phase 9</b><br/><sub>Raw Gazebo camera · detection vs metric geometry</sub></p>
    </td>
    <td width="50%">
      <a href="https://aegisland-research-cockpit.vercel.app/phases/phase6b/">
        <img src="docs/assets/readme/frame_phase6b.png" alt="Phase 6B case study"/>
      </a>
      <p align="center"><b>Phase 6B</b><br/><sub>Stop calling the whole image good or bad</sub></p>
    </td>
  </tr>
</table>

<img src="docs/assets/readme/chart_phase6b_light.png" alt="Phase 6B mixed success versus unsafe" width="100%"/>

<img src="docs/assets/readme/chart_v3_light.png" alt="V3 mixed unsafe touchdown rates" width="100%"/>

<p align="center">
  <img src="results/v3_frozen/unsafe_touchdown_rate.png" alt="V3 frozen unsafe rates by profile" width="48%"/>
  <img src="results/v3_frozen/success_rate.png" alt="V3 frozen success rates by profile" width="48%"/>
</p>

---

## Evidence ladder

| Layer | Status | What it supports |
|---|---|---|
| Phase 6B synthetic landing | **frozen held-out** | selective confidence on the defined benchmark |
| Phase 7 stress factorial | **audited / seen** | where redundancy assumptions break |
| Phase 8 PX4/Gazebo traces | **external seen** | surrogate resemblance = `diagnostic_mismatch` |
| Phase 9 Gazebo camera | **external perception seen** | strong detection ≠ trustworthy metric geometry |
| Phase 10 temporal + σ | **frozen holdout** | uncertainty improved; point-error gate failed |
| Phase 10R P0 | **forensics only** | miss decomposition + preregistration draft |
| Physical aircraft | **not tested** | no claim |

```mermaid
flowchart LR
  A["6B synthetic<br/>frozen"] --> B["7–8 stress<br/>+ mismatch"]
  B --> C["9 raw camera<br/>seen"]
  C --> D["10 temporal + σ<br/>frozen mixed"]
  D --> E["10R forensics<br/>pending approval"]
```

**Nothing in this repository is a physical-flight safety acceptance.**

---

## Quickstart

```bash
git clone https://github.com/suhaslord/uav-safety-research.git
cd uav-safety-research
git checkout phase10r1-p0-forensics-infrastructure
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
python scripts/serve_dashboard.py   # http://127.0.0.1:8765
```

Or open the hosted archive: **[aegisland-research-cockpit.vercel.app](https://aegisland-research-cockpit.vercel.app/)**

Regenerate README screenshots after UI changes:

```bash
python3 scripts/serve_dashboard.py &
node scripts/capture_readme_shots.mjs
```

---

## Limitations

- Simulation only — no hardware-camera or physical-flight validation
- Phase 10 holdout is small (**20** truth-visible / **15** paired observations)
- That holdout is now **seen** for Phase 10R
- Phase 8 is a short external trace with a genuine `diagnostic_mismatch`
- Passing CI ≠ UAV safety acceptance

---

## Safety

**AegisLand is not validated flight-control software.** Educational / simulation-only. Do not use it to operate a physical aircraft.

---

<div align="center">

**Suhas Beemineni** · River Islands High School

Aerospace · autonomous systems · AI reliability · reproducible research

</div>
