# Phase 6B Held-Out Evaluation Protocol

## Purpose

This protocol was originally recorded before observing the first Phase 6B 30-episode-per-cell landing development result. It is amended below before any Phase 6B held-out seed is executed.

Phase 6B is a new post-frozen revision motivated by the original Phase 6 selective-confidence audit. It must be evaluated separately from the historical Phase 6 frozen result.

## Frozen operating choices

The following choices remain fixed for held-out evaluation:

- lateral component confidence threshold: `0.80`
- altitude component confidence threshold: `0.80`
- temporal calibration seed: `616161`
- component calibration seed: `616161`
- temporal calibration samples per condition: `180`
- component calibration samples per condition: `280`
- synthetic image severity: `1.0`
- frozen V3 safety supervisor: unchanged
- Phase 6 renderer, temporal tracker, robust velocity filter, controller, dynamics, wind process, and independent reference estimator: unchanged except for the explicitly documented Phase 6B component-fusion and confidence layers

The 0.80/0.80 component gates were selected from the predeclared risk/coverage grid in the Phase 6B calibration-development benchmark, not from landing outcomes, and were not altered by later development audits.

## Pre-freeze amendment: full-domain scale observability

Before any Phase 6B held-out run, a development-only audit using seed `666666` identified a calibration-domain defect: the first component-calibration dataset underrepresented the simulator's 5.8–8.0 m initial altitude range. Full-domain calibration was therefore introduced using four stratified altitude bands spanning 0.25–8.0 m.

A second development audit showed that full-domain fitting alone could still be overconfident for clean/occlusion high-altitude frames. This was traced to a known property of the synthetic renderer: apparent marker half-size is quantized to integer pixels, and at small apparent scales one adjacent scale bin can span more than the 0.85 m altitude-error target.

Before held-out evaluation, Phase 6B therefore adds an analytic, simulation-specific altitude-observability ceiling:

`delta_z_bin = 35/h - 35/(h+1)`

`p_z_good <= min(1, 0.85 / delta_z_bin)`

where `h` is the apparent half-size implied by the image-derived altitude estimate. The scale-bin width is also included as a confidence feature.

This correction does **not** alter the altitude measurement, controller, reference estimator, V3 supervisor, or the preselected 0.80/0.80 component gates. It limits confidence when the synthetic pixel scale itself cannot resolve the target accuracy.

The change is permitted as a pre-freeze development correction because:

1. no Phase 6B held-out seed had been executed;
2. the defect was identified by a dedicated development-domain audit rather than by a held-out outcome;
3. the operating thresholds remained fixed;
4. the correction and all prior development results are preserved in the repository history.

## Development landing study

Phase 6B landing development uses seed `626262` with 30 paired episodes per condition/architecture. This seed is development-only and cannot become held-out evidence.

The first Phase 6B development run preceded the full-domain observability correction and is preserved as a pre-correction result. The corrected architecture must be rerun on the same development seed before final freezing.

No additional threshold search is permitted from landing outcomes. If the corrected development run exposes a clear software/interface defect, it may be fixed and documented, but any algorithmic redesign after observing the preregistered held-out seeds requires a new revision and new seeds.

## Held-out seeds declared in advance

If the corrected Phase 6B implementation is technically stable after development, the frozen evaluation will use:

- held-out landing seed: `868686`
- held-out selective-perception seed: `878787`

These seeds were declared before the corrected Phase 6B development landing table was observed and remain unused at the time of this amendment. Once either held-out run is executed, its seed becomes permanently seen and must not be reused for tuning.

## Held-out landing comparison

For each of the five image conditions:

- clean
- blur
- low_light
- occlusion
- mixed

run 100 paired episodes for each architecture:

1. `image_temporal` — established Phase 6 temporal image perception without Aegis redundant fusion;
2. `image_aegis_v3` — historical Phase 6 Aegis image integration;
3. `image_aegis_phase6b` — component-selective Phase 6B Aegis integration.

This produces 1,500 landing episodes total.

Primary outcomes:

- success rate;
- unsafe touchdown rate;
- safe abort rate.

Report 95% Wilson confidence intervals for rates.

Paired revision outcomes:

- Phase 6B minus Phase 6 success-rate difference;
- Phase 6B minus Phase 6 unsafe-touchdown difference;
- Phase 6 unsafe episodes rescued to Phase 6B success;
- Phase 6 successes that become Phase 6B unsafe touchdowns;
- success/abort transitions.

Component-behavior outcomes:

- lateral component abstention rate;
- altitude component abstention rate;
- lateral reference-takeover count/rate;
- altitude reference-takeover count/rate;
- unresolved component count;
- mean `p_x_good` and `p_z_good`.

Touchdown failures must also be decomposed into lateral position, horizontal speed, and vertical speed violations.

## Held-out selective-perception audit

Using seed `878787`, generate 20 sequences × 100 frames for each image condition using the same synthetic image generator family and severity distribution as the development component benchmark.

For the fixed 0.80 gates, report separately for lateral and altitude:

- coverage;
- selected bad-estimate rate;
- bad-estimate rejection recall;
- calibration ECE.

Also report learned altitude confidence and the analytic observability ceiling separately, so a rejection caused by degraded image evidence can be distinguished from one caused by coarse synthetic scale resolution.

The full predeclared risk/coverage grid may be reported as a diagnostic curve, but the 0.80/0.80 thresholds remain the primary frozen operating point and must not be changed after viewing held-out results.

## Interpretation rule

The held-out Phase 6B result is allowed to be positive, neutral, or negative. A negative result is not a reason to rerun with a different seed or threshold and present that rerun as the original evaluation.

Any later algorithm changes become a new named revision and require new held-out seeds.

## Previously seen seeds that are excluded

Do not use these as Phase 6B final validation seeds:

- `616161` — calibration development
- `626262` — landing development
- `636363` — selective smoke/development use
- `646464` — failed contextual-confidence ablation
- `656565` — component calibration development benchmark
- `666666` — high-altitude calibration-domain audit
- `747474` — historical frozen Phase 6 landing
- `757575` — historical frozen Phase 6 selective audit

Reserved and still unseen for the Phase 6B frozen evaluation:

- `868686` — held-out landing
- `878787` — held-out selective perception

## Safety scope

All Phase 6B experiments remain synthetic, planar simulation studies. This protocol does not validate a real camera, physical UAV, autopilot, or real-world flight-safety system.
