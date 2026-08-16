# Phase 11 P14 development stop — independent coarse fallback

## Status

**DEVELOPMENT STOP BEFORE CANDIDATE FREEZE — CHALLENGE / PROTECTED VALIDATION NOT EXPOSED**

P14 preregistration: `docs/phase11_p14_independent_coarse_fallback_preregistration.md`

Simulation benchmark:

- run: `31975575075`
- workflow/scientific head: `5859b0245528cfe57ae212004a3682b7625e5823`
- invariant tests: PASS (`9 passed`)
- failure stage: base grouped-conformal calibration

## Exposure ledger

The workflow generated the fresh fit, base-calibration, and transfer-calibration raw simulation splits before candidate construction stopped on the preregistered base-calibration row minimum.

Permanently seen:

- fit seed `638638`;
- base calibration seed `649649`;
- transfer-calibration seed `660660`.

Not exposed:

- seen challenge seed `671671`;
- protected validation seed `682682`.

The unexposed seeds are retired rather than recycled.

## Failure

P14 required at least `300` actual `auxiliary_fallback` rows in base calibration. Only **`66`** occurred.

Candidate construction correctly stopped with:

`RuntimeError: P14 base-calibration group auxiliary_fallback rows 66 < 300`

No candidate was frozen and no P14 challenge-performance claim is made.

## Interpretation

This is a calibration-design sample-size failure, not evidence that the independent auxiliary observation model succeeds or fails.

The auxiliary channel is intentionally fallback-only in the final estimator, so easier calibration compositions rarely invoke it even though the simulated auxiliary observation exists on most frames. Requiring calibration to use only rows where the primary stack happens to fail discards most of the available independent-sensor calibration evidence.

## Next revision

P15 should preserve the P14 auxiliary observation model and fallback-only final-use rule unchanged, but calibrate the auxiliary channel using **all available auxiliary observations** on the calibration splits, regardless of whether the primary output was available on those same frames.

This is scientifically cleaner because:

- the auxiliary observation process is generated independently of primary availability;
- its error distribution can be characterized directly without conditioning on a rare primary-failure event;
- the final estimator can still use the auxiliary observation only when the primary stack is unavailable;
- primary base/continuity calibration remains restricted to the outputs actually produced by those primary sources.

P15 must use fresh seeds/families and preregister this source-specific calibration rule before generation. P14 seeds may be used only as descriptive motivation.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
- no real auxiliary-sensor performance claim
