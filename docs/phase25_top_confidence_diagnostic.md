# AegisLand — main-goal diagnostic: does the *trusted* top prediction localize the pad?

**Status:** Read-only, retrospective Phase 25 diagnostic. **No new experiment or independent data admitted.**  
**Question:** *When landing perception becomes unreliable, can AegisLand identify unreliable estimates before a downstream system trusts them?*

## Why this analysis matters

Phase 25's archived `frame_success` metric says whether **all annotated pad targets are matched by at least one prediction** in the large, low-confidence-floor detector output. That is not the same question as whether the **highest-confidence target prediction**—the one a future reliability gate would consider—is correctly localized.

A frame can have `frame_success=True` even if a very confident *incorrect* box outranks the correct lower-confidence box. Reporting frame success alone risks overstating the reliability of the top candidate. This diagnostic measures that discrepancy without retraining, altering the original matching, or changing the old results.

## Immutable evidence and definitions

Read only:
- `results/phase25_failure_atlas/run_manifest.json`
- `results/phase25_failure_atlas/frame_condition_metrics.csv`
- `results/phase25_failure_atlas/prediction_boxes.csv`
- `results/phase25_failure_atlas/ground_truth_targets.csv`

The program verifies **all four prediction table SHA-256 hashes** against the original Phase 25 run manifest, requires 86 frames × 6 dependent conditions × 2 models = 1032 cases, and fails if frame/prediction/target counts do not reconcile. Historical files are never rewritten.

For each frame, model and condition:

1. Score all the recorded predictions of frozen `landing_pad` class 0 without reading ground truth.
2. Identify the maximum-confidence candidate, resolving score ties by the original prediction index.
3. **Only after choosing that prediction**, compute its maximum IoU against the existing pad annotation boxes. Label it correct if IoU ≥ 0.50, otherwise incorrect. Retain zero-area boundary-clipped predictions as IoU=0 wrong guesses rather than dropping them.
4. Report whether this differs from the previously published `frame_success` definition.
5. Report descriptive accepted counts and wrong-top-box counts at **fixed illustrative score cutoffs** 0.05, 0.25, 0.50, 0.75, 0.90. These are not selected thresholds and are **not** a validation of a new accept/abstain decision rule.

## Evidence boundaries

These are **previously used protected test images**, and all six stress variants come from 86 frames in only **two video sessions**. The table contains no independent negative-target set, so a true false-accept rate on empty images cannot be estimated. Do not resample frames as independent statistical units, report p-values, select deployment thresholds, or use this table to lock a Phase 26 threshold.

This is a *failure diagnosis*, not a new held-out validation, a safe landing probability, an integrated controller experiment, or a flight-safety claim. Top-box agreement does not guarantee safe state estimation.

## How to reproduce

```bash
python -m unittest discover -s tests -p 'test_phase25_top_confidence_diagnostic.py' -v
python scripts/diagnose_phase25_top_confidence.py \
  --results-dir results/phase25_failure_atlas \
  --out-dir phase25_top_box_reliability_audit
```

The GitHub workflow `phase25-top-confidence-diagnostic.yml` also saves `summary.json`, `top_prediction_outcomes.csv`, the exact commit and Python version as a downloadable Actions artifact. No GPU, internet dataset download, or model checkpoint is necessary.

## Actual main-goal next step

Phase 26 still requires a **new independently captured and appropriately licensed real-camera landing-pad dataset**. The prerequisite is verified capture/session lineage, physical landing-target compatibility, negative frame inventory, reliable bounding boxes, zero overlap against all 422 original KIOS real images and full-session dev/test separation. Then freeze one confidence rule on development data only, and evaluate sealed test sessions only once. The existing main research record still correctly says `NO_DATASET_ADMITTED`.

Motor-fault pilots are a separate side research track; they do not close the landing-perception reliability question.
