# Real landing-pad detector benchmark

**Status:** valid protected real-image baseline after fixing the one-class label export.  
**Workflow run:** `34932763449`  
**Source commit:** `b569da0012e4ed74c420cbbd15e25665c9850c48`  
**Artifact SHA-256:** `7080c8243c1d7cb85a63f81ea0531eda34dd1f18616f7b4dfdc869a2379c9833`

## Setup

- **Dataset:** KIOS Aerial Landing Pad, Unreal Engine Dataset (2024), real-video subset
- **Labeled real frames:** 422
- **Model:** `yolo11n.pt` pretrained initialization
- **Training:** up to 12 epochs, 320 px, batch 16, seed `20260915`
- **Split:** temporal per source video — 60% train, 15% validation, 5% embargo, 20% protected test
- **Counts:** 252 train, 64 validation, 20 embargoed, 86 protected test
- **Training ingestion check:** 252 images, 0 backgrounds, 0 corrupt
- **Validation ingestion check:** 64 images, 0 backgrounds, 0 corrupt
- **Protected-test ingestion check:** 86 images, 0 backgrounds, 0 corrupt

The source KIOS label files can contain an additional class. For this one-class landing-pad baseline, the split builder keeps the selected landing-pad boxes and rewrites them as class `0`. This prevents the class-count mismatch that invalidated the first detector attempt.

## Clean held-out result

| Metric | Protected-test result |
| --- | ---: |
| Precision | **0.796** |
| Recall | **0.384** |
| mAP50 | **0.427** |
| mAP50–95 | **0.272** |

## Held-out robustness

| Condition | Precision | Recall | mAP50 | mAP50–95 |
| --- | ---: | ---: | ---: | ---: |
| Clean | 0.796 | 0.384 | 0.427 | 0.272 |
| Blur | 0.844 | 0.378 | 0.413 | 0.271 |
| Low light | 0.787 | 0.372 | 0.417 | 0.269 |
| Noise | 0.895 | 0.398 | 0.433 | 0.262 |
| Occlusion | 0.622 | 0.326 | 0.348 | 0.166 |
| Mixed | 0.597 | 0.186 | 0.185 | 0.081 |

The stress images are deterministic transformations of the **86 protected test frames**. None of the stress conditions is used for training in this first detector baseline.

## Readout

The baseline is much more meaningful than the earlier synthetic-only estimator because it is trained and evaluated on real camera frames with a protected temporal split. It is still limited: clean-test recall is only **0.384**, and the mixed degradation is the clearest failure mode, reducing mAP50 from **0.427** to **0.185** (about a **56.7% relative drop**). Occlusion also produces a substantial drop. Noise happens to score slightly above clean on mAP50 in this single baseline run, so the result should not be simplified into “every degradation always makes performance worse.”

This remains a research baseline, not evidence of flight safety or certification.
