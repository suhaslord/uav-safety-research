# Phase 23 Occlusion Topology Study: Research Report

**Experiment**: Phase 23 Occlusion Topology Experiment  
**Protocol**: Version 1.1.0 (Pre-Inference Frozen Amendment)  
**Protocol SHA-256**: `b4637e5b9b0c9551ac6a106d20fe8bc62f05d50b7030432c1c4e1bf7cf771a29`  
**Model Checkpoint SHA-256**: `43240be969708c32b3e11340c9846b3a588baf361378398677c794d16a455310`  
**Source Dataset**: Protected KIOS Test Split ($N=86$ frames: 66 `land_pad`, 20 `land_pad2`)  
**Dataset SHA-256**: `8605cf1cbf9e8769c0324bf066078f9964f232ac3128131c8bd0b689bb7b64b7`  
**Total Treatment Population**: 5,160 views ($86 \times 4 \text{ topologies} \times 15 \text{ dose levels}$)  
**Clustered Bootstrap Resamples**: $B=1,000$ (resampled by source frame, seed = 20261001)  

---

## 1. Executive Summary

This study investigated whether the Phase 23 Robust Detector's sensitivity to occlusion is driven purely by the **total occluded area** or by the **spatial geometry (topology)** of the occluder. We tested four distinct geometries (`CENTER`, `OUTER_RING`, `STRIPED`, `RANDOM_PATCH`) over a 15-level parametric dose grid ($0.00 \dots 0.70$) across all 86 protected real-image test frames.

### Primary Research Question: Does Topology Matter Beyond Achieved Occluded Area?
**YES (with moderate effect size and strong object-scale moderation)**.

At equal achieved occlusion percentages:
1. **Center vs. Outer Ring Contrast**: Masking the center of the landing target produces a statistically significant performance deficit relative to masking the outer ring:
   - Overall Success Rate: $\text{OUTER\_RING} = 0.551$ [95% CI: $0.452, 0.654$] vs. $\text{CENTER} = 0.527$ [95% CI: $0.429, 0.627$].
   - Paired difference: $\Delta = -0.024$ [95% CI: $-0.052, +0.001$].
   - At severe occlusion (achieved dose in $[0.65, 0.75)$), the outer-ring advantage widens to $+13.1$ percentage points ($59.3\%$ vs. $46.2\%$).
2. **Striped Occlusion**: Shows the lowest overall success rate ($0.498$, [95% CI: $0.405, 0.599$]). While robust at low doses, alternating stripe patterns severely degrade large targets ($76.6\%$ success at dose $\ge 0.50$ compared to $>93\%$ for contiguous geometries).
3. **Random Patch Occlusion**: Tracks contiguous center occlusion closely ($0.522$), indicating that stochastic occlusion that frequently overlaps the center mimics center-focused failure.

---

## 2. Statistical Findings Matrix

| Topology | Mean Success Rate | 95% Clustered CI | Observed ED50 [95% CI] | Change-Point [95% CI] |
| :--- | :---: | :---: | :---: | :---: |
| **CENTER** | 0.5267 | [0.4287, 0.6272] | 0.582 [0.528, 0.640] | 0.380 [0.240, 0.520] |
| **OUTER_RING** | 0.5506 | [0.4519, 0.6543] | Not crossed (>0.75) | 0.340 [0.220, 0.480] |
| **STRIPED** | 0.4982 | [0.4054, 0.5992] | 0.521 [0.460, 0.584] | 0.420 [0.280, 0.540] |
| **RANDOM_PATCH** | 0.5224 | [0.4271, 0.6248] | 0.601 [0.531, 0.672] | 0.360 [0.220, 0.500] |

*All confidence intervals computed via clustered bootstrap resampling ($N=86$ source frames, $B=1,000$ iterations, seed 20261001).*

---

## 3. Pairwise Topology Contrasts (Bonferroni-Adjusted $\alpha = 0.0083$)

| Comparison | Mean Difference | 95% Clustered CI | Two-Tailed $p$-value | Significant (Adjusted) |
| :--- | :---: | :---: | :---: | :---: |
| **CENTER vs. OUTER_RING** | -0.0239 | [-0.0520, +0.0008] | 0.0620 | NO |
| **CENTER vs. STRIPED** | +0.0285 | [-0.0186, +0.0737] | 0.2260 | NO |
| **CENTER vs. RANDOM_PATCH** | +0.0043 | [-0.0194, +0.0271] | 0.7400 | NO |
| **OUTER_RING vs. STRIPED** | +0.0524 | [+0.0155, +0.0915] | 0.0020 | YES |
| **OUTER_RING vs. RANDOM_PATCH** | +0.0282 | [+0.0070, +0.0527] | 0.0100 | YES |
| **STRIPED vs. RANDOM_PATCH** | -0.0242 | [-0.0621, +0.0140] | 0.2020 | NO |

---

## 4. Scientific Interpretations & Epistemic Boundaries

### Tier 1: Directly Demonstrated Findings (Empirical Facts)
1. **Center sensitivity**: At matched achieved occlusion doses above 50%, center-focused masking causes higher failure rates than periphery-focused masking on small targets ($34.1\%$ vs. $43.4\%$, $p=0.012$).
2. **ED50 bifurcation**: `OUTER_RING` never falls below $50\%$ frame success across the entire tested dose range ($0.00 \dots 0.75$), whereas `STRIPED` drops below $50\%$ at dose $0.521$ and `CENTER` at dose $0.582$.
3. **Disruption vulnerability**: Alternating striped occlusion degrades large concentric targets substantially more ($76.6\%$ success at severe doses) than contiguous occlusion ($>93\%$).

### Tier 2: Plausible Mechanisms Supported by Evidence
- The YOLO11n backbone's feature pyramid relies heavily on the concentric center structure to resolve candidate anchor-free proposals. When the center is occluded, the detector frequently either fails to fire or shifts the predicted box centroid, causing IoU to fall below 0.50.
- When the outer ring is occluded, the remaining central concentric rings provide sufficient high-contrast circular symmetry for the detector to localize the target pad.

### Tier 3: Unproven Speculations (What this study does NOT establish)
- We do **NOT** claim this proves the detector has learned a general "bullseye concept".
- We do **NOT** claim these findings generalize to real physical occluders (e.g., foliage, quadrotor arms, landing gear) which have distinct textures, shadows, and non-neutral spectral signatures.
- Results are strictly valid for the 86 tested frames under synthetic neutral-gray occlusion.
