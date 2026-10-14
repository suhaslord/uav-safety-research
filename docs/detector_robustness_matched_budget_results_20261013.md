# Detector robustness — matched-budget development results (2026-10-13 PT)

**Outcome: candidate NOT promoted.** This is continued work on the existing AegisLand detector, not a new numbered research phase.

- Successful end-to-end Actions run: [38512201126](https://github.com/suhaslord/uav-safety-research/actions/runs/38512201126)
- Downloadable evidence artifact: **detector-robustness-matched-budget-model-pilot**, ID **11870487981**, containing the exact `comparison.json`, training-data receipt, separate baseline/candidate `best.pt` checkpoints and per-epoch `results.csv`.
- Full project CI on the corrected code: [38512201066](https://github.com/suhaslord/uav-safety-research/actions/runs/38512201066), **PASS**.
- Earlier workflow failure: [38511960396](https://github.com/suhaslord/uav-safety-research/actions/runs/38511960396), caused by missing `train:` YAML metadata in validation-only stress datasets. The validator requires both `train:` and `val:` keys; corrected without training on stress-validation images.

## What was actually changed

The first exploratory pilot appeared favorable, but unfairly gave the augmented arm 756 images per epoch versus 252 for baseline. This follow-up corrects the optimizer-budget confound **without reading or tuning on the protected test set**.

Both arms use 252 train images per epoch, seed 20261013, the same YOLO11n initialization, batch 16, 320 px, SGD optimizer with built-in training augmentations off, and four training epochs. One arm uses all 252 original development-train images; the other retains 126 original files and deterministically replaces the other 126 with one moderate augmented view each (26 blur, 25 low-light, 25 noise, 25 partial obstruction, 25 mixed). All labels and filenames remain unchanged.

Exactly **64 unchanged validation images**, plus five deterministic stress treatments of those same development-validation frames, were evaluated on both saved checkpoints. These 384 dependent views per model are from the existing KIOS videos and should not be treated as independent capture sessions. No zero-pad negatives were admitted. No Phase 23 checkpoint/protocol has been changed.

## Measured metrics (development validation ONLY)

Values are from the saved machine-readable `comparison.json` within the successful Action artifact, not inferred from screenshots.

| Condition | Baseline mAP50 | Candidate mAP50 | Candidate − baseline | Baseline recall | Candidate recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| Clean | 0.2930 | 0.2536 | **−0.0395** | 0.2545 | 0.3281 |
| Blur | 0.2878 | 0.1894 | **−0.0984** | 0.2812 | 0.2545 |
| Low light | 0.3396 | 0.3306 | **−0.0091** | 0.3906 | 0.3789 |
| Noise | 0.2515 | 0.2815 | **+0.0300** | 0.2500 | 0.3438 |
| Partial occlusion | 0.3138 | 0.3286 | **+0.0148** | 0.3906 | 0.3281 |
| Mixed | 0.1830 | 0.1371 | **−0.0459** | 0.1406 | 0.2344 |

**Clean precision:** baseline 0.6705, candidate 0.3346 (−0.3360). **Clean mAP50–95:** baseline 0.1783, candidate 0.1464 (−0.0319). Neither the noisy nor occluded mAP50 gain proves a robustness gain across operating points: noise mAP50–95 was **lower** for the candidate (0.1576 vs. 0.1184), while partial-occlusion mAP50–95 was slightly higher (0.1017 vs. 0.1070).

## Model identities and decision

- Verified historical split manifest SHA-256: `32623634069c4f3082b79a6a42bca408c636f4b626e5f7691276257999544905`
- Matched candidate receipt SHA-256: `fcaa1c6d8926c7de8dc660b03a947f753d61ba3bf888bac97f2b7df46e6dcc2a`
- Four-epoch baseline `best.pt` SHA-256: `81d2d48a1bfe6db01f5498aea5959f3c26b19d51a5c19acd63bdda617a448a03`
- Four-epoch augmented candidate `best.pt` SHA-256: `e186e1b772623687de790ac5007cca48bf80cf447a26ec8bdfd747790c94923a`
- Both recorded `matched_optimizer_step_budget: true`, `protected_test_evaluated: false`, `independent_validation: false`, and `model_improvement_established: false`.

**Decision:** do not replace the existing published detector or claim that augmentation has improved reliability. The candidate loses clean precision and mAP as well as blur and mixed mAP. Keep both artifacts as reproducible negative evidence. The matched-budget comparison is a real improvement to experimental validity, not a verified improvement in model accuracy or autonomous landing safety.

**Research limitations:** the 64 development images are temporally dependent within two KIOS videos, stress copies depend on those same sources, only one optimization seed and four epochs were run, and no eligible independent camera sessions or absent-pad examples exist. No prospective calibration threshold, flight readiness, controller validation or generalization claim follows from this result.
