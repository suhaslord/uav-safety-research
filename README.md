# AegisLand — UAV Safety Research

AegisLand is a **simulation-only UAV landing safety research project**.

The project asks a simple question:

> **When a landing camera becomes stale, degraded, or confidently wrong, can independent evidence and calibrated uncertainty reveal that failure before the system trusts it too much?**

The goal is not to prove that an aircraft is safe to fly. The goal is to build a careful experimental record showing **when a perception-and-uncertainty approach works, when it fails, and whether the result survives new evidence without retuning**.

**Live research cockpit:** https://aegisland-research-cockpit.vercel.app/

---

## What are we trying to answer?

### Main research question

Can a UAV landing system recognize when its visual position estimate should **not** be trusted, while still remaining useful enough to avoid unnecessary holds or aborts?

### The questions behind the project

1. **Safety supervision** — Can confidence and independent evidence stop unsafe landing decisions before touchdown?
2. **Perception robustness** — What happens when camera measurements become noisy, biased, ambiguous, or temporarily unavailable?
3. **External validity** — Do results that look strong in one simulation setting survive harder geometry, appearance, and simulator shifts?
4. **Uncertainty calibration** — Can uncertainty intervals stay honest without becoming so wide that the system is unusable?
5. **Latency** — What does stale perception do to position error, short-horizon residual error, and uncertainty behavior?
6. **Context effects** — Which predefined environmental factors explain why a method works better in simple scenes than difficult ones?
7. **Frozen transfer** — Can a simple model predict behavior in fresh synthetic contexts **without being refit after seeing them**?

The next meaningful research question is broader external validity: **does the same behavior transfer to a meaningfully different simulator, sensor model, or real recorded camera dataset while preserving the same evidence discipline?**

---

## Current result — frozen through Phase 22

The current scientific lineage is frozen through **Phase 22: Frozen Additive Context Transfer**.

Phase 22 asked:

> **Can a simple additive model predict a fresh 32-cell context surface without refitting?**

It passed development, transfer, protected validation, and the one-shot final holdout.

| Final Phase 22 check | Result |
|---|---:|
| RMSE-surface cellwise R² | **0.8319** |
| MAE-surface cellwise R² | **0.7744** |
| Stable-sign accuracy on eligible cells | **100%** |
| Locked gates | **10 / 10 PASS** |

Frozen identities:

- scientific head: `668d065714dde279857bc0e196f0ef7cc5e182ed`
- Phase 22 result SHA-256: `0ddc968b8bd48c2de6d904194b417854913389a8927cff0b15b96c6501f8294c`
- Phase 22 candidate SHA-256: `62e75d7b39088c2e66f1cc6be4d180501b79632f2f6847af1fbe0bd96be17551`

This does **not** mean every phase passed. Negative results are intentionally preserved. For example, the external-validity and paired-degradation studies in Phases 13A and 13B failed their locked criteria, and several latency hypotheses in Phases 14–18 also failed before later narrower questions succeeded.

That is part of the point of AegisLand: **a failed preregistered question stays failed instead of being rewritten after the result is known.**

---

## Research map

| Area | Phases | Main question |
|---|---|---|
| Safety architecture | 1–4 | Can confidence, temporal logic, and independent evidence prevent unsafe actions? |
| Perception + robustness | 5–6B | Does the architecture still work when the system must reason from degraded image-derived measurements? |
| External validation | 7–10R | How much of the apparent result depends on the simulator, camera geometry, and environmental shift? |
| Reliability + calibration | 11–13C | Can availability and uncertainty stay trustworthy under protected and harder-domain evidence? |
| Latency + error dynamics | 14–19 | What does stale perception change, and which latency effects actually replicate? |
| Context structure + transfer | 20–22 | Which context factors attenuate performance, and can that structure predict fresh contexts without refitting? |

Browse every phase and its verdict in the **research archive**:

https://aegisland-research-cockpit.vercel.app/phases/

---

# How to run AegisLand

## 1. Requirements

You need:

- **Python 3.10+**
- **Git**
- a terminal such as PowerShell, Command Prompt, Terminal, or bash

No physical UAV is required. The core research code runs in simulation.

---

## 2. Clone the repository

```bash
git clone https://github.com/suhaslord/uav-safety-research.git
cd uav-safety-research
```

---

## 3. Create a virtual environment

```bash
python -m venv .venv
```

Activate it.

### Windows PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
```

### macOS / Linux

```bash
source .venv/bin/activate
```

---

## 4. Install the project

```bash
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

This installs the package plus the development test dependency.

---

## 5. Run the tests

```bash
pytest -q
```

A clean test run verifies that the repository behaves as expected in your environment. It does **not** establish flight safety.

---

## 6. Run a small Monte Carlo experiment

For a quick local research run:

```bash
python scripts/run_experiments.py --episodes 20 --seed 2026 --out results/demo
```

This compares the baseline and supervised landing behavior across the repository's simulated perception-degradation profiles.

Generated outputs are written to `results/demo/`, including:

- `episodes.csv` — episode-level results
- `summary.csv` — aggregated metrics
- `summary.md` — readable summary table
- `unsafe_touchdown_rate.png`
- `success_rate.png`
- `run_metadata.json`

For a larger run, increase `--episodes` while keeping the seed fixed when you want reproducible comparisons.

Example:

```bash
python scripts/run_experiments.py --episodes 100 --seed 2026 --out results/run_100
```

---

## 7. Run the research cockpit locally

```bash
python scripts/serve_dashboard.py
```

Then open:

```text
http://127.0.0.1:8765
```

Press `Ctrl+C` in the terminal to stop the local server.

The production version is available at:

https://aegisland-research-cockpit.vercel.app/

---

## Reproducing the frozen scientific record

The simple Monte Carlo command above is the easiest way to understand the codebase, but it is **not a replacement for the sealed phase-specific evaluations** used in the later research lineage.

For the frozen scientific record:

1. Read the phase's preregistration or final report before running anything.
2. Keep development, transfer, protected, and final evidence roles separate.
3. Do not tune a method after protected or final evidence has been exposed.
4. Do not reinterpret a failed gate as a pass because a later phase succeeded.
5. Preserve frozen code, candidate hashes, seeds, and result artifacts when making a replication claim.

Useful starting points:

- [Reproducibility protocol](docs/reproducibility.md)
- [Phase 12 Iteration 3 final report](docs/phase12_iteration3_final_report.md)
- [Phase 12 Iteration 3 preregistration](docs/phase12_iteration3_preregistration.md)
- [Phase 12 width-tail forensics](docs/phase12_width_tail_forensics.md)
- [Phase 11 final report](docs/phase11_final_report.md)
- [Research cockpit](https://aegisland-research-cockpit.vercel.app/)
- [Full phase archive](https://aegisland-research-cockpit.vercel.app/phases/)

The canonical production UI bundle is under `deploy/vercel/`. Historical dashboard assets remain under `dashboard/` because earlier phases are part of the research record.

---

## What this project does **not** claim

- **Simulation only.** The project has not demonstrated safety on a physical aircraft.
- **No certification claim.** Passing experimental gates is not regulatory or flight-safety approval.
- **No production-readiness claim.** The research results do not establish operational reliability.
- **No real-sensor equivalence claim.** Synthetic and Gazebo evidence cannot automatically be generalized to real cameras.
- **No controller-tuning authorization.** A positive research result does not authorize deployment or flight-controller changes.
- **CI is software evidence, not safety evidence.** Passing tests shows that the code ran as tested; it does not prove the UAV is safe.

---

## In one sentence

**AegisLand studies how to recognize when UAV landing perception should not be trusted, then tests whether those conclusions survive harder evidence without moving the rules after seeing the results.**

> **Safety note:** AegisLand is educational, simulation-only research. It is not validated flight-control software and should not be used to operate a physical aircraft.
