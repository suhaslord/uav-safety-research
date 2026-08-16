# Phase 11 P11 development stop — second powered direct-conformal replication

## Status

**DEVELOPMENT STOP BEFORE CANDIDATE FREEZE — TRANSFER / PROTECTED VALIDATION NOT EXPOSED**

P11 preregistration: `docs/phase11_p11_powered_direct_conformal_preregistration.md`

Simulation benchmark:

- run: `31974740090`
- workflow/scientific head: `2f0bfc48979a39a51a3eb79354f9e700cf10d43f`
- invariant tests: PASS (`10 passed` across P9/P10/P11 guards)
- failure stage: candidate construction from fresh fit + grouped calibration

## Exposure ledger

The freeze stage generated fresh P11 fit and grouped-calibration evidence before the preregistered group-count assertion stopped candidate construction.

Permanently seen:

- fit seed `495495`;
- grouped-calibration seed `506506`.

Not exposed:

- seen-transfer seed `517517`;
- protected-validation seed `528528`.

Both unexposed seeds are retired with P11 rather than recycled.

## Failure

P11 preserved the P9/P10 four-group direct-conformal calibration thresholds exactly and expanded the fresh grouped-calibration cohort to `30` trajectory families.

The rarest fixed group remained underpowered:

- required `continuity_h67 >= 30` calibration rows;
- observed `continuity_h67 = 8` rows.

Candidate construction stopped with:

`RuntimeError: P9 calibration group continuity_h67 rows 8 < 30`

No candidate was frozen and no transfer or interval-performance claim is made.

## Interpretation

P9, P10, and P11 together show that the four-group uncertainty partition is statistically inefficient for the natural simulated gap distribution:

- P9 missed the horizon-3 count (`110 < 120`) with 12 calibration families;
- P10 missed the horizon-4/5 count (`50 < 60`) with 18 families;
- P11 used 30 families but still produced only `8` horizon-6/7 rows versus the required `30`.

This is now evidence about calibration design, not a reason to lower thresholds after exposure. Very long continuity gaps are too rare to support a standalone h6-7 conformal bucket efficiently under the current benchmark generator.

## Next revision

Phase 11 P12 should preserve the P9/P10/P11 **soft continuity estimator unchanged** and keep direct finite-sample absolute-error conformal calibration, but preregister a simpler three-group partition on entirely fresh evidence:

1. `base_output`;
2. `continuity_h3`;
3. `continuity_h47` for horizons 4 through 7.

This combines the sparse long-horizon bucket with the adjacent later-continuity regime rather than lowering any already-observed P11 threshold.

P12 should use a larger fresh calibration cohort and new calibration/transfer minimums chosen before generation. P11 `495495` / `506506` may be used only as descriptive motivation.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
