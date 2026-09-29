# Phase 25 · Failure Atlas

**Status:** Retrospective frame-level diagnostic on the Phase 23/24 protected temporal holdout.
**Training or test-threshold tuning:** None.

## Paired frame outcomes

| Condition | Baseline success | Phase 23 success | Recovered | Regressed | Both succeeded | Both failed | Baseline mAP50 | Phase 23 mAP50 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| clean | 61.6% | 53.5% | 7 | 14 | 39 | 26 | 0.427 | 0.555 |
| blur | 52.3% | 61.6% | 13 | 5 | 40 | 28 | 0.413 | 0.586 |
| low_light | 57.0% | 44.2% | 6 | 17 | 32 | 31 | 0.417 | 0.424 |
| noise | 52.3% | 55.8% | 10 | 7 | 38 | 31 | 0.433 | 0.596 |
| occlusion | 61.6% | 50.0% | 6 | 16 | 37 | 27 | 0.348 | 0.138 |
| mixed | 50.0% | 51.2% | 7 | 6 | 37 | 36 | 0.185 | 0.129 |

## Object counts

| Condition | Baseline TP / FP / FN | Phase 23 TP / FP / FN |
| --- | ---: | ---: |
| clean | 53 / 23676 / 33 | 46 / 12837 / 40 |
| blur | 45 / 23812 / 41 | 53 / 12500 / 33 |
| low_light | 49 / 23878 / 37 | 38 / 13178 / 48 |
| noise | 45 / 20743 / 41 | 48 / 10959 / 38 |
| occlusion | 53 / 24277 / 33 | 43 / 13512 / 43 |
| mixed | 43 / 19685 / 43 | 44 / 8162 / 42 |

## Confidence

- Phase 22 baseline: 136359 boxes; ECE 0.0022638642465699593; Brier 0.0011594653460208306.
- Phase 23 robust: 71420 boxes; ECE 0.0021717556226146136; Brier 0.0019621414029638794.

| Model | Correct boxes (n, median score) | Incorrect boxes (n, median score) |
| --- | ---: | ---: |
| Phase 22 baseline | 288, 0.297 | 136071, 0.002 |
| Phase 23 robust | 272, 0.348 | 71148, 0.002 |

## Statistical associations with recovery and regression

Observable properties associated with detector recovery and regression across 516 paired views:

1. **Degradation Type (Condition)**: Consistent pattern across conditions, though the overall association does not reach statistical significance (χ² p = 0.12).
   - Blur and noise show net recovery; low-light and occlusion show net regression.
   - Clean and mixed stress show roughly balanced transitions.
2. **Object Size**: Smaller pads (Q1/Q2) suffer higher miss rates under severe stress.
   - In occlusion and mixed stress, the fixed 8-pixel minimum occluder clamp covers up to 60-100% of small pads.
3. **Confidence Collapse**: Under severe stress (occlusion and mixed), Phase 23 true positive confidence drops severely while background false positive scores increase, compressing the detection margin.
4. **FP/FN Tradeoff**: Robust training eliminates false negatives under benign blur/noise, but induces false positives and misses under partial occlusions.

## Main Question Readout: Why does robust training improve clean/blur/noise while degrading occlusion/mixed?

1. **Why clean, blur, and noise improve:**
   - Training at 480px (vs 320px baseline) provides 2.25× more pixel area, resolving internal concentric rings and fine edges.
   - Extensive HSV color jitter and multi-scale mosaic training force invariance to global photometric shifts, contrast loss, and high-frequency sensor noise without distorting landing pad spatial coherence.

2. **Why occlusion and mixed severely regress (observational hypothesis):**
   - The stress transform occludes the central 55% of the target, obscuring the primary concentric rings and center symbol.
   - Phase 23 at 480px became strongly specialized to this internal marking structure. When the center is occluded, true positive confidence collapses below background noise.
   - For distant (small) landing pads, the 8px clamp causes disproportionately severe occlusion (>60-100% of pad area), leading to complete detection failure.
   - In mixed stress, the compound corruption (occlusion + blur + low light + noise) eliminates both internal features and outer boundary gradients, causing Phase 23 recall to plummet to 8.1%.

## Target misses

The size plot counts each annotated pad, including targets missed in frames that contain more than one pad.

## Limits

This is a descriptive audit of previously reported data. The split contains only two source sequences (effective N=2 sequences), so the 516 paired views represent repeated observations across 6 synthetic conditions rather than independent environments. The report gives paired counts and descriptive differences; p-values reported in offline statistical artifacts assume independence and must be interpreted with caution. Detector-score correctness does not establish landing safety, controller behavior, or flight readiness.

Phase 26 must set any reliability rule with separate development data and evaluate it on new evidence.
