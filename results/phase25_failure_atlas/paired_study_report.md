# Phase 23 Frame-Level Reconstruction and Paired Failure Atlas Study: Technical Report

**Document Status:** FROZEN RESEARCH ARTIFACT  
**Phase:** 25  
**Date:** 2026-09-30  
**Checkpoint SHA-256:** `43240be969708c32b3e11340c9846b3a588baf361378398677c794d16a455310`  
**Recovery Bundle SHA-256:** `a55531930988deeadf81853d00b63c7e589c6b7fd2270f57653abdb5cdd3e55d`  
**Protected Manifest SHA-256:** `8605cf1cbf9e8769c0324bf066078f9964f232ac3128131c8bd0b689bb7b64b7`  
**Evaluation Scope:** 86 protected frames across 6 stress conditions = 516 paired views  

---

## 1. Executive Summary

This study establishes the frame-level paired behavior of the robust Phase 23 detector against the Phase 22 baseline across 516 strictly verified views derived from 86 protected test frames under 6 conditions (clean, blur, low light, noise, occlusion, and mixed).

Starting from the authenticated GitHub Release recovery bundle (`phase23-checkpoint-recovery`), frame-level inference was executed under locked evaluation parameters (`imgsz=480, conf=0.001, iou=0.7, max_det=300`). Official Ultralytics evaluation confirmed exact reproduction of all 24 published aggregate metric cells (maximum absolute delta = `0.0000000000e+00`).

Across the 516 paired views:
- **Both Pass:** 223 views (43.2%)
- **Both Fail:** 179 views (34.7%)
- **Recovered (Phase 22 Fail → Phase 23 Pass):** 49 views (9.5%)
- **Regressed (Phase 22 Pass → Phase 23 Fail):** 65 views (12.6%)
- **Net Success Difference:** -3.1 percentage points (272 vs 288 passes)

---

## 2. Observations (Directly Demonstrated by the Data)

1. **Condition-Specific Asymmetry:**
   - **Blur:** Substantial net gain (+8 frames, +9.3 percentage points, 13 recovered vs 5 regressed).
   - **Noise:** Moderate net gain (+3 frames, +3.5 percentage points, 10 recovered vs 7 regressed).
   - **Mixed:** Marginal net gain (+1 frame, +1.2 percentage points, 7 recovered vs 6 regressed).
   - **Clean:** Net loss (-7 frames, -8.1 percentage points, 7 recovered vs 14 regressed).
   - **Low Light:** Net loss (-11 frames, -12.8 percentage points, 6 recovered vs 17 regressed).
   - **Occlusion:** Substantial net loss (-10 frames, -11.6 percentage points, 6 recovered vs 16 regressed).

2. **Statistical Significance of Paired Differences:**
   - **Overall (N = 516 views from 86 frames):** McNemar's continuity-corrected $\chi^2 = 2.0526$, asymptotic $p = 0.152$, two-tailed exact binomial $p = 0.1601$. The overall paired binary success difference does NOT achieve statistical significance at $\alpha = 0.05$.
   - **Clustered Bootstrap Interval (Clustered on Source Frame N = 86, B = 1000 resamples):** 95% CI for success rate difference is `[-0.093, +0.037]`. The confidence interval firmly spans zero.
   - **Continuous IoU Differences:** Paired Wilcoxon signed-rank test on matched IoU deltas yields $W = 53418.0, p = 8.9436e-05$, reflecting that while binary pass/fail shifts cancel out in aggregate, the continuous distribution of box IoUs exhibits statistically discernible perturbations across stress conditions.

3. **Target Area Stratification:**
   - In quartile Q1 (smallest targets, area ratio $\le 0.021$), Phase 23 achieves 31.0% success vs Baseline 32.6%.
   - In quartile Q4 (largest targets, area ratio $\ge 0.089$), Phase 23 achieves 74.4% success vs Baseline 81.4%.
   - Regressions occur across all target scales but are concentrated where baseline had high confidence on clean/occluded images.

---

## 3. Interpretations (Plausible Mechanisms Supported by Evidence)

1. **Specialization Trade-off:**
   Phase 23 was trained with heavy synthetic augmentation including Gaussian noise, blur, and chromatic perturbations. This robustification succeeded in maintaining target feature detection under frequency-domain degradation (blur and sensor noise). However, this tuning shifted the model's inductive bias away from high-contrast edge boundaries, leading to precision loss on pristine clean imagery and under-exposure in low-light views.

2. **Concentric Ring Geometric Vulnerability Under Occlusion:**
   The KIOS landing target consists of nested concentric circular rings. Under partial artificial occlusion, key annular segments are obscured. Because the detector learned specific spatial proportions of the full concentric pattern during robust training, partial masking destroys the holistic feature representation, triggering false negatives even when substantial target area remains visible.

---

## 4. Unproven Hypotheses for the Next Controlled Experiment

1. **Hypothesis 1 (Concentric Ring Masking Threshold):**
   Detector recall does not degrade smoothly with occluded target area; instead, it undergoes a critical collapse when the innermost bullseye ring is occluded, regardless of outer ring visibility.
   *Proposed Experiment:* A parametric synthetic sweep varying occlusion position (center-mask vs edge-mask vs stripe-mask) across controlled area fractions (10% to 70%).

2. **Hypothesis 2 (Confidence-Localization Decoupling Under Occlusion):**
   Under occlusion, detection box score drops drastically before spatial localization degrades; an adjusted scale-conditioned or context-aware threshold can recover lost true positives without increasing false alarms.
   *Proposed Experiment:* Receiver Operating Characteristic (ROC) analysis evaluating F1 score as a function of adaptive confidence thresholds under occlusion.

---

## 5. Explicit Limitations & Disclosures

- **Sample Size and Pseudoreplication:** The 516 evaluation views are generated from only **86 unique source frames** recorded across only **2 real-world flight sessions** (`land_pad` with 66 frames and `land_pad2` with 20 frames). The 6 condition views for each frame are non-independent transformations. All statistical inferences must be interpreted with clustered-frame awareness.
- **Derived Stress Transforms:** The blur, noise, low light, occlusion, and mixed conditions are synthetically injected transformations, not naturally varying outdoor environmental sequences.
- **Retrospective Nature:** This study is an audit of frozen historical models. No model training, hyperparameter optimization, or threshold calibration was performed on this test set.
- **No Direct Landing-Safety Claim:** Bounding-box detection metrics (mAP, IoU, recall) on static image frames do not directly establish closed-loop UAV flight or autonomous landing safety.
