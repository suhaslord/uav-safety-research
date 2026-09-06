# AegisLand

I built AegisLand to test one question:

> **If a landing camera is confidently wrong, can independent evidence and calibrated uncertainty expose the error without making the system unusably conservative?**

This repository is a simulation study, not flight software. The useful part is the experiment record: what changed, what was frozen, what evidence was allowed to influence development, which gates passed, which gates failed, and which holdouts stayed untouched until their preregistered stage.

## Current result: Phase 12 Iteration 3

**Phase 12 is closed. Iteration 3 passed development, transfer, protected validation, and final unseen replication without retuning after candidate freeze.**

The Phase 12 lineage was created after Phase 11 P14R missed one locked protected H4 lateral tail-efficiency gate (`2.4354x` vs `<= 2.25x`). Phase 11 remained closed. Phase 12 used fresh scale-fit/calibration/development/transfer/protected/final evidence and never reused the Phase 11 protected seed.

### Final holdout — seed `935935`

| Final check | Result |
|---|---:|
| Useful availability | **98.57% — PASS** |
| Lateral 95% coverage | **95.53% — PASS** |
| Altitude 95% coverage | **95.22% — PASS** |
| Calibration MACE | **0.01751 — PASS** |
| Lateral median interval width / p95 error | **0.5613x — PASS** |
| Lateral p95 interval width / p95 error | **2.23035x — PASS** (`<= 2.25x`) |
| Altitude median interval width / p95 error | **0.7768x — PASS** |
| Altitude p95 interval width / p95 error | **1.7291x — PASS** |
| Rescue recovery | **95.43% — PASS** |
| Diagnostic AUROC | **0.9833** |

The final H4 lateral p95 result is close to its locked boundary, which is why the unchanged protected and final replications matter. No threshold was relaxed and no post-hoc interval multiplier was added.

## What changed in Phase 12

The Phase 11 point estimator, bounded continuity path, independent rescue, velocity caps, innovation scales, availability logic, and gate definitions stayed fixed. Phase 12 changed only the uncertainty model.

The first two development iterations improved the targeted lateral H4 p95 ratio but still failed it:

- v1 severity-conditioned normalized conformal: `2.3620x` — FAIL
- v2 continuity-scale contrast shrinkage: `2.3485x` — FAIL

Seen-only forensics showed that the largest continuity widths were poorly aligned with the largest actual errors, while normalized lateral anchor innovation was a much stronger inference-visible indicator of error heteroscedasticity than severity. Iteration 3 therefore added one bounded continuity-only lateral reliability coordinate derived from anchor innovation and fit its low-capacity normalization using scale-fit evidence only.

No neural model, optimizer sweep, development-selected coefficient, calibration weakening, gate change, point-estimator change, rescue change, or threshold movement was introduced.

## Frozen Iteration 3 identity

- scientific Git SHA: `8d0617a83d699cd14eae6194ce3a86a5c034dfbc`
- candidate SHA-256: `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`
- method: `continuity_lateral_innovation_residual_normalized_robust_conformal`
- frozen invariant suite: `35 passed`
- broad CI on frozen scientific SHA: PASS

### Replication progression

| Stage | Seed | Lateral H4 p95 | Lateral 95% coverage | Verdict |
|---|---:|---:|---:|---|
| Development | `907907` | `2.16845x` | `94.95%` | PASS |
| Transfer | `913913` | `2.05804x` | `94.50%` | PASS |
| Protected validation | `924924` | `2.21245x` | `95.40%` | PASS |
| Final holdout | `935935` | **`2.23035x`** | **`95.53%`** | **PASS** |

No scientific code or candidate content changed after freeze.

## Evidence ledger

Permanently seen in Phase 12:

- scale-fit `880880`
- calibration A `891891`
- calibration B `902902`
- development-only `907907`
- transfer `913913` — exposed once after development PASS
- protected `924924` — exposed once after transfer PASS
- final `935935` — exposed once after protected PASS

Untouched / forbidden throughout Phase 12:

- Phase 11 protected `858858` — never reused or reevaluated
- retired Phase 11 P15-v2 `869869` — never exposed

## How the evidence changed over time

| Phase | Evidence | What I learned |
|---|---|---|
| 6B | Synthetic landing holdout | selective intervention can help in the defined synthetic benchmark |
| 7 | Stress-factor experiments | redundancy assumptions break under some mismatches |
| 8 | PX4/Gazebo trace comparison | the external trace was a diagnostic mismatch, not a validation pass |
| 9 | Genuine Gazebo camera frames | strong detection does not automatically give trustworthy metric geometry |
| 10 | Temporal estimate + calibrated uncertainty | uncertainty improved; point-error target failed |
| 10R | New geometry + appearance holdout | mean error improved, but tail, misses, and shift calibration failed |
| 11 | Fresh transfer + protected validation | availability and coverage recovered; locked lateral tail efficiency still failed |
| **12** | Fresh scale-fit/calibration + development → transfer → protected → final | **innovation-conditioned continuity uncertainty passed the locked simulation-study gates across the full frozen progression** |

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

- [Phase 12 Iteration 3 final report](docs/phase12_iteration3_final_report.md)
- [Phase 12 Iteration 3 preregistration](docs/phase12_iteration3_preregistration.md)
- [Phase 12 width-tail forensics](docs/phase12_width_tail_forensics.md)
- [Phase 12 development log](docs/phase12_development_log.md)
- [Phase 11 final report](docs/phase11_final_report.md)
- [Reproducibility protocol](docs/reproducibility.md)
- [Live research cockpit](https://aegisland-research-cockpit.vercel.app/)

The canonical production UI bundle is under `deploy/vercel/`. Historical dashboard assets remain in `dashboard/` because earlier phases are part of the research record.

## Limits I do not want this project to hide

- **Simulation only.** This has not been validated on a physical aircraft or hardware camera.
- **Safety acceptance is false.** Passing simulation-study gates is not a flight-safety or certification claim.
- **Controller tuning is not authorized from this result.** Phase 12 evaluates uncertainty behavior around a frozen estimator lineage.
- The final H4 lateral p95 ratio, `2.23035x`, passes but is close to the locked `2.25x` maximum.
- The study does not establish real-sensor rescue equivalence, autonomous landing safety, operational reliability, or production readiness.
- Passing CI tests says the software runs as tested. It does not make the system flight-safe.

## Next question

Phase 12 is now closed. No more Phase 12 tuning or evidence exposure is authorized.

Any follow-on study should start a **new preregistered lineage with fresh evidence**. A legitimate next question is whether the same uncertainty-allocation idea transfers to a meaningfully different simulator, sensor model, or real recorded camera dataset while preserving the same evidence hygiene.

**Safety note:** AegisLand is educational, simulation-only research. It is not validated flight-control software and should not be used to operate a physical aircraft.