# Detector robustness: first paired development pilot — 2026-10-13 PT

**Execution: PASS. Experimental status: exploratory development only.**
[GitHub Actions run 38509701137](https://github.com/suhaslord/uav-safety-research/actions/runs/38509701137) succeeded after restoring the SHA-verified KIOS archive from cache. The original Zenodo attempt timed out, but this successful rerun reconstructed the fixed source split and completed both real YOLO11n CPU training runs.

The saved `phase27-dev-only-model-pilot` artifact (GitHub Actions artifact ID **11868999004**) contains the full development-only comparison JSON, training image receipt, separate baseline/candidate `best.pt` files, and both training CSV logs. The ZIP is **not** a new official Phase 23 checkpoint or independent flight-safety evidence.

## Exact measured values

Both runs used YOLO11n pretrained initialization, image size 320, batch 16, seed 20261013, **2 epochs** and the same declared training hyperparameters. The original validation images and labels were byte-identical for both arms. All **64** validation images came from the existing KIOS source videos, not new capture sessions.

| Development validation metric | Original-train baseline | Train + augmentations | Candidate − baseline |
| --- | ---: | ---: | ---: |
| Precision | 0.187348 | 0.659904 | +0.472556 |
| Recall | 0.171875 | 0.234375 | +0.062500 |
| mAP50 | 0.062513 | 0.246161 | +0.183648 |
| mAP50–95 | 0.041711 | 0.162624 | +0.120912 |

**Source:** original `comparison.json` in the successful Action artifact; no retrospective protected test statistics are used here.

## Data identities and authenticated output

- Official source: historical KIOS split manifest SHA-256 `32623634069c4f3082b79a6a42bca408c636f4b626e5f7691276257999544905`
- Original training: **252** labeled images. Original validation: **64** labeled images, unchanged.
- Generated variants: **504 train-only** images, including 93 blur, 111 low-light, 106 noise, 97 partial occlusion and 97 mixed. The candidate training directory has **756** images (252 originals plus 504 variants).
- Augmentation receipt SHA-256: `d4c204de344b6cf8b01cdc6d927e92793fa6b1e0094166b91e9e0f689556a793`
- Baseline `best.pt` SHA-256: `d855148f5c4005114e2bc5cc14e8258133aa4790c7a3370c6877464ba9322ed9`
- Candidate `best.pt` SHA-256: `cc52556d9bf77186a19c76bbceefc04cb8aac3cd9b90d906edb11285f34c32b5`
- `protected_test_evaluated: false`; `independent_validation: false`; `model_improvement_established: false`.

## Interpretation and next experiment

This **does not isolate the effect of camera augmentation**. In the same two epochs, the candidate processes three times as many training images and therefore receives roughly three times as many optimizer steps. The two training arms also share the same two original KIOS source-video sessions with the development validation split. This is an intentionally small proof-of-execution, not a fair causal ablation or a new benchmark conclusion.

The observed pilot mAP50 difference is a **measured development signal** only. It is not comparable directly to the historical Phase 23 protected-test aggregates, and we must not rename this newly trained candidate "Phase 23 robust" or replace the archived Phase 23 weights.

Next: preregister a **matched-optimization-budget** comparison and separately inspect untouched development-frame errors under controlled conditions, rather than repeatedly evaluating protected KIOS test frames. Only after Phase 26 admits genuinely independent labeled camera sessions, including negative examples, can a prospective independent reliability evaluation be run. This code is research software and not for aircraft control.

> Historical provenance: this experiment was originally introduced as PR #203 under the temporary \"Phase 27\" label. The label was subsequently removed to honor the pre-existing requirement not to create new phases. Existing GitHub Actions run names, archive contents, and recorded hashes are retained without alteration. This is model-development work within the existing research, not a new research phase.
