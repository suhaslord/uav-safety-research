# Phase 11 P8 development stop — innovation-clipped continuity

## Status

**DEVELOPMENT FROZEN — PROTECTED VALIDATION NOT EXPOSED**

P8 preregistration: `docs/phase11_p8_innovation_clipped_preregistration.md`

Freeze workflow:

- run: `31973942401`
- scientific freeze head: `5772f0b54d58c5f987eb96e61ce849e66516fd16`
- artifact ID: `9270540056`
- artifact digest: `sha256:e6c841b02a7c95e3ecf44fc9770856ab5e51d5a262d5db9f9415f7292165f8fb`
- `candidate_freeze.json` SHA-256: `871c625c7de47b7d06b7a4bac0b46bb658bbce1d180ab5ad42973ec1e00d4248`
- `transfer_result.json` SHA-256: `4c956c4fe27c6a03750f7a92cf083ff6101690bdb9569925a9beff9dca6e9ca1`

The pre-generation invariant tests passed before P8 development evidence was generated.

## Exposure ledger

The completed freeze run generated the P8 development evidence, so these seeds are permanently seen:

- fit: `352352`
- single-factor calibration: `363363`
- continuity adaptation: `374374`
- compositional transfer calibration: `385385`

Protected validation seed `396396` was **not generated or exposed** and is retired with P8 rather than recycled.

## Seen transfer-calibration result

Evidence role: `phase11_p8_seen_transfer_calibration`

| Gate | Result | Verdict |
|---|---:|---|
| H1 availability | `98.26%` | PASS |
| H2 lateral 95% coverage | `95.12%` | PASS |
| H2 altitude 95% coverage | `95.12%` | PASS |
| H3 calibration MACE | `0.000890` | PASS |
| H4 lateral median half-width / p95 error | `1.162x` | PASS component |
| H4 lateral p95 half-width / p95 error | `2.862x` | FAIL |
| H4 altitude median half-width / p95 error | `1.370x` | FAIL |
| H4 altitude p95 half-width / p95 error | `1.854x` | PASS component |
| H5 continuity lateral 95% coverage | `95.65%` | PASS component |
| H5 continuity altitude 95% coverage | `95.65%` | PASS component |
| H5 continuity lateral p95 half-width / error | `4.477x` | FAIL |
| H5 continuity altitude p95 half-width / error | `4.486x` | FAIL |
| H6 base lateral 95% coverage | `95.07%` | PASS component |
| H6 base altitude 95% coverage | `95.07%` | PASS component |
| H6 base lateral p95 half-width / error | `3.637x` | FAIL |
| H6 base altitude p95 half-width / error | `2.460x` | FAIL |
| H7 trajectory shift AUROC | `0.9905` | diagnostic PASS |

Overall preregistered development result: **MIXED / FAILED**.

Because H4, H5, and H6 failed, P8 is not eligible for protected validation.

## Point-error / continuity diagnostics

Across all available transfer outputs:

- availability: `2830 / 2880 = 98.26%`;
- lateral MAE: `0.11189 m`;
- lateral p95 error: `0.40384 m`;
- altitude MAE: `0.24801 m`;
- altitude p95 error: `0.95959 m`.

Base-output p95 errors were `0.31787 m` lateral and `0.72336 m` altitude, while p95 half-widths were `1.15597 m` and `1.77927 m` respectively.

Innovation-clipped-continuity p95 errors were `1.13568 m` lateral and `2.02836 m` altitude, while p95 half-widths were `5.08432 m` and `9.09999 m` respectively.

Continuity rows by horizon:

- horizon 3: `142`;
- horizon 4: `60`;
- horizon 5: `27`;
- horizon 6: `13`;
- horizon 7: `11`.

Point-error tails grew monotonically with horizon. At horizon 3, p95 error was about `0.951 m` lateral / `1.541 m` altitude; by horizon 7 it was about `1.888 m` / `2.482 m`.

## Innovation diagnostics

Fit-frozen innovation caps:

- lateral: `0.0626662 m`;
- altitude: `0.181433 m`.

On seen transfer continuity rows:

- median lateral raw innovation: `0.13534 m` (`~2.16x` cap);
- median altitude raw innovation: `0.33197 m` (`~1.83x` cap);
- p95 innovation-cap utilization saturated at the preregistered maximum `3.0` on both axes;
- **88.93%** of continuity rows clipped at least one axis.

Fit-frozen velocity caps:

- lateral: `0.112627 m/frame`;
- altitude: `0.155270 m/frame`.

On continuity rows, about `17.4%` lateral and `37.9%` altitude slopes were at `>=99%` of the velocity cap.

Still-unavailable rows:

- `33` insufficient-anchor rows;
- `17` gaps beyond the seven-frame horizon.

## Interpretation

P8 solved the P7 method counterexample and produced enough adaptation/transfer continuity evidence, but the resulting uncertainty stack was too conservative.

1. Innovation clipping was active on almost nine of ten continuity rows, so the fit q95 innovation cap did not behave like a rare robustness safeguard under compositional shift.
2. Coverage remained exceptionally accurate because transfer conformal calibration compensated for the shifted error distribution.
3. The compensation was too expensive: both continuity and base-output interval tails became far wider than preregistered efficiency limits.
4. The problem is therefore no longer simply undercoverage. The current combination of learned base scale, continuity correction, and source-conditional transfer multipliers can manufacture honest coverage by inflating intervals too aggressively.
5. P9 should simplify uncertainty rather than add another correction layer.

No P8 cap, blend coefficient, horizon, scale model, correction model, conformal multiplier, or gate was changed after transfer exposure.

## Next revision

P9 should use completely fresh evidence and test two tightly scoped changes:

1. **Soft innovation weighting instead of hard clipping.** Use a preregistered analytic weight based on a fit-frozen robust innovation scale, so modest compositional innovation is downweighted smoothly rather than clipped on nearly every row.
2. **Direct grouped conformal absolute-error intervals.** Remove the learned scale model and adaptation correction from the P9 uncertainty path. Calibrate direct absolute residual radii in predeclared source/horizon groups so coverage cannot be rescued only by compounding multiple learned multipliers.

A reasonable P9 grouping is:

- `base_output`;
- continuity horizon `3`;
- continuity horizons `4–5`;
- continuity horizons `6–7`.

Group minimums and fallback behavior must be preregistered before P9 generation.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
