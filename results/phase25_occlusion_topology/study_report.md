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
**YES, for at least one preregistered pairwise contrast**.
Performance differed significantly between `OUTER_RING` and `STRIPED` under the multiplicity-adjusted analysis ($\Delta = +5.24$ percentage points, $p = 0.002$). Other overall pairwise comparisons did not meet the multiplicity-adjusted significance threshold.

### Center vs. Outer Ring Contrast: Does Evidence Support Stronger Center Sensitivity?
**INCONCLUSIVE (Suggestive descriptive pattern in high-dose small-target subgroup, but not confirmatory across the full experiment)**.
- Across all dose levels, the overall difference between `CENTER` and `OUTER_RING` is not statistically significant: $\Delta = -0.024$ [95% CI: $-0.052, +0.001$], $p = 0.062$.
- In the exploratory subgroup of small/distant targets (`land_pad`, $N=66$) at severe occlusion (achieved dose $\ge 0.50$), an observed descriptive penalty of $9.28$ percentage points was noted ($34.1\%$ success for `CENTER` vs. $43.4\%$ for `OUTER_RING`, nominal unadjusted $p = 0.012$), but this subgroup finding did not meet the preregistered multiplicity-adjusted threshold ($\alpha_{\text{adj}} = 0.00833$).

### Striped & Random Patch Occlusions:
- **`STRIPED`**: Exhibits the lowest overall success rate ($0.498$, [95% CI: $0.405, 0.599$]). While resilient on small targets, alternating stripe patterns severely degrade large concentric targets ($76.6\%$ success at dose $\ge 0.50$ compared to $>93\%$ for contiguous geometries).
- **`RANDOM_PATCH`**: Tracks contiguous center occlusion closely ($0.522$), with no significant difference from `CENTER` ($\Delta = +0.004$, $p = 0.740$).

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

## 3. Pairwise Topology Contrasts (Bonferroni-Adjusted $\alpha = 0.00833$)

| Comparison | Mean Difference | 95% Clustered CI | Two-Tailed $p$-value | Significant (Adjusted $\alpha=0.00833$) |
| :--- | :---: | :---: | :---: | :---: |
| **CENTER vs. OUTER_RING** | -0.0239 | [-0.0520, +0.0008] | 0.0620 | NO |
| **CENTER vs. STRIPED** | +0.0285 | [-0.0186, +0.0737] | 0.2260 | NO |
| **CENTER vs. RANDOM_PATCH** | +0.0043 | [-0.0194, +0.0271] | 0.7400 | NO |
| **OUTER_RING vs. STRIPED** | +0.0524 | [+0.0155, +0.0915] | 0.0020 | **YES** |
| **OUTER_RING vs. RANDOM_PATCH** | +0.0282 | [+0.0070, +0.0527] | 0.0100 | NO (Nominal $p=0.010$) |
| **STRIPED vs. RANDOM_PATCH** | -0.0242 | [-0.0621, +0.0140] | 0.2020 | NO |

---

## 4. Dose-Response & Monotonicity Analysis

Empirical binned success rates across the 8 common-support dose bins exhibit **non-monotonic fluctuations** due to frame-level variance and discrete image composition:
- `OUTER_RING` success in bin $[0.00, 0.05)$ is $54.7\%$, falls to $47.2\%$ in $[0.05, 0.15)$, rises to $66.9\%$ in $[0.45, 0.55)$, and ends at $59.1\%$ in $[0.65, 0.75)$.
- `CENTER` success similarly fluctuates ($53.3\%$ in clean bin, $59.4\%$ in $[0.05, 0.15)$, $50.1\%$ in $[0.35, 0.45)$, and $45.8\%$ in $[0.65, 0.75)$).
- **Conclusion on Monotonicity**: Empirical binned observations are **NOT strictly monotonic**. Overall downward trends are observed primarily in fitted parametric and segmented regressions for `CENTER`, `STRIPED`, and `RANDOM_PATCH`.

---

## 5. Scientific Interpretations & Epistemic Boundaries

### Tier 1: Directly Demonstrated Findings (Empirical Facts)
1. **Confirmatory Pairwise Difference**: `OUTER_RING` achieves significantly higher success than `STRIPED` under the multiplicity-adjusted analysis ($\Delta = +5.24$ percentage points [95% CI: $+1.55, +9.15$], $p = 0.002$).
2. **ED50 Differences**: `OUTER_RING` never falls below $50\%$ frame success across the entire tested dose range ($0.00 \dots 0.75$), whereas `STRIPED` crosses $50\%$ at dose $0.521$ and `CENTER` at dose $0.582$.
3. **Disruption on Large Targets**: Alternating striped occlusion degrades large concentric targets substantially more ($76.6\%$ success at severe doses) than contiguous occlusion ($>93\%$).
4. **Overall Center Contrast**: Across all 86 frames and all doses, `CENTER` vs. `OUTER_RING` difference is not statistically significant ($p = 0.062$). In the small-target high-dose subgroup, an observed descriptive difference of $9.28$ percentage points was noted ($p = 0.012$), but does not meet the family-wise adjusted threshold.

### Tier 2: Plausible Mechanistic Hypotheses (Supported Patterns, Unproven Mechanisms)
- One possible explanation consistent with the observed spatial proposal shifts is that proposal generation in the anchor-free head may rely on central concentric gradients to anchor candidate boxes. When the center is occluded, proposals may either fail to exceed confidence thresholds or shift in centroid, lowering IoU below 0.50.
- When the outer ring is occluded, the remaining central concentric rings may provide sufficient gradient symmetry for localization.
- *Note*: Internal feature activations were not directly ablated in this study; these statements represent consistent hypotheses rather than measured internal mechanisms.

### Tier 3: Unsupported Speculations (What this study does NOT establish)
- We do **NOT** claim this proves the detector has learned an abstract "bullseye concept".
- We do **NOT** claim these findings generalize to real physical occluders (e.g., foliage, quadrotor arms, landing gear) which have distinct textures, shadows, and non-neutral spectral signatures.
- Results are strictly valid for the 86 tested frames under synthetic neutral-gray occlusion.
