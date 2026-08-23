# Phase 11 P5 development stop — calibrated perception continuity

## Status

**DEVELOPMENT FROZEN — PROTECTED VALIDATION NOT EXPOSED**

P5 preregistration: `docs/phase11_p5_calibrated_continuity_preregistration.md`

Freeze workflow:

- run: `32615378687`
- freeze head: `b6fc290cde01f5935423c47701d371c10d80dd01`
- artifact ID: `9486774870`
- artifact digest: `sha256:882321c9a58b174877c20150aa829ddef0f6bc02b29379ed48d1e6d97d83775b`
- candidate JSON SHA-256: `daa06109c55af8cc83fd9cdb58ed5c040cdd3574c83f1c73c6dd62e9487e5116`
- transfer-result SHA-256: `a34c8548fb5711bdae732c514817c38cc9cf356805e68e9f55bfb45dfeb5711f`

The freeze workflow passed all P5 invariant tests and verified that protected validation seed `242242` was **not generated**. No P5 validation frames or validation result were created. Protected validation seed `242242` frames/results remain absent from the tip artifact.

## Frozen continuity candidate

- maximum bridge horizon: `5` missing frames;
- bridged outputs never feed back into direct-observation velocity history;
- fit-frozen lateral velocity cap: `0.10883070275429642 m/frame`;
- fit-frozen altitude velocity cap: `0.1479663768591145 m/frame`;
- ridge lambda: `4.0`;
- no severity gate;
- no interval-width gate in the primary result.

## Seen transfer-calibration result

Evidence role: `phase11_p5_seen_transfer_calibration`

On the seen transfer-calibration split only, P5 availability was 99.51%. This is not comparable to P4 protected-validation availability (83.13%), and P5 makes no protected-validation or flight claim.

| Gate | Frozen development result | Verdict |
|---|---:|---|
| H1 estimator availability | `99.51%` | PASS |
| H2 lateral 95% coverage | `95.12%` | PASS |
| H2 altitude 95% coverage | `95.12%` | PASS |
| H3 calibration-curve MACE | `0.000783` | PASS |
| H4 lateral median half-width / p95 error | `0.652x` | PASS |
| H4 altitude median ratio | `0.663x` | PASS |
| H4 lateral p95 half-width / p95 error | `1.594x` | PASS |
| H4 altitude p95 ratio | `1.453x` | PASS |
| H6 shift AUROC | `0.96875` | PASS |

### Long-bridge honesty gate

There were `42` available rows with bridge horizon `3..5`, sufficient to evaluate the preregistered long-bridge gate.

- lateral 95% long-bridge coverage: `88.10%` — PASS against `>=88%`;
- altitude 95% long-bridge coverage: `85.71%` — **FAIL** against `>=88%`;
- lateral median half-width / median long-bridge error: `2.089x` — PASS;
- altitude median half-width / median long-bridge error: `1.510x` — PASS.

Overall P5 development result: **MIXED / FAILED** solely because long-horizon altitude coverage missed the preregistered floor.

## Decision before protected validation

Protected validation seed `242242` is intentionally **not exposed** and is retired rather than recycled into a later benchmark.

The P5 preregistration explicitly required stopping before validation if H1–H5 failed on the seen transfer split. That condition occurred, so validation is not run.

No bridge horizon, velocity-cap rule, uncertainty-model feature, ridge constant, conformal rule, transfer multiplier, or gate was changed after transfer exposure.

## Interpretation

On seen compositional transfer data, a bounded five-frame direct-anchored bridge raised availability while overall calibration stayed within preregistered H2–H4 bands. Protected validation was not exposed.

P5 provides a next-step diagnosis on seen transfer evidence only:

1. A bounded direct-anchored five-frame continuity layer raised availability on seen transfer compositions.
2. Overall uncertainty on seen transfer data remained well calibrated and efficient when those recovered frames were included.
3. The observed weakness is localized to **long bridge horizons**, especially altitude, rather than to the general uncertainty model.

The next revision should therefore preserve P5 point estimation and continuity behavior but calibrate uncertainty separately for short/direct versus long (`3..5`) bridge states on completely new evidence.

## Next scientific boundary

Any P6 method must use new fit/calibration/transfer/development-challenge/protected-validation evidence. P5 transfer seed `231231` is permanently seen. P5 protected seed `242242` remains ungenerated and retired.

Passing a future P6 protected validation still does **not** authorize the final Phase 11 frozen holdout. That final holdout requires a separate explicit user approval checkpoint.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
