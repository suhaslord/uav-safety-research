# AegisLand

I built AegisLand to test one question:

> **If a landing camera is confidently wrong, can an independent estimate expose the error before touchdown without making the system unusably conservative?**

This repository is a simulation study, not flight software. The useful part is the experiment record: what I changed, what I measured, which gates passed, and which results failed.

## What I tested

I started with synthetic landing experiments where the visual estimate could be biased while still looking internally consistent. I compared image-only estimation against supervisory variants that used temporal checks, a second imperfect estimate, uncertainty, and abstention.

Later phases moved toward harder evidence: PX4/Gazebo traces, genuine camera frames, partial views, appearance changes, frozen transfer sets, and protected validation that was evaluated only after the candidate and gates were fixed.

## Current result: Phase 11 P14R

Phase 11 is closed. The final candidate P14R was frozen at scientific head `58b06089a621264afb886f6aee2acaacf8a8709c`, passed every required seen-transfer gate, and then entered protected validation.

The protected result was **mixed / failed overall**. Availability and uncertainty coverage were strong, but one preregistered H4 lateral tail-efficiency component exceeded its frozen maximum:

| Protected check | Result |
|---|---:|
| Useful availability | **98.53% — PASS** |
| Lateral 95% coverage | **96.17% — PASS** |
| Altitude 95% coverage | **95.82% — PASS** |
| Calibration MACE | **0.03678 — PASS** |
| Lateral median interval width / p95 error | **0.855× — PASS** |
| Lateral p95 interval width / p95 error | **2.435× — FAIL** (`<= 2.25×` required) |
| Altitude median interval width / p95 error | **1.113× — PASS** |
| Altitude p95 interval width / p95 error | **1.833× — PASS** |
| Rescue recovery | **94.63%** |

### What I think this means

Phase 11 supports a narrower result than “the system passed.” Bounded continuity plus an independent rescue path solved most of the earlier availability problem, and a robust groupwise conformal envelope restored uncertainty coverage under the tested shift. But protected shift still produced an excessively wide lateral tail relative to the error it was covering.

I did **not** loosen the 2.25× threshold after seeing 2.435×. I also did **not** expose the final P15-v2 unseen holdout after the protected failure. Phase 11 therefore ends without a final unseen-replication claim.

## Why Phase 11 existed

Phase 10R improved mean error on ambiguous views but failed the preregistered all-gates rule. It left three problems visible:

- truth-visible miss rate: **20.0%**;
- lateral / altitude 95% uncertainty coverage: **84.3% / 79.7%** under shift;
- both p95 improvement gates failed.

Phase 11 specifically tested whether bounded continuity, independent rescue, and a more robust uncertainty-transfer scheme could repair those weaknesses without post-hoc retuning.

## Earlier results that looked much better

Phase 6B used a simpler synthetic setup. There, selective intervention reduced unsafe touchdowns from **43% to 1%**, with a deliberate **3% timeout** cost.

A separate V3 experiment also showed that independent error structure can matter: unsafe touchdowns fell from **84.2% to 2.4%** in that abstract redundant-perception setup.

Both results were useful, but later testing showed why the project needed harder evidence. Synthetic success did not guarantee that the same ideas would survive genuine camera limitations and distribution shift.

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
| 11 | Frozen seen transfer + protected validation | availability and coverage recovered; one locked lateral tail-efficiency component still failed |

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

- [Phase 11 final report](docs/phase11_final_report.md)
- [Phase 10R frozen result](docs/phase10r_frozen_holdout_result.md)
- [Phase 10R protocol](docs/phase10r_frozen_holdout_protocol.md)
- [Phase 10 result](docs/phase10_frozen_holdout_result.md)
- [Reproducibility protocol](docs/reproducibility.md)
- [Research log](docs/research_log.md)
- [Live research cockpit](https://aegisland-research-cockpit.vercel.app/)

The canonical production UI bundle is under `deploy/vercel/`. Historical dashboard assets remain in `dashboard/` because earlier phases are part of the research record.

## Limits I do not want this project to hide

- **Simulation only.** I have not validated this on a physical aircraft or hardware camera.
- **Safety acceptance is false.** Passing most metrics is not a flight-safety claim.
- Phase 11 failed the protected H4 lateral p95 interval-width / p95-error component: **2.435×** vs a frozen **2.25×** maximum.
- The final P15-v2 unseen holdout was **not exposed** after that failure and is retired without an unseen-replication claim.
- Phase 10R previously had a **20%** truth-visible miss rate and undercoverage under appearance/geometry shift.
- The Phase 10 camera holdout was small: 20 truth-visible frames and 15 paired observations.
- Passing CI tests says the software runs as tested. It does not make the system flight-safe.

## Next question

Phase 11 is closed. Any attempt to improve the lateral tail-efficiency failure must be a **new preregistered phase** with fresh development, transfer, and protected evidence. The Phase 11 protected result should not be reused as a hidden test, and the retired P15-v2 holdout should not be opened to rescue this result.

A legitimate next study would ask whether a new uncertainty model can reduce protected lateral tail width **without** sacrificing the availability and coverage gains that P14R achieved.

**Safety note:** AegisLand is educational, simulation-only research. It is not validated flight-control software and should not be used to operate a physical aircraft.
