# Phase 12 lateral width-tail forensic note

## Status

**PERMANENTLY-SEEN DEVELOPMENT EVIDENCE ONLY.**

This note uses only Phase 12 scale-fit (`880880`), calibration A (`891891`), calibration B (`902902`), and development (`907907`) evidence. It does not generate or inspect transfer (`913913`), protected validation (`924924`), final holdout (`935935`), closed Phase 11 protected (`858858`), or retired Phase 11 P15-v2 (`869869`) evidence.

The diagnostic workflow is `.github/workflows/phase12-forensics.yml`; its first successful run is `34004467895` and artifact `phase12-width-tail-forensics` has artifact id `9980520288`.

## Question

Why does Phase 12 iteration 2 still miss the locked overall lateral H4 p95 half-width / p95-error threshold (`2.3485x` observed vs `<=2.25x`) while median width, coverage, calibration, and honesty gates already pass?

## Finding 1 — the width tail is a continuity-allocation problem

The iteration-2 lateral 95% half-width tail is dominated by the two longest continuity bands.

| Seen role | Top-5%-width rows | H4-5 among top width | H6-7 among top width | Top-width rows also in top-5%-error |
|---|---:|---:|---:|---:|
| scale fit | 759 | 145 | 614 | 27.4% |
| calibration A | 763 | 188 | 575 | 28.2% |
| calibration B | 788 | 140 | 648 | 22.8% |
| development | 576 | 105 | 471 | 20.7% |

The core mismatch is therefore not simply that long-horizon continuity is difficult. The current scale makes long-horizon rows wide almost deterministically, but most of the widest rows are not the rows with the largest realized errors.

Development group results reinforce this:

| Group | Rows | lateral p95 error (m) | lateral p95 half-width (m) | 95% coverage |
|---|---:|---:|---:|---:|
| base | 4762 | 0.5687 | 0.7962 | 94.33% |
| H3 | 723 | 1.1122 | 1.4138 | 97.37% |
| H4-5 | 980 | 1.2657 | 1.5763 | 97.35% |
| H6-7 | 627 | 1.4139 | 1.7772 | 97.45% |
| rescue | 4234 | 0.2057 | 0.2065 | 95.06% |

All three continuity bands are conservative on development. More global continuity shrinkage would attack the symptom but would not fix which rows receive width.

## Finding 2 — severity explains width much better than it explains error

Within continuity rows, Spearman rank correlations were:

| Seen role | severity vs abs error | severity vs half-width | normalized lateral anchor innovation vs abs error | innovation vs half-width |
|---|---:|---:|---:|---:|
| scale fit | +0.154 | +0.459 | **+0.416** | +0.086 |
| calibration A | +0.145 | +0.480 | **+0.498** | +0.011 |
| calibration B | +0.065 | +0.458 | **+0.474** | -0.029 |
| development | **-0.003** | +0.406 | **+0.435** | -0.059 |

Iteration 2 therefore allocates width strongly according to severity even when severity has essentially no development rank relationship with actual continuity error. By contrast, anchor innovation consistently predicts error across all four permanently-seen environments while barely affecting current width.

`p9_anchor_innovation_lateral_abs` is computed by the unchanged P9 estimator from the recent genuine-anchor state before truth error is calculated. Dividing it by the already frozen P9 lateral innovation scale yields an inference-visible dimensionless reliability coordinate.

## Finding 3 — the highest-innovation continuity quartile is the difficult tail

For normalized lateral anchor innovation quartiles, current iteration-2 95% intervals are badly misallocated:

| Seen role | Q1 p95 error / coverage | Q2 | Q3 | Q4 (highest innovation) |
|---|---|---|---|---|
| scale fit | 0.676 m / 100% | 0.502 m / 100% | 0.741 m / 100% | **2.057 m / 87.3%** |
| calibration A | 0.766 m / 99.7% | 0.620 m / 100% | 0.729 m / 100% | **2.187 m / 81.2%** |
| calibration B | 0.706 m / 100% | 0.585 m / 100% | 0.658 m / 100% | **2.118 m / 82.9%** |
| development | 0.708 m / 100% | 0.631 m / 100% | 0.704 m / 99.7% | **1.836 m / 89.9%** |

The first three innovation quartiles are strongly overcovered while the highest-innovation quartile contains the actual difficult tail. This is exactly the structure a reliability-normalized uncertainty scale should address: move width from easy continuity rows toward genuinely unstable estimator states, rather than shrink all continuity intervals.

Gain carries essentially the same information with reversed sign because it is a deterministic consequence of the same soft innovation update. Lateral slope-cap utilization is also informative but materially weaker (error Spearman roughly `0.23–0.28`). Anchor innovation is therefore the lowest-capacity primary coordinate.

## Finding 4 — the calibration max rule is not the main problem

At 95% lateral coverage, calibration A/B normalized-radius max/min ratios are small:

- base: `1.0115x`
- H3: `1.0219x`
- H4-5: `1.0375x`
- H6-7: `1.0667x`
- rescue: `1.0101x`

The worst environment disagreement is only about 6.7%. Replacing the robust pointwise maximum with a less conservative aggregation is therefore not justified as the primary iteration-3 change.

## Iteration-3 conclusion

The evidence supports one small architectural change and argues against several alternatives:

1. **Use normalized anchor innovation as a continuity-only residual reliability coordinate.**
2. Keep the iteration-2 severity scale as the baseline rather than deleting severity entirely.
3. Fit the innovation effect only from fresh Phase 12 scale-fit evidence; do not choose coefficients from development.
4. Keep horizon groups, calibration environments, finite-sample conformal rule, and calibration-A/B maximum unchanged.
5. Keep base and independent-rescue uncertainty unchanged.
6. Keep the P14R point estimator, continuity path, rescue selection, velocity caps, innovation scales, availability decisions, and all H1-H11 definitions unchanged.

A separate iteration-3 preregistration must freeze the exact formula before the next `907907` development evaluation. Transfer remains unauthorized.

## Claim boundary

This remains simulation-only uncertainty research. `simulation_only = true`, `safety_acceptance = false`, and `controller_tuning_allowed = false` remain mandatory. No physical-flight, certification, production, or operational-safety claim is supported.
