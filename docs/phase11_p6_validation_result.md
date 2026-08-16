# Phase 11 P6 frozen validation result — source-conditional continuity calibration

## Status

**FROZEN PROTECTED VALIDATION RESULT — MIXED / FAILED OVERALL**

Evidence role: `phase11_p6_frozen_candidate_validation`

P6 candidate-freeze workflow:

- run: `31972988822`
- scientific freeze head: `33e6ff85baa71f796bdcdb7dab2bc26f14b8f71a`
- candidate artifact ID: `9270300062`
- candidate artifact digest: `sha256:09a5b14a6ab374007b3d577dfaab41a195a44f94d2058bd0b57bcbd3f6dac4ca`
- candidate JSON SHA-256: `2bbb91fd0cb45ef11ba4411b406f4b311eff8c5d24020a7e7a64df823ac68073`

Protected validation:

- seed: `286286` — now permanently seen
- families: `99..101`
- workflow run: `31973115295`
- workflow head: `8c73d808d9042cced7f615194e777b842bb0cd34`
- validation artifact ID: `9270332403`
- validation artifact digest: `sha256:7a40da228e9121dbb5be03d514b0db1c3ad51b78fe05795722fe27aefde1cbe3`
- `validation_frames.csv` SHA-256: `468746447fcd325fc5923b1a139e511e454f49854180d32fc00216a4fec14eee`
- `validation_result.json` SHA-256: `f5c97f29c1d6c9613fcd2c4ba49c42e444703b2260271ec1cec8dc2392ce3254`

The validation workflow verified that the P6 scientific script, invariant tests, and preregistration were unchanged from the freeze SHA and verified the exact candidate JSON digest before exposing validation.

## Preregistered protected-validation result

| Gate | Frozen result | Verdict |
|---|---:|---|
| H1 useful availability | `90.42%` | FAIL (`>=92%` required) |
| H2 lateral 95% overall coverage | `91.78%` | PASS |
| H2 altitude 95% overall coverage | `90.48%` | PASS |
| H3 calibration-curve MACE | `0.05648` | PASS |
| H4 lateral median half-width / p95 error | `0.521x` | PASS |
| H4 lateral p95 half-width / p95 error | `1.828x` | PASS |
| H4 altitude median half-width / p95 error | `0.598x` | PASS |
| H4 altitude p95 half-width / p95 error | `0.827x` | PASS |
| H5 continuity lateral 95% coverage | `99.28%` | FAIL (`<=99%` required) |
| H5 continuity altitude 95% coverage | `63.77%` | FAIL |
| H5 continuity lateral p95 width / error | `1.236x` | PASS component |
| H5 continuity altitude p95 width / error | `0.343x` | PASS component but reflects undercoverage |
| H6 base lateral 95% coverage | `90.89%` | PASS |
| H6 base altitude 95% coverage | `93.64%` | PASS |
| H6 base lateral p95 width / error | `0.700x` | PASS |
| H6 base altitude p95 width / error | `1.033x` | PASS |
| H7 trajectory shift AUROC | `0.9462` | diagnostic PASS |

Overall preregistered verdict: **MIXED / FAILED**.

## Error and availability diagnostics

Across all P6 available validation outputs:

- availability: `1302 / 1440 = 90.42%`;
- lateral MAE: `0.09651 m`;
- lateral p95 error: `0.37870 m`;
- altitude MAE: `0.24005 m`;
- altitude p95 error: `0.85674 m`.

Source populations:

- base outputs: `1164` rows (`80.83%` of truth-visible frames);
- continuity extensions: `138` rows (`9.58%`);
- unavailable: `138` rows (`9.58%`).

The base-output population remained inside its preregistered calibration and efficiency gates. The dominant reliability failure is therefore specific to the continuity-extension population.

## Read-only post-exposure forensics

The following diagnostics are **descriptive only**. They are not a license to change P6 and re-evaluate seed `286286`.

Compared with the seen P6 transfer split:

- continuity rows increased from `64` to `138`;
- continuity altitude p95 error increased from about `0.489 m` to `1.495 m`;
- continuity lateral p95 error increased from about `0.466 m` to `0.560 m`;
- altitude local-slope use at `>=99%` of the fit-frozen slope cap increased from about `9.4%` of continuity rows to about `35.5%`;
- the protected-validation continuity horizon counts were `64` at horizon 3, `43` at horizon 4, and `31` at horizon 5;
- among still-unavailable protected-validation rows with at least two prior genuine anchors, `22` were at horizon 6 and `15` at horizon 7; `42` unavailable rows occurred before two genuine anchors existed.

A reconstruction using only already-frozen rows also shows that the absolute altitude error of the latest genuine anchor is strongly associated with the later continuity altitude error in this validation split. That anchor truth error is **not inference-visible**, so it cannot be used as a P7 input. It instead motivates an inference-visible anchor-consistency diagnostic: compare each newest genuine anchor against the trend implied by earlier genuine anchors before using it as the intercept for extrapolation.

## Interpretation

P6 proves that pooled calibration was not the whole problem.

1. Source-conditional calibration fixed the P5 seen-transfer overcoverage and passed every P6 development gate.
2. Under a different protected composition set, ordinary/base outputs remained reasonably calibrated.
3. Continuity outputs changed regime: high-slope and poor-anchor cases became much more common, especially on altitude.
4. A single `continuity_extension` calibration group cannot compensate for a continuity point estimator whose anchor/intercept quality changes under stronger compositional shift.
5. The next revision should therefore improve the **causal robustness of the continuity state** and expose anchor-consistency information to uncertainty calibration, rather than adding another post-hoc scalar multiplier.

No P6 parameter, source group, horizon, damping constant, model coefficient, calibration quantile, or gate was changed after validation exposure.

## Next scientific boundary

Do **not** tune on seed `286286`.

A P7 method change requires completely new fit/calibration/development/validation evidence and a new preregistration before generation.

A principled P7 direction is a robust genuine-anchor trend for continuity only:

- retain only genuine perception outputs as anchors;
- fit a causal robust line from the last up to three genuine anchors rather than using the newest anchor value as the sole extrapolation intercept;
- expose an inference-visible anchor-trend innovation / slope-consistency signal to the reliability scale model;
- separately test whether a slightly longer bounded horizon can recover the remaining short-gap availability without sacrificing continuity-specific coverage.

A final Phase 11 frozen holdout remains unauthorized and still requires a separate explicit user approval at an exact future freeze checkpoint.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
