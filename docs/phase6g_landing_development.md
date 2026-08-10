# Phase 6G landing-development protocol

## Purpose

Phase 6G tests whether the **frozen Phase 6E perception estimator** improves the image-to-landing system when integrated with the simpler Phase 6C component-fusion policy.

This is a simulation-only development experiment. It is not final held-out validation.

## Frozen Phase 6G architecture before the new development matrix

Phase 6G is defined by:

- Phase 6 synthetic landing-pad renderer;
- frozen Phase 6E image estimator from `src/uav_safety/phase6e_perception.py` injected into the existing `CalibratedTemporalImagePipeline`;
- historical Phase 6 empirical scalar temporal calibrator unchanged;
- frozen Phase 6E component-confidence calibrator;
- fixed x and z component selection thresholds `0.80 / 0.80`;
- Phase 6 robust image-derived velocity filter unchanged;
- independent lower-rate reference estimator unchanged;
- Phase 6C component fusion unchanged:
  - low-confidence x may use reference x/vx;
  - low-confidence z may use reference z;
  - low-confidence z does **not** overwrite the established temporal/image vz;
- no Phase 6D 3-sigma hard-alias rule;
- original landing controller unchanged;
- frozen V3 safety supervisor unchanged;
- isolated environment/image/reference RNG streams unchanged.

Implementation under test: `src/uav_safety/simulator_image_phase6g.py`.

The perception layer is already frozen by `docs/phase6e_perception_freeze.md`. Any change to Phase 6E perception after this protocol creates a new architecture label.

## Targeted replay gate

Before the new development family is executed, Phase 6G is replayed on four already-seen historical development cases:

- low light `327915747` — Phase 6B altitude-vz coupling timeout;
- mixed `404641207` — Phase 6B vertical-speed regression;
- occlusion `1033307971` — Phase 6C near-ground altitude-alias regression;
- occlusion `1488232361` — shared historical horizontal-speed failure.

This replay is diagnostic only. Phase 6G proceeds to the new development family only if it does not reintroduce the first three perception/fusion regressions. The unrelated shared horizontal-speed failure is not required to become a success.

## New development seed family

A repository search for exact seed `838381` returned no matches before this protocol was committed.

- **Phase 6G landing-development seed family:** `838381`
- calibration seed: `616161`

`838381` is development-only and becomes permanently seen once executed.

Final replacement held-out seeds remain untouched:

- landing: `918271`
- selective perception: `928271`

## Paired development matrix

For each condition, generate 50 episode seeds deterministically from top-level family `838381` and use the exact same episode seeds for every architecture.

Conditions:

- clean
- blur
- low light
- occlusion
- mixed

Architectures:

1. `image_temporal` — image-only temporal landing baseline;
2. `image_aegis_v3` — original Phase 6 Aegis image architecture;
3. `image_aegis_phase6g` — frozen Phase 6E perception + Phase 6C component fusion.

Total: 750 simulated landing episodes (50 × 5 conditions × 3 architectures).

## Primary outcomes

- success rate;
- unsafe-touchdown rate;
- abort rate;
- timeout rate.

Secondary diagnostics include final x error, final |vx|, final |vz|, temporal abstention, component abstention, reference-takeover counts, interventions, and paired transition counts.

## Development acceptance criteria

Phase 6G may be frozen for final held-out evaluation only if **all** criteria pass on the paired `838381` matrix.

1. **No paired regression from original Phase 6:** across all conditions, an episode that succeeds under `image_aegis_v3` may not become unsafe, aborted, or timed out under Phase 6G.
2. **Clean preservation:** Phase 6G success must be >= original Phase 6 success and unsafe/abort/timeout rates must each be <= original Phase 6.
3. **Blur preservation:** same requirement as clean.
4. **Low-light preservation:** Phase 6G success must be >= original Phase 6, with unsafe/abort/timeout each <= original Phase 6.
5. **Mixed preservation:** Phase 6G success must be >= original Phase 6, with unsafe/abort/timeout each <= original Phase 6.
6. **Occlusion preservation:** Phase 6G success must be >= original Phase 6 and unsafe-touchdown rate must be <= original Phase 6. Abort/timeout increases are not allowed if they reduce success below original Phase 6.
7. **Image-only value check:** paired transition counts versus `image_temporal` must be saved so any claimed benefit can be tied to exact rescued/failing episodes rather than only aggregate percentages. This is descriptive, not an additional pass/fail criterion.
8. **No post-result retuning:** if any pass/fail criterion fails, Phase 6G is preserved as a failed development revision. No Phase 6E perception rule, 0.80 gate, fusion weight, controller constant, or supervisor constant may be adjusted using the `838381` outcome table while retaining the Phase 6G label.
9. **No final-seed leakage:** neither `918271` nor `928271` may appear in any development input, workflow, or result metadata.

## Freeze rule

Passing this development matrix does not itself make the result final. If Phase 6G passes, the exact implementation commit and constants must be frozen in a separate document **before** either replacement held-out seed is executed. The final held-out results must then be reported regardless of outcome.
