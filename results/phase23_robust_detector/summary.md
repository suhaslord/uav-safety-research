# Phase 23 · Robust Sim-to-Real Landing Perception

**Status:** Detector comparison on the protected KIOS temporal holdout. Gains are condition-dependent and severe-stress regressions remain.
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

- **Clean Recall**: Increased by **+20.9 percentage points** (from **38.4%** to **59.3%**); misses remain.
- **Clean Detection Quality**: mAP50 increased by **+12.9 percentage points** (from **0.427** to **0.555**).
- **Blur Condition**: mAP50 under motion blur increased from **0.413** to **0.586** (+17.3 percentage points), with recall rising to **57.0%**.
- **Sensor Noise Robustness**: mAP50 under noise stress improved to **0.596** (vs 0.433 baseline).
- **Remaining Frontier (Occlusion & Mixed)**: mAP50 regressed from **0.348 to 0.138** under occlusion and from **0.185 to 0.129** under mixed stress; recall also fell in both conditions. Aggregate detector metrics do not measure a safety fallback, controller response, or landing safety.
