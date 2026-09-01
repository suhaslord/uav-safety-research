# AegisLand

I built AegisLand to test one question:

> **If a landing camera is confidently wrong, can an independent estimate expose the error before touchdown without making the system unusably conservative?**

This repository is a simulation study, not flight software. The useful part is the experiment record: what I changed, what I measured, and which results failed.

## What I tested

I started with synthetic landing experiments where the visual estimate could be biased while still looking internally consistent. I compared image-only estimation against supervisory variants that used temporal checks, a second imperfect estimate, uncertainty, and abstention.

Later phases moved toward harder evidence: PX4/Gazebo traces, genuine camera frames, partial views, appearance changes, and protected holdouts that were evaluated once after the candidate was frozen.

## Current result: Phase 10R

Phase 10R was frozen at `e1d566f8baa47bf10f9bdf39dd5988724208be80` and then evaluated once on 12 new geometry trajectories across three appearance conditions: 36 sequences and **1,440 truth-visible frames**.

It **failed the preregistered all-gates rule**.

| Test | Result |
|---|---:|
| Clean lateral / altitude MAE vs Phase 9 | PASS — `0.704x / 0.417x` |
| Ambiguous lateral MAE improvement | PASS — **79.2%** |
| Ambiguous altitude MAE improvement | PASS — **73.7%** |
| Ambiguous lateral p95 improvement | FAIL — **-1.1%** |
| Ambiguous altitude p95 improvement | FAIL — **7.3%** |
| Truth-visible miss rate | FAIL — **20.0%** |
| False-positive rate | PASS — **0.0%** |
| 95% uncertainty coverage | FAIL — **84.3% lateral / 79.7% altitude** |

### What I think this means

The candidate improved average error on ambiguous views, but that was not enough. A difficult tail remained, one in five truth-visible frames was missed, and uncertainty that looked calibrated during development became overconfident after appearance and geometry changed.

The narrow conclusion is: **good in-domain calibration did not transfer cleanly under this shift.**

I am not treating the mean-error improvement as a safety win because the tail, availability, and uncertainty gates failed.

## Earlier result that looked much better

Phase 6B used a simpler synthetic setup. There, selective intervention reduced unsafe touchdowns from **43% to 1%**, with a deliberate **3% timeout** cost.

That result was useful, but later testing showed why the project needed harder evidence. Synthetic success did not guarantee that the same ideas would survive genuine camera limitations and distribution shift.

A separate V3 experiment also showed that independent error structure can matter: unsafe touchdowns fell from **84.2% to 2.4%** in that abstract redundant-perception setup. Again, that is evidence for the benchmark, not a claim about a physical aircraft.

## A result that did not transfer

In Phase 10, every usable Gazebo-camera observation was already clean ArUco geometry at centimeter scale. The temporal estimator therefore did **not** improve the point estimate:

| Metric | Phase 9 | AegisT10 |
|---|---:|---:|
| Lateral / altitude MAE | `2.77 / 1.57 cm` | `2.77 / 1.57 cm` |
| Median \|residual\| / sigma (lat / alt) | `13.17 / 5.11` | `0.65 / 0.52` |
| 2-sigma coverage | — | `93% / 100%` |

So the useful Phase 10 result was about uncertainty calibration, not better point estimation. I froze the mixed result and did not retune after seeing the holdout.

## How the evidence changed over time

| Phase | Evidence | What I learned |
|---|---|---|
| 6B | Synthetic landing holdout | selective intervention can help in the defined synthetic benchmark |
| 7 | Stress-factor experiments | redundancy assumptions break under some mismatches |
| 8 | PX4/Gazebo trace comparison | the external trace was a diagnostic mismatch, not a validation pass |
| 9 | Genuine Gazebo camera frames | strong detection does not automatically give trustworthy metric geometry |
| 10 | Temporal estimate + calibrated uncertainty | uncertainty improved; point-error target failed |
| 10R | New geometry + appearance holdout | mean error improved, but tail, misses, and shift calibration failed |
| 11 | Next | test reliability and abstention specifically under domain shift |

## Reproducing the repository

```bash
git clone https://github.com/suhaslord/uav-safety-research.git
cd uav-safety-research
python -m venv .venv
# macOS / Linux: source .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest
python scripts/serve_dashboard.py
```

Useful records:

- [Phase 10R frozen result](docs/phase10r_frozen_holdout_result.md)
- [Phase 10R protocol](docs/phase10r_frozen_holdout_protocol.md)
- [Phase 10 result](docs/phase10_frozen_holdout_result.md)
- [Reproducibility protocol](docs/reproducibility.md)
- [Research log](docs/research_log.md)
- [Live result archive](https://aegisland-research-cockpit.vercel.app/)

## Limits I do not want this project to hide

- **Simulation only.** I have not validated this on a physical aircraft or hardware camera.
- The Phase 10R miss rate was **20%**, above the preregistered 10% maximum.
- Both Phase 10R p95 improvement gates failed.
- Phase 10R 95% uncertainty coverage fell to **84.3% lateral / 79.7% altitude** under shift.
- The Phase 10R holdout is now seen and cannot be reused as a hidden test.
- The Phase 10 camera holdout was small: 20 truth-visible frames and 15 paired observations.
- Passing CI tests says the software runs as tested. It does not make the system flight-safe.

## Next question

Rather than retuning Phase 10R on a failed holdout, the next phase asks whether the estimator can recognize when its uncertainty calibration has stopped transferring. I want to measure coverage under shift, tail failures, and abstention behavior directly.

**Safety note:** AegisLand is educational, simulation-only research. It is not validated flight-control software and should not be used to operate a physical aircraft.
