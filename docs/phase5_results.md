# Phase 5 Robustness and Synthetic-Image Results

## Status

Phase 5 was run after the frozen V3 evaluation without retuning the V3 supervisor. The full GitHub Actions validation completed successfully after fixing a pandas 3 aggregation incompatibility in the seed-family summarizer.

The validation included:

- compile checks,
- the complete automated test suite,
- five unseen-seed families,
- six degradation-strength levels,
- four reference-quality levels,
- six reference-dropout levels,
- seven persistent-bias magnitudes, and
- 1,500 synthetic landing-pad images across five visual conditions.

These are simulation-only results. They are not evidence of real-aircraft safety.

---

## 1. Unseen seed families

Each family used 100 paired episodes per architecture for both `mixed` and `occlusion`.

### Mixed

Across five unseen seed families:

| Architecture | Mean success | Mean unsafe touchdown | Success range |
|---|---:|---:|---:|
| Baseline | 17.6% | 82.4% | 14%–21% |
| V2 | 17.2% | 82.8% | 14%–20% |
| **V3** | **97.6%** | **2.4%** | **96%–99%** |

V3 unsafe-touchdown rate ranged from **1% to 4%** across the five families.

### Occlusion

| Architecture | Mean success | Mean unsafe touchdown | Success range |
|---|---:|---:|---:|
| Baseline | 66.8% | 33.2% | 58%–81% |
| V2 | 66.2% | 33.8% | 57%–78% |
| **V3** | **98.8%** | **1.2%** | **97%–100%** |

This materially strengthens the original frozen result: the V3 effect was not limited to one held-out seed family.

---

## 2. Degradation-strength sweep

The frozen `mixed` perception profile was scaled from `0.60x` through `1.60x`. Noise, dropout probability, and persistent bias increase with severity; confidence is also reduced above `1.0x`.

| Severity | Baseline success | Baseline unsafe | V3 success | V3 unsafe | V3 abort | V3 timeout |
|---:|---:|---:|---:|---:|---:|---:|
| 0.60x | 77% | 23% | **99%** | **1%** | 0% | 0% |
| 0.80x | 41% | 59% | **96%** | **4%** | 0% | 0% |
| 1.00x | 10% | 90% | **97%** | **3%** | 0% | 0% |
| 1.20x | 2% | 98% | **98%** | **2%** | 0% | 0% |
| 1.40x | 2% | 98% | **94%** | **6%** | 0% | 0% |
| 1.60x | 1% | 99% | **92%** | **8%** | 0% | 0% |

V3 degrades gradually rather than collapsing as the stress level increases.

A useful caution appears in V2 at high severity: its unsafe-touchdown rate becomes numerically small only because it increasingly aborts or times out. At `1.40x`, V2 had 41% aborts and 55% timeouts; at `1.60x`, it had 82% aborts and 15% timeouts. This is the same safety-versus-availability failure mode identified earlier in the project.

---

## 3. Weaker and noisier reference estimates

The independent reference estimator was degraded by increasing both noise and update interval while the `mixed` perception profile remained fixed.

| Reference condition | Noise multiplier | Update interval | V3 success | V3 unsafe |
|---|---:|---:|---:|---:|
| Nominal | 1.0x | every 5 steps | **96%** | **4%** |
| Weaker 1 | 1.5x | every 7 steps | **96%** | **4%** |
| Weaker 2 | 2.0x | every 10 steps | **93%** | **7%** |
| Weaker 3 | 3.0x | every 15 steps | **81%** | **19%** |

This is the clearest Phase 5 limitation. V3 still strongly outperforms the single-stream systems in the weakest-reference condition, but its performance is meaningfully dependent on the quality and refresh rate of the independent evidence.

The next paper should therefore describe V3 as **robust to substantial reference degradation, not independent of reference quality**.

---

## 4. Reference-update dropout

Reference dropout probability was swept from 0% to 75%.

| Reference dropout | V3 success | V3 unsafe |
|---:|---:|---:|
| 0% | **98%** | 2% |
| 12% | **97%** | 3% |
| 25% | **100%** | 0% |
| 40% | **98%** | 2% |
| 60% | **99%** | 1% |
| 75% | **95%** | 5% |

The non-monotonic values are expected sampling variation at 100 episodes per point and should not be interpreted as dropout improving the system. The important result is that the architecture remained highly available even with substantial missing reference updates.

---

## 5. Persistent-bias magnitude

The `mixed` profile's noise and dropout were held fixed while lateral visual bias was swept from 0 to 1.20 m.

| Persistent bias | Baseline success | Baseline unsafe | V3 success | V3 unsafe |
|---:|---:|---:|---:|---:|
| 0.00 m | 100% | 0% | **100%** | 0% |
| 0.20 m | 95% | 5% | **99%** | 1% |
| 0.40 m | 64% | 36% | **97%** | 3% |
| 0.62 m | 5% | 95% | **99%** | 1% |
| 0.80 m | 1% | 99% | **100%** | 0% |
| 1.00 m | 0% | 100% | **100%** | 0% |
| 1.20 m | 0% | 100% | **100%** | 0% |

This is an unusually strong result and should be treated cautiously rather than overclaimed. The sweep still uses the same abstract redundant-estimator family and the same planar simulator. A stronger follow-up should include reference bias, correlated estimator errors, time-varying bias, and additional random families.

---

## 6. Synthetic image-perception benchmark

A standalone 96×96 grayscale landing-pad renderer and interpretable pixel estimator were tested on 300 images per condition, for 1,500 images total.

| Condition | Valid estimates | Mean abs. lateral error | 95th-percentile error | Mean confidence |
|---|---:|---:|---:|---:|
| Clean | 100% | 0.017 m | 0.031 m | 0.833 |
| Blur | 100% | 0.016 m | 0.030 m | 0.783 |
| Low light | 100% | 0.074 m | 0.255 m | 0.636 |
| Occlusion | 100% | 0.082 m | 0.194 m | 0.818 |
| Mixed | 100% | **0.344 m** | **1.002 m** | 0.518 |

### Important failure found

The estimator reported a **valid result for 100% of images**, even under severe `mixed` degradation. That means the first image front end does not yet have a meaningful abstention mechanism.

Under `mixed`:

- 46.7% of samples exceeded 0.25 m absolute error,
- 24.7% exceeded 0.50 m,
- 5.7% exceeded 1.00 m,
- yet every sample was still marked valid.

Confidence is directionally useful in low light and mixed degradation, but not fully calibrated. In particular, occlusion showed a positive confidence/error correlation in this benchmark, indicating that some larger errors can still receive higher confidence.

This is the main Phase 6 target.

---

# Phase 5 conclusion

The strongest conclusion supported by these experiments is:

> **Aegis V3's large improvement under persistent-bias and occlusion stress survives multiple unseen random seed families, stronger perception degradation, large reference dropouts, and a substantial range of visual-bias magnitudes. Its main measured weakness is dependence on the quality of the independent reference estimate.**

The synthetic-image experiment also identifies a new problem before image perception is connected to the controller:

> **The current pixel estimator is accurate in easy conditions but too willing to return a valid estimate under severe degradation.**

---

# Phase 6 plan

The next phase should not retune the frozen V3 result. It should test a new perception interface.

1. Add an explicit image-estimator abstention/invalid state.
2. Calibrate confidence against measured pixel-estimation error using a separate development dataset.
3. Generate temporal synthetic image sequences rather than independent frames.
4. Feed image-derived observations into the simulator through the same observation interface used by V3.
5. Compare:
   - abstract perception + V3,
   - image perception without safety supervision,
   - image perception + temporal filtering,
   - image perception + V3 redundant supervision.
6. Add harder image shifts: partial pad visibility, contrast inversion, shadows, clutter, structured occluders, and time-varying visual bias.
7. Keep all work simulation-only and preserve a new held-out evaluation set before reporting Phase 6 performance.
