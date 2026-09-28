# Phase 14 surrogate-fit result — frozen uncertainty-to-recoverability bridge

## Status

**FIT COMPLETE — bridge candidate frozen before development evidence.**

This is identification evidence, not a development PASS claim.

## Evidence identity

- workflow run: `34010431456`
- artifact: `9982290446`
- artifact digest: `sha256:17eb7a8f8f9844f97f46f35e017cebad8155bcce6a42cfe7599bc6d2c603bb8b`
- bridge-candidate SHA-256: `0443d4e45a1966c77544c5c9965de8caec6e622c79ef8c2ce47aee82a3c95981`
- scientific SHA: `a80cd02d0781e7b3dde9ea523b2fe17ecd44002c`
- fit seed: `1414140`
- fit families: `1489–1520`
- extracted adjacent usable transitions: `14,773`
- frozen Phase 12 candidate SHA-256: `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`

## Locked recoverable set

Unchanged from the earlier merged invariance benchmark:

- lateral: `|e_x| <= 0.30 m`
- altitude: `|e_z| <= 0.85 m`

The old hand-selected surrogate values `A = diag(0.65, 0.70)` and disturbance bounds `0.05 / 0.12 m` are not used by Phase 14.

## Data-derived frozen bridge

### Lateral

- fitted no-intercept one-step coefficient `a_x = 0.6102677720`
- fit transitions inside lateral bound: `12,556`
- 99% normalized-residual multiplier `gamma_x = 1.7156205837`
- frozen Phase 12 half-width admission cap `h_cap_x = 0.0613350659 m`
- contraction budget `(1-|a|)r = 0.1169196684 m`
- disturbance bound at cap `gamma*h_cap = 0.1052277016 m`
- one-step image at cap `0.2883080332 m`
- analytic margin to the `0.30 m` box: `0.0116919668 m`
- fit normalized-residual coverage: `0.9901242434`

### Altitude

- fitted no-intercept one-step coefficient `a_z = 0.6227394449`
- fit transitions inside altitude bound: `13,521`
- 99% normalized-residual multiplier `gamma_z = 1.5934734179`
- frozen Phase 12 half-width admission cap `h_cap_z = 0.1811164977 m`
- contraction budget `(1-|a|)r = 0.3206714718 m`
- disturbance bound at cap `gamma*h_cap = 0.2886043246 m`
- one-step image at cap `0.8179328528 m`
- analytic margin to the `0.85 m` box: `0.0320671472 m`
- fit normalized-residual coverage: `0.9900894904`

## Frozen interpretation

The candidate is contractive on both axes without clipping or forced stabilization. The uncertainty caps were derived algebraically from the fitted contraction budget, the separately fitted 99% normalized-residual multiplier, the fixed recoverable box, and the preregistered `0.90` reserve fraction.

This does **not** establish downstream validity. Development must now test whether:

1. the normalized-residual envelope survives fresh natural simulation evidence,
2. admitted transitions remain empirically inside the fixed box at the preregistered rates,
3. admission remains nontrivial, and
4. the same frozen bridge survives the exact fixed-two-frame latency challenge from Phase 13.

No fit parameter may change after this file.

`simulation_only = true`
`safety_acceptance = false`
`controller_tuning_allowed = false`
