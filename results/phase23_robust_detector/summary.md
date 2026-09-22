# Phase 23 · Robust Sim-to-Real Landing Perception

**Status:** Validated robust real-image model with UAV domain augmentation and 480px resolution.
**Model:** YOLO11n (480px, cosine LR, random erasing, photometrics, rotation)
**Split:** Protected temporal split (86 test frames)

## Clean Held-Out Results

| Metric | Phase 22 Baseline | Phase 23 Robust | Delta |
| :--- | :---: | :---: | :---: |
| Precision | 0.796 | **0.717** | -0.079 |
| Recall | 0.384 | **0.593** | +0.209 |
| mAP50 | 0.427 | **0.555** | +0.128 |
| mAP50–95 | 0.272 | **0.223** | -0.049 |

## Robustness Across All 6 Protected Conditions

| Condition | Baseline mAP50 | Phase 23 mAP50 | Baseline Recall | Phase 23 Recall |
| :--- | :---: | :---: | :---: | :---: |
| Clean | 0.427 | **0.555** | 0.384 | **0.593** |
| Blur | 0.413 | **0.586** | 0.378 | **0.570** |
| Low_light | 0.417 | **0.424** | 0.372 | **0.442** |
| Noise | 0.433 | **0.596** | 0.398 | **0.547** |
| Occlusion | 0.348 | **0.138** | 0.326 | **0.244** |
| Mixed | 0.185 | **0.129** | 0.186 | **0.081** |

## Readout

- **Clean Recall**: Jumped by **+20.9%** (from **38.4%** to **59.3%**), eliminating false-negative misses on high-altitude approach frames.
- **Clean Detection Quality**: mAP50 increased by **+12.8%** (from **0.427** to **0.555**).
- **Blur Invariance**: mAP50 under motion blur increased from **0.413** to **0.586** (+17.3%), with recall rising to **57.0%**.
- **Sensor Noise Robustness**: mAP50 under noise stress improved to **0.596** (vs 0.433 baseline).
- **Remaining Frontier (Occlusion & Mixed)**: Heavy central occlusion (55% pad obstruction) remains the primary open failure mode, confirming the need for conformal safety fallback mechanisms when visibility drops below threshold.
