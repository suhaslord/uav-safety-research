# Phase 11 P10 development stop — powered direct-conformal replication

## Status

**DEVELOPMENT STOP BEFORE CANDIDATE FREEZE — TRANSFER / PROTECTED VALIDATION NOT EXPOSED**

P10 preregistration: `docs/phase11_p10_powered_direct_conformal_preregistration.md`

Development workflow:

- run: `31974512804`
- workflow/scientific head: `fbb6f5b22c3fb2c8d48345460a48dfa119f8c24e`
- invariant tests: PASS (`7 passed` across P9+P10 guards)
- failure stage: candidate construction from fresh fit + grouped-calibration evidence

## Exposure ledger

The candidate-freeze stage generated the P10 fit and grouped-calibration splits before the locked sample-size assertion stopped construction.

Permanently seen:

- fit seed: `451451`
- grouped-calibration seed: `462462`

Not exposed:

- seen-transfer seed `473473`: **NOT EXPOSED**;
- protected-validation seed `484484`: **NOT EXPOSED**.

Both unexposed seeds are retired with P10 rather than recycled.

## Failure

P10 intentionally preserved P9's direct-conformal group minimums unchanged:

- `base_output >= 1000`;
- `continuity_h3 >= 120`;
- `continuity_h45 >= 60`;
- `continuity_h67 >= 30`.

P10 increased the fresh grouped-calibration cohort from 12 to 18 trajectory families without changing the scientific method.

Observed grouped-calibration `continuity_h45` rows: **`50`**.

The freeze correctly stopped with:

`RuntimeError: P9 calibration group continuity_h45 rows 50 < 60`

No candidate file was produced and no P10 transfer-performance claim is made.

## Interpretation

P10 remains a power/sample-size stop, not evidence that the soft-update/direct-conformal method passes or fails. Increasing from 12 to 18 calibration families was still insufficient for the rarer horizon-4/5 group on this fresh seed.

The preregistered `60`-row minimum must not be reduced after observing `50`.

## Next revision

Phase 11 P11 should preserve the P9/P10 method and thresholds exactly, but use a substantially larger fresh grouped-calibration cohort. To avoid another marginal underpowering event, the next preregistration should use **30 fresh calibration families** while retaining:

- the same q99 velocity-cap rule;
- the same q95 innovation-scale rule;
- the same soft bounded-influence equation and `3.0` scale multiplier;
- the same 0.5/0.5 slope blend;
- the same horizons 3-7 and damping `0.85`;
- the same four direct absolute-error conformal groups;
- the same calibration and transfer minimums;
- the same H1-H6 gates.

P10 `451451` / `462462` are permanently seen and may not be reused as hidden evidence.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
