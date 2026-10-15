# 20-epoch 384 px detector comparison — development result

**Outcome: FAIL development screen. Do not promote the candidate.** This is a matched two-arm experiment, **not** a claim of improved robustness, independent generalization, or flight safety.

- GitHub Actions receipt: [run 38683570846](https://github.com/suhaslord/uav-safety-research/actions/runs/38683570846) · [six-file artifact including both checkpoints and exact comparison JSON](https://github.com/suhaslord/uav-safety-research/actions/runs/38683570846/artifacts/11949269203)
- Artifact ZIP SHA-256: `a2b58d25ca260fcab3a428455f7d673450f1fedef319f677bad700b243c9be43`
- Frozen split SHA-256: `32623634069c4f3082b79a6a42bca408c636f4b626e5f7691276257999544905`
- Seed `20261015`; initialized from `yolo11n.pt`; 20 epochs, 384 px, batch 16, CPU, SGD, matched training-image count 252 per arm, matched optimizer-step budget.
- Candidate: train-only photometric augmentation on 38/252 images (15%); train conditions blur, low light, noise. The 64-frame development validation shares two original KIOS video sessions; no independent sessions, no protected-test reads.
- Source: the artifact's `detector_robustness-comparison/comparison.json` (schema `aegisland.detector_robustness.development-comparison.v2`) and `detector_robustness-aug/receipt.json`.

## Aggregate development-validation metrics

| Metric | Matched baseline | Photometric candidate | Candidate − baseline |
|---|---:|---:|---:|
| Precision | 0.7791 | 0.5310 | −0.2482 |
| Recall | 0.6406 | 0.4246 | −0.2161 |
| mAP50 | 0.7817 | 0.4841 | −0.2976 |
| mAP50–95 | 0.3580 | 0.2816 | −0.0765 |

## Development mAP50 difference by condition

| Condition | Candidate − baseline |
|---|---:|
| Clean | −0.2976 |
| Blur | −0.3163 |
| Low light | −0.2104 |
| Noise | −0.3685 |
| Partial occlusion | −0.2495 |
| Mixed | −0.2401 |

The mean six-condition mAP50 difference was **−0.2804**. All five predeclared development screening gates evaluated to `false`: clean mAP50, clean precision, blur mAP50, mixed mAP50, and mean six-condition mAP50. The result does **not** support the proposed longer-training photometric candidate.

## Reproducibility / acceptance boundaries

- Baseline `best.pt` SHA-256: `4727a202a9fd393de480336363515a8639736a530fa44c4bb7817063c82b7855`
- Candidate `best.pt` SHA-256: `be7be4469d3b0e640ae293c4ec5e2f8d03ade76b3b013137ce317e7437e10a33`
- Both checkpoint files, training CSVs, augmentation receipt and machine-readable comparison are in the linked Actions artifact.
- The two development sessions are dependent on the training source; the experiment explicitly records `independent_validation=false`, `protected_test_evaluated=false`, `model_improvement_established=false` and `automatic_model_promotion=false`.
- Preserve existing accepted checkpoints and frozen results. This comparison is exploratory and should stay labeled **development-only negative result**. No new protected evaluation or threshold tuning is authorized by this report.
