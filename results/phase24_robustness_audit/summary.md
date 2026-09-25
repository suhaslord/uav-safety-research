# Phase 24 · Robustness frontier audit

**Type:** Descriptive reanalysis of committed Phase 23 condition aggregates.  
**New detector training or predictions:** None.  
**Source SHA-256:** 1f93dd35fe383d9a65f85268490d754323da61ca052fa2b4a7363bf481e00073

## Readout

- Equal-weight macro mAP50: **0.370 → 0.405** (+0.034, +9.3% relative).
- Equal-weight macro recall: **0.340 → 0.413** (+0.072, +21.3% relative).
- mAP50 improves in **4/6** conditions; it regresses in **2/6**.
- Occlusion + mixed-stress macro mAP50: **0.266 → 0.133** (-0.133, -49.9% relative).

## Method and limits

The macros are unweighted arithmetic means of the six published condition-level metrics. The occlusion + mixed-stress readout equally averages those two conditions. All conditions reuse the same 86-frame temporal test holdout; the six transformed views are not 516 independent frames.

The repository contains aggregate metrics, not per-frame predictions, so this audit reports no confidence intervals or significance tests. Detector metrics alone do not establish landing safety, controller performance, or real-flight readiness. safety_acceptance=false; controller_tuning_allowed=false.

## Reproduce

Run python scripts/analyze_phase24_robustness_frontier.py from the repository root. The script validates the source deltas and writes this summary, summary.json, condition_frontier.csv, and the dashboard data JSON.
