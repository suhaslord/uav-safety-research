# Phase 6C revision note

## Status

Phase 6C is a **development-only, simulation-only** revision. It is not a frozen result and has not used the reserved held-out seeds.

Reserved unseen seeds remain:

- landing evaluation: `868686`
- selective-perception evaluation: `878787`

Historical Phase 6 frozen seeds remain permanently seen and unchanged:

- landing: `747474`
- selective perception: `757575`

## Why Phase 6C exists

Phase 6B introduced component-wise confidence for lateral position and altitude. Its post-observability development run improved selective perception and retained large gains over image-only landing in degraded conditions, but it introduced two regressions relative to the original Phase 6 Aegis path:

1. one low-light development episode timed out after repeated altitude-reference takeovers;
2. one mixed-condition development episode touched down slightly above the permitted vertical-speed limit.

Failure replay showed that both regressions coincided with hundreds of altitude-reference takeovers.

The vertical controller consumes the estimated vertical rate `vz`, while the component confidence model `p_z_good` is calibrated against **altitude/scale error**, not vertical-rate error. Phase 6B therefore coupled an altitude-confidence decision to a different state variable whose reliability had not been calibrated by that gate.

## Phase 6C hypothesis

If altitude-component abstention is limited to the state variable it actually evaluates, then the Phase 6B regressions should disappear without weakening the lateral safety behavior.

Phase 6C therefore changes exactly one behavior relative to Phase 6B:

- lateral abstention still permits reference blending of lateral position and lateral velocity;
- altitude abstention may blend altitude position `z` toward the independent reference;
- altitude abstention **does not replace or blend vertical rate `vz`**;
- the established Phase 6 vertical-rate estimate is preserved;
- the 0.80 lateral and 0.80 altitude gates are unchanged;
- the temporal image pipeline, scale-observability confidence cap, independent reference estimator, controller, frozen V3 supervisor, environment, and paired RNG design are unchanged.

## Targeted development replay

Before any larger development matrix, Phase 6C was replayed on the three already-seen diagnostic episodes from the Phase 6B development result.

- Low-light seed `327915747`: Phase 6B timed out; Phase 6C returned to a successful simulated landing with the same 18.45 s duration as original Phase 6.
- Mixed seed `404641207`: Phase 6B produced a vertical-speed unsafe touchdown; Phase 6C returned to a successful simulated landing with final vertical speed close to original Phase 6.
- Occlusion seed `1488232361`: original Phase 6 and Phase 6B both had the same horizontal-speed failure; Phase 6C preserved that failure rather than appearing to fix an unrelated mechanism.

This replay is diagnostic evidence only because all three episode seeds were already seen during development.

## Full Phase 6C development matrix

Phase 6C was then evaluated on the paired 30-episode-per-condition development matrix using episode seed family `626262` and calibration seed `616161`.

- clean: 100% success, 0% unsafe;
- blur: 100% success, 0% unsafe;
- low light: 100% success, 0% unsafe, removing the Phase 6B timeout;
- mixed: 100% success, 0% unsafe, removing the Phase 6B vertical-speed regression;
- occlusion: 93.33% success and 6.67% unsafe, versus 96.67% success and 3.33% unsafe for original Phase 6 and Phase 6B.

Therefore Phase 6C was **not frozen**. It solved the direct Phase 6B coupling problem but introduced one additional occlusion failure.

The new occlusion regression occurred at already-seen development seed `1033307971`. Original Phase 6 and Phase 6B succeeded; Phase 6C touched down with vertical speed about `-0.856 m/s`, just beyond the `0.80 m/s` touchdown limit.

## Occlusion trace finding

A near-ground trace showed that the failure was not ordinary low-confidence altitude noise. The visual track abruptly aliased from roughly `0.2 m` altitude to a false `3–5 m` altitude while `p_z_good` remained near 0.97–1.00. The temporal derivative consequently clipped near `+1.2 m/s`, making the controller believe the simulated vehicle was ascending even though it was already descending near the ground.

At the same time, the independent reference estimator remained near the true low-altitude regime. This created a large image/reference altitude contradiction that the component probability alone did not capture.

## Phase 6D hypothesis

Phase 6D tests whether **soft uncertainty and hard estimator contradiction should be handled separately**.

The revision keeps all Phase 6C behavior unless a statistically large image/reference altitude disagreement occurs:

- soft altitude uncertainty (`p_z_good < 0.80`) uses Phase 6C behavior: blend altitude position `z` only and preserve the established Phase 6 `vz`;
- hard altitude contradiction uses a fixed 3-sigma consistency rule based on the combined image/reference positional uncertainty;
- when the altitude disagreement exceeds 3 combined standard deviations and the reference is usable, both `z` and `vz` may use the existing Phase 6B fallback weight;
- lateral behavior, component thresholds, controller, and frozen V3 supervisor remain unchanged.

The 3-sigma rule was declared before the Phase 6D landing development matrix; it is not selected from Phase 6D outcome rates.

## Phase 6D targeted replay

Before the full matrix, Phase 6D was replayed on four already-seen development cases. The full test suite passed 64 tests.

- Low-light seed `327915747`: remained a successful simulated landing.
- Mixed seed `404641207`: remained a successful simulated landing.
- Occlusion alias seed `1033307971`: recovered from the Phase 6C unsafe touchdown to success; the hard-altitude-alias rule fired on 9 frames.
- Shared horizontal-speed failure seed `1488232361`: remained unsafe, as expected for an unrelated lateral failure mechanism.

This targeted replay is diagnostic development evidence only and does not count as held-out validation.

## Freeze rule

Phase 6D must first pass the full paired development matrix on development seed `626262`. No architecture or threshold may be selected based on the reserved held-out seeds. The reserved landing seed `868686` and selective-perception seed `878787` remain unused until a final architecture is frozen. Any eventual held-out result must be reported regardless of outcome.
