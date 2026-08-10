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

## Freeze rule

Phase 6C must first pass the full paired development matrix on development seed `626262`. No architecture or threshold may be selected based on the reserved held-out seeds. If Phase 6C is frozen, the held-out run must use the preregistered seeds exactly once and must be reported regardless of outcome.
