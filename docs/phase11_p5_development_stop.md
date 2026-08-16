# Phase 11 P5 development stop — calibrated perception continuity

## Status

**DEVELOPMENT FROZEN — PROTECTED VALIDATION NOT EXPOSED**

P5 preregistration: `docs/phase11_p5_perception_continuity_preregistration.md`

Freeze workflow:

- run: `31972687836`
- freeze head SHA: `c5927d208873417adce3ce78daf1c670b6a5fce1`
- artifact ID: `9270220380`
- artifact digest: `sha256:538a9876922f56016235c22775dc98a81431a5dfe87ea660b5951239f132b6bc`
- candidate JSON SHA-256: `5bafa7ede17b026dea0dbaf16f20fb6c70f83137b3b48552727f6a9ac7d0cc4e`
- transfer-result SHA-256: `590e8bdc01175d325a06ad9db526caebfb21a064f24d6709e9566d3502721172`

The freeze workflow's invariant tests passed and verified that protected validation seed `242242` was not generated.

## Seen transfer-calibration result

Evidence role: `phase11_p5_seen_transfer_calibration`

P5 solved the P4 availability bottleneck on seen transfer data:

- truth-visible availability: **`99.51%`** — PASS against `>=92%`;
- lateral 95% coverage: `95.12%` — PASS;
- altitude 95% coverage: `95.12%` — PASS;
- calibration-curve MACE: `0.000783` — PASS;
- lateral median / p95 interval-efficiency ratios: `0.611x` / `1.552x` — PASS;
- altitude median / p95 interval-efficiency ratios: `0.632x` / `1.647x` — PASS;
- trajectory-level shift AUROC: `0.9462` — diagnostic PASS.

The new bounded continuity extension produced `61` seen transfer rows (`4.24%` of truth-visible frames).

Continuity-specific diagnostics:

- lateral 95% coverage: `91.80%`;
- altitude 95% coverage: **`100.00%`**;
- lateral p95 half-width / p95 error: `0.848x`;
- altitude p95 half-width / p95 error: `1.535x`.

The preregistered H5 continuity-specific honesty gate requires 95% coverage in `[88%,99%]` on both axes. Altitude overcoverage therefore fails H5 and P5 fails overall before protected validation.

## Decision before validation

Protected validation seed `242242` is intentionally **not exposed**.

The candidate is not eligible for protected validation because a preregistered primary development gate failed. Spending unseen validation evidence would not add scientific value.

## Interpretation

P5 establishes that the continuity mechanism itself can nearly eliminate short-gap availability loss without breaking the overall reliability layer. The remaining issue is calibration granularity rather than estimate production:

1. overall availability rises from P4's `83.13%` protected-validation result to `99.51%` on the new seen P5 transfer split;
2. overall coverage and interval efficiency remain excellent;
3. the continuity-extension subgroup is small and behaves differently from genuine/inherited-bridge outputs;
4. global two-stage calibration makes altitude intervals too conservative specifically for that subgroup.

This supports a narrow P6 hypothesis: preserve the P5 continuity estimator unchanged and calibrate `continuity_extension` outputs separately from non-continuity outputs at the compositional transfer stage.

## Next revision

P6 should make exactly one scientific change:

- **source-conditional transfer calibration** with two preregistered groups: `continuity_extension` and `base_output`.

All P5 continuity constants remain unchanged in P6:

- max extension horizon `5`;
- damping `0.85`;
- fit-derived q99 velocity caps;
- genuine-anchor-only history;
- no recursive continuity anchors.

P6 must use new fit/calibration/transfer/validation seeds and new trajectory families. P5 transfer seed `231231` is permanently seen and may not become hidden evidence.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
