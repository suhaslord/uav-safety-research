# Phase 11 P7 candidate freeze — powered horizon-aware calibration

## Status

**CANDIDATE FROZEN BEFORE INDEPENDENT DEVELOPMENT CHALLENGE**

P7 preregistration: `docs/phase11_p7_powered_horizon_preregistration.md`

Freeze workflow:

- run: `31971298967`
- freeze head: `3be4423afa24dfa85af9ed36e4064b007fcc5e13`
- artifact ID: `9269862892`
- artifact digest: `sha256:7a3e156da21deefd2374b8597e5ec9aa0550f151907692b60a3e6464ed57ff9a`
- artifact candidate JSON SHA-256: `9ed0a09bb32095dd7a1b03c97e10e16d70571ebd28c2922e99f2e633575fc1eb`

The freeze workflow passed all P7 invariant tests and verified that neither development seed `341341` nor protected-validation seed `352352` was generated during candidate freeze.

## Horizon calibration support

The expanded preregistered transfer panel produced:

- direct/short (`h=0..2`) available rows: `2,785`;
- long (`h=3..5`) available rows: **`84`**.

The long group therefore exceeds the unchanged preregistered minimum of `40` rows and is eligible for separate transfer calibration.

## Frozen continuity/model constants

- maximum bridge horizon: `5`;
- direct observations only in velocity history;
- fit-frozen lateral velocity cap: `0.10943258589853086 m/frame`;
- fit-frozen altitude velocity cap: `0.15679862246612833 m/frame`;
- ridge lambda: `4.0`;
- no hard severity or interval-width rejection;
- separate conformal transfer multipliers for `h<=2` and `h=3..5`;
- exact scale coefficients and conformal values are stored in the immutable artifact and `results/phase11_p7/candidate_freeze.json`.

## Exposure boundary

At this checkpoint:

- transfer seed `330330` is seen calibration evidence;
- development-challenge seed `341341` is still unseen;
- protected-validation seed `352352` is still unseen.

The next allowed action is exactly one independent development-challenge evaluation on `341341` with this unchanged candidate.

Only if every preregistered P7 development gate passes may `352352` be generated.

Even a protected-validation pass would not authorize the final Phase 11 frozen holdout; that final exposure requires a separate explicit user approval checkpoint.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
