# Phase 11 P6 calibration stop — horizon-aware uncertainty

## Status

**STOPPED BEFORE CANDIDATE FREEZE — INSUFFICIENT LONG-BRIDGE CALIBRATION SUPPORT**

P6 preregistration: `docs/phase11_p6_horizon_calibration_preregistration.md`

First freeze-workflow attempt:

- run: `31971164980`
- head: `c1eec476040a13680686fbe754100564d5b24953`
- freeze job: failed at preregistered invariant checks before candidate artifact generation.

## What happened

The P6 protocol required at least `40` available observations in each transfer-calibration horizon group before a candidate could be frozen:

- `direct_short`: bridge horizon `0..2`;
- `long`: bridge horizon `3..5`.

The generated P6 transfer panel contained:

- `1,412` direct/short rows;
- only **`23` long-bridge rows**.

Therefore the long-horizon transfer calibration was underpowered relative to the preregistered minimum and the candidate-freeze step correctly aborted.

## Exposure ledger

The invariant tests generated the fit/calibration/transfer data needed to count the horizon groups before failing. Therefore:

- fit seed `253253` is seen development evidence;
- calibration seed `264264` is seen development evidence;
- transfer seed `275275` is **permanently seen**;
- independent development-challenge seed `286286` was **not generated**;
- protected-validation seed `297297` was **not generated**.

Seeds `286286` and `297297` are retired rather than recycled into later hidden evidence.

No candidate freeze JSON, development-challenge result, or protected-validation result was produced.

## Scientific interpretation

P6 did not fail because the horizon-aware calibration hypothesis was falsified. It failed earlier: the proposed transfer panel did not contain enough naturally occurring horizon-3..5 bridge observations to estimate a separate long-horizon conformal transfer multiplier at the preregistered sample floor.

The correct next step is **not** to lower the 40-row requirement after seeing `23`. A new revision should instead increase the amount of preregistered compositional calibration data likely to exercise longer gaps while keeping the same minimum-support rule and using completely new seeds/families.

## Next boundary

P7 should:

- keep the P5 continuity estimator unchanged;
- keep the direct/short vs long horizon-aware calibration idea;
- retain the minimum `40` long-bridge calibration observations;
- expand the transfer-calibration panel, especially temporal-dropout compositions;
- preserve an independent development challenge before any protected validation.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
