# Phase 25A — baseline-only diagnostic

The [Failure Atlas](https://aegisland-research-cockpit.vercel.app/failure-atlas/) displays real Phase 22 baseline detections over the 86 protected KIOS frames and six frozen reconstructions (516 frame-condition cases). It is a retrospective analysis of the same test frames used in Phases 23–24. **It is not independent validation.** The Phase 23 checkpoint has been recovered and authenticated; paired per-frame outcomes (49 recovered, 65 regressed, 223 both-pass, 179 both-fail) are reported in the [paired frame outcomes](../results/phase25_failure_atlas/paired_frame_outcomes.csv).

## Evidence and reproduction

- [Run manifest](../results/phase25_baseline_diagnostic/run_manifest.json): archive, split, stress, model, method, software, and output hashes.
- [Published aggregate reconciliation](../results/phase25_baseline_diagnostic/aggregate_validation.csv): baseline recall and mAP50 match the six published values within 0.001 (in fact, differences are at floating point precision, except noise recall differs by ~0.000000015).
- [Full prediction table](../results/phase25_baseline_diagnostic/prediction_boxes.csv.gz): 136,359 model predictions with score ≥ 0.001, normalized coordinates, nearest target IoU, and frozen one-to-one match status.
- [Frame metrics](../results/phase25_baseline_diagnostic/frame_condition_metrics.csv): 516 rows with TP, FP, FN, frame success, score, IoU, target area, brightness, and gradient-based sharpness.
- [Ground truth targets](../results/phase25_baseline_diagnostic/ground_truth_targets.csv) and [condition summary](../results/phase25_baseline_diagnostic/summary.json).

The archive checksum, protected IDs, reconstructed image hashes, and checkpoint hash are checked before inference. The exact validation settings are `imgsz=320`, `conf=0.001`, NMS `iou=0.7`, `max_det=300`, batch `16`, CPU. Python, Torch, Ultralytics, NumPy, and Pillow versions are pinned and checked before inference; exact versions are in the run manifest. Run `python scripts/run_phase25_baseline_diagnostic.py --archive PATH --source PATH --stress PATH --baseline PATH` after restoring those inputs from the recorded reconstruction. The output directory must be empty. The builder `python scripts/build_failure_atlas_data.py --check` validates all table hashes and the compact site snapshot.

The frame success criterion is every annotated landing pad matched once at IoU ≥ 0.50, using all detections above the frozen 0.001 score floor. A duplicate prediction is a false positive. This low score floor intentionally yields many false positives; the matched-target counts are not interchangeable with published validation recall, which Ultralytics chooses at a score on its precision-recall curve. The Atlas draws only scores ≥ 0.01 plus any lower-scoring true positives for legibility, and labels omitted boxes. It still reports TP/FP/FN from the complete 0.001 table. A score-versus-IoU plot is descriptive box correctness, not a safety probability; its 0.70 display filter is not a selected reject rule.

| Condition | Baseline frames with all targets matched | TP | FP | FN |
| --- | ---: | ---: | ---: | ---: |
| Clean | 53 / 86 | 53 | 23,676 | 33 |
| Blur | 45 / 86 | 45 | 23,812 | 41 |
| Low light | 49 / 86 | 49 | 23,878 | 37 |
| Noise | 45 / 86 | 45 | 20,743 | 41 |
| Occlusion | 53 / 86 | 53 | 24,277 | 33 |
| Mixed | 43 / 86 | 43 | 19,685 | 43 |

The deployment build reconstructs all 86 protected source frames and six stress conditions from the checksum-verified Zenodo archive, verifies them against the frozen image inventories, then serves 640-pixel-wide JPEG previews for all 516 frame-condition views. The previews are generated during deployment and stay out of Git along with the raw archive, labels, and model weights. The Failure Atlas credits the 2024 KIOS dataset creators and links to the source record. Zenodo currently leaves the record's license field blank; this project does not claim to relicense the source images. Some frames are temporally adjacent; no independent-frame uncertainty claim is made. The Phase 26 protocol requires different, duplicate-screened imagery before any new reliability rule is frozen and evaluated.
