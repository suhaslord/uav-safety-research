# Phase 11 P3 development stop — learned-scale composition transfer

## Status

**DEVELOPMENT FROZEN — PROTECTED VALIDATION NOT EXPOSED**

P3 preregistration: `docs/phase11_p3_learned_scale_preregistration.md`

Freeze workflow:

- run: `31970370012`
- head SHA: `1b93325eeea06410402b49683b28ee1325430bc3`
- artifact ID: `9269620496`
- artifact digest: `sha256:a3feed59c58ca1d53a5aecd1a95c2d9bb9bb3eecb1c58c187d5220e4a51ac7f3`
- candidate JSON SHA-256: `1f882617ccb6048e00e63b32f124350495bc9b68142913ee05d05ac77b723859`
- transfer-result SHA-256: `7314a3aee1a29ac769ba46f3154da85b666ed043aae7c877eb2d2e1bcd90335e`

The freeze workflow passed all P3 invariant tests and verified that protected validation seed `154154` was not generated. No `validation_frames.csv` or `validation_result.json` was created.

## Seen transfer-calibration result

Evidence role: `phase11_p3_seen_transfer_calibration`

P3 substantially improved the P2 interval-tail pathology while preserving excellent calibration:

- lateral 95% coverage: `95.11%` — PASS;
- altitude 95% coverage: `95.11%` — PASS;
- mean absolute coverage error across 50/68/80/90/95 targets: `0.000815` — PASS;
- trajectory-level shift AUROC: `0.98264` — PASS;
- preselection availability: `93.75%`;
- uncertainty-budget retention conditional on available output: `99.56%`;
- truth-visible usable availability after budget: `93.33%`.

### Interval-tail efficiency

| Metric | P3 result | Gate |
|---|---:|---|
| lateral median 95% half-width / all-available p95 error | `0.642x` | PASS |
| altitude median ratio | `0.625x` | PASS |
| lateral p95 half-width / p95 error | `2.334x` | **FAIL** (`<=2.25x`) |
| altitude p95 ratio | `1.761x` | PASS |

P3 reduced the corresponding P2 p95 ratios from approximately `5.705x` lateral / `3.332x` altitude to `2.334x` / `1.761x`. The remaining lateral miss is narrow but is still a preregistered failure.

### Uncertainty-budget utility

The frozen width budget retained almost every available estimate, but its p95 nonworsening component was mixed:

- lateral all-available p95 error: `0.170038 m`;
- lateral post-budget p95: `0.169390 m` — nonworsening PASS;
- altitude all-available p95 error: `0.439714 m`;
- altitude post-budget p95: `0.439865 m` — nonworsening FAIL.

The altitude difference is only about `0.000152 m`, but the preregistered gate is binary and therefore remains failed. This result is not reclassified after exposure.

## Decision before protected validation

P3 protected validation seed `154154` is intentionally **not exposed** and is retired rather than recycled into a later benchmark.

The seen development result is already sufficient to show that P3 is a major improvement over P2 but does not satisfy every preregistered development condition. Spending a protected validation split on a candidate known to miss its own development gate would add little scientific value.

No P3 feature, ridge coefficient rule, conformal rule, transfer rule, uncertainty budget, threshold, or gate was changed after transfer exposure.

## Interpretation

P3 supports three conclusions:

1. Removing P2's hand-written multiplicative risk inflation largely fixes extreme interval tails.
2. Two-stage single-factor plus compositional conformal calibration can preserve highly accurate empirical coverage on seen compositions.
3. A hard post-hoc selection layer is no longer obviously necessary: the underlying P3 all-available representation already combines high availability with calibrated uncertainty, while the tiny budget-induced p95 change is dominated by sample-quantile sensitivity rather than a clear reliability gain.

The next revision should therefore test **calibrated uncertainty as the primary reliability output**, with availability measured before any hard selection. Optional uncertainty-budget flags may remain diagnostic, but they should not be required to establish the primary result.

## Next scientific boundary

Any P4 method must use new fit/calibration/transfer/validation evidence and a new preregistration. It may inherit the P3 learned-scale basis concept, but it may not tune against P3 transfer rows as if they were unseen.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
