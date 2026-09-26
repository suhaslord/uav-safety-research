# Phase 25 — Failure Atlas protocol

## Status and purpose

Phase 25 is a retrospective, frame-level diagnostic of the Phase 22 baseline
and frozen Phase 23 detector. Phase 23 and Phase 24 already reported aggregate
metrics on this protected temporal test split, so this audit does not create a
new independent confirmation result. No model training, threshold selection,
or model selection is part of Phase 25.

The audit asks which target boxes each detector finds under the six existing
conditions, where their outcomes differ, and how detector score relates to
box correctness. Detector scores are not landing-safety probabilities.

## Frozen inputs

- Protected test IDs: `results/phase25_failure_atlas/protected_test_manifest.csv`
- Expected frames: 86, subject to validation against all supplied files
- Conditions: clean, blur, low_light, noise, occlusion, and mixed
- Expected frame-condition views: 86 × 6 = 516, subject to manifest validation
- Baseline: exact checkpoint from GitHub Actions artifact `10382104202`
  (`kios-real-detector-baseline`, run `34932763449`)
- Phase 23 model: exact frozen Phase 23 checkpoint; this checkpoint must be
  recovered before frame predictions can be generated
- Input hashes and artifact provenance: `docs/phase25_input_lock.json`; its
  Phase 23 checkpoint hash and original inference package versions are
  deliberately unset until the checkpoint and its metadata or evaluation
  environment are recovered
- Frozen per-model inference settings (input size, confidence floor, NMS IoU,
  max detections, batch, workers, and device): `docs/phase25_input_lock.json`.
  Phase 22 uses CPU at 320 px; Phase 23 uses device `0` at 480 px.
- Aggregate reconciliation tolerance: 0.001
- Frame outcome matching: same class, confidence-ranked, one-to-one, IoU ≥ 0.50
- Stress transforms: the committed implementation and seed `20260915`
  in `scripts/build_real_image_stress_suite.py`

The baseline artifact archive SHA-256 is
`7080c8243c1d7cb85a63f81ea0531eda34dd1f18616f7b4dfdc869a2379c9833`; its
`best.pt` SHA-256 is
`3a1801b192d624f8dcdda4bc5d9a9157309000df67a4c30d62368c37901feddd`.
The 86-row manifest was extracted from that verified artifact. The KIOS
images and labels, Phase 23 checkpoint, and original inference package
versions are external inputs and must be recovered before the run. The runner
refuses to start until the exact Ultralytics and PyTorch versions are recorded
in the lock and match the installed packages. Model and data hashes are
recorded in every successful run manifest.

The checked Phase 23 Actions artifact (run `35797446835`, artifact
`10725155542`) contains `samples.csv`, `summary.json`, and `summary.md`, but no
checkpoint. The recorded train arguments identify the model resolution and
evaluation settings; they do not substitute for the frozen weights or missing
runtime version record.

## Run sequence

Restore the original files to local paths, then run the validator before the
prediction runner. The validator and runner both read the committed lock; they
do not accept a caller-supplied checkpoint hash.

```bash
python scripts/verify_phase25_inputs.py \
  --source-root data/derived/kios_real_yolo \
  --stress-root data/derived/kios_real_stress \
  --baseline-weights data/external/phase25_inputs/phase22_baseline_best.pt \
  --phase23-weights data/external/phase25_inputs/phase23_robust_best.pt

python scripts/run_phase25_frame_audit.py \
  --source-root data/derived/kios_real_yolo \
  --stress-root data/derived/kios_real_stress \
  --baseline-weights data/external/phase25_inputs/phase22_baseline_best.pt \
  --phase23-weights data/external/phase25_inputs/phase23_robust_best.pt

python scripts/analyze_phase25_failures.py
```

The analysis command runs only after the prediction runner has written its
complete, aggregate-reconciled output directory.

If the exact stress images are unavailable but the source archive is recovered,
the repository records the split builder, stress generator, and seed. Rebuild
into fresh ignored paths, then let the validator confirm the protected IDs and
labels before inference:

```bash
python scripts/download_kios_real_landing_dataset.py \
  --out data/external/kios_landing_pad \
  --accept-download \
  --extract

python scripts/prepare_kios_real_yolo_split.py \
  --dataset-root data/external/kios_landing_pad/extracted \
  --out data/derived/kios_real_yolo

python scripts/build_real_image_stress_suite.py \
  --split-root data/derived/kios_real_yolo \
  --out data/derived/kios_real_stress \
  --seed 20260915
```

These commands do not replace checkpoint recovery or aggregate reconciliation.

## Frozen analysis

For each prediction, match to the highest-IoU unmatched ground-truth box of the
same class, processing predictions by descending confidence. A match at IoU
≥ 0.50 is a true positive; unmatched predictions are false positives, and
unmatched labels are false negatives. A frame succeeds when all its labeled
targets are matched. Empty-target frames are rejected by input validation.

For every frame-condition-model row, retain target count, detection count,
TP/FP/FN, best IoU, highest score, and whether all targets were found. For
every predicted box, retain normalized coordinates, confidence, match IoU,
matched target index, and TP/FP status. Duplicate boxes cannot reuse a target.

Compare the two detectors with four paired frame outcomes: recovered,
regressed, both succeeded, and both failed. Summarize object-level TP/FP/FN
and frame-success rates by condition. The manifest has only two source
sequences (66 and 20 test frames), so Phase 25 will report paired counts and
descriptive differences without p-values or bootstrap confidence intervals.
Frame-level resampling would overstate the independent sample size here.

Confidence analysis uses all predicted boxes, with TP as the binary outcome.
Use fixed-width bins and report bin counts, mean score, observed box
correctness, ECE, and Brier score. These summarize score-versus-localization
behavior on this reused set; they do not calibrate a safety decision.

Image associations may include target area, normalized target center, mean
brightness, contrast, and a simple sharpness measure. Treat associations as
descriptive. Occlusion and mixed are generated image transformations, not
evidence about all real-world occlusions or camera conditions.

## Reproduction gate

Before writing prediction rows, rerun aggregate validation for both exact
checkpoints on all six conditions with the frozen settings above. Compare
Phase 23 recall and mAP50 against the committed
`results/phase23_robust_detector/robustness_metrics.csv` and baseline values
in `results/phase23_robust_detector/robustness_comparison.csv`. If a required
input is missing or metrics differ by more than the preregistered tolerance
(0.001), stop before generating Phase 25 outputs and record the mismatch.

The prediction runner must also verify that every condition contains exactly
the protected image IDs, that labels are unchanged, and that all expected
input files have SHA-256 entries in `run_manifest.json`. It must not download,
regenerate, or overwrite data automatically.

## Outputs

On a successful run, `results/phase25_failure_atlas/` contains:

- `run_manifest.json`
- `prediction_boxes.csv`
- `frame_condition_metrics.csv`
- `transition_counts.csv`
- `condition_summary.csv`
- `confidence_calibration.csv`
- `confidence_distribution.csv` for correct and incorrect boxes
- `feature_summary.csv` by detector and condition
- `failure_by_target_size.csv` for both detectors
- `summary.json` and `summary.md`
- `figures/` with outcome transitions, failure matrix, confidence reliability,
  and failure rate by target size

The report and website can be published only after these outputs exist and
reconcile. Any example gallery must use images whose publication is allowed by
the dataset terms; source images and model weights stay outside Git.

## Limits and next phase

Phase 25 is an exploratory failure audit on one previously reported temporal
holdout. It does not show causal failure mechanisms, controller performance,
flight readiness, or landing safety. Phase 26 must use separate development
data to choose any reliability rule, then evaluate the frozen rule on new
evidence.
