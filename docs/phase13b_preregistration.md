# Phase 13B preregistration — Thirteen Paired Degradation Audit

## Status

**PREREGISTERED BEFORE ANY PHASE 13B DEVELOPMENT EVIDENCE IS GENERATED OR EXPOSED.**

Phase 13B is a new scientific lineage created only after the Phase 13A zero-shot development result was permanently recorded as a failure.

Phase 13A remains immutable and failed. Phase 13B does not replace, reinterpret, or relax that result.

## Why Phase 13B exists

Phase 13A asked the strongest absolute-transfer question:

> Does the frozen Phase 12 model still satisfy the predecessor gate set on a deliberately different 13-domain external-validity distribution?

It failed at development because the paired no-shift control itself did not reproduce the predecessor calibration/efficiency gate set. That means the added stress overlay could not be cleanly isolated as the cause of the failure.

Phase 13B asks a narrower causal question:

> Within each of the same 13 locked base domains, how much does the preregistered stress overlay degrade interval honesty relative to its exact matched no-shift control?

This is a paired degradation study, not a second attempt to make Phase 13A pass.

## Frozen scientific components

Phase 13B keeps unchanged:

- frozen Phase 12 scientific SHA `8d0617a83d699cd14eae6194ce3a86a5c034dfbc`
- frozen Phase 12 candidate SHA-256 `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`
- point estimator
- rescue path
- all Phase 12 uncertainty parameters
- all 13 Phase 13A domain definitions
- all 13 Phase 13A stress magnitudes
- truth-leakage rules
- zero-adaptation requirement
- simulation-only claim boundary

The machine-readable stress source remains `docs/phase13_domain_manifest.json`.

No stress value may be changed in Phase 13B.

## Seen Phase 13A evidence

The canonical Phase 13A development result is permanently seen and may be used only to motivate the new question.

- result JSON SHA-256: `2e851c4cef6c965dfce5c629f9ef0ce7d3d28bae11d80256a3f0d60ec9eab26b`
- run: `34008402512`
- artifact: `9981691482`

The Phase 13A development frames are **not** Phase 13B evaluation evidence and may not be reused to score Phase 13B.

Phase 13B thresholds below are not selected by fitting to Phase 13A outcomes. Where possible they inherit the already-preregistered Phase 13A honesty and catastrophic floors.

## Exactly 13 paired domains

Phase 13B preserves the same 13 domain names and frozen overlays:

1. camera_scale_miscalibration
2. lateral_sensor_bias
3. correlated_measurement_noise
4. heavy_tail_measurement_noise
5. fixed_latency_2f
6. jittered_latency_0_4f
7. burst_staleness_5f
8. lateral_wind_drift
9. vertical_gust
10. dynamics_gain_mismatch
11. oscillatory_drift
12. reacquisition_shock
13. latency_wind_calibration_compound

The number 13 remains a study constraint: all 13 must be represented and no domain may be removed after seeing results.

## Fresh Phase 13B evidence

All Phase 13B evidence is disjoint from Phase 13A.

### Development

- seed: `1313131`
- families: `1297–1320`
- role: permanently seen Phase 13B development evidence

### Transfer

- seed: `1313132`
- families: `1321–1344`
- remains unexposed unless development passes

### Protected validation

- seed: `1313133`
- families: `1345–1368`
- remains unexposed unless transfer passes

### Final

- seed: `1313134`
- families: `1369–1392`
- remains unexposed unless protected validation passes

Each stage contains 24 families split evenly across the existing intervention strata.

No Phase 13A seed or family is reused.

## Paired construction

For each domain and each fresh family:

1. generate one predecessor base event;
2. clone it to a no-shift control;
3. apply the already-frozen Phase 13 stress overlay to the paired copy;
4. run the exact frozen Phase 12 candidate on both;
5. compare only matched control-vs-shift behavior.

Truth trajectories and predecessor availability must remain identical within a pair.

## Primary paired outcomes

For each domain and axis, compute:

- control 95% coverage
- shifted 95% coverage
- coverage delta = shifted minus control
- control p95 absolute error
- shifted p95 absolute error
- p95 error inflation ratio = shifted / control
- control availability
- shifted availability

The paired analysis is domain-local. No domain may be rescued by averaging it with easier domains.

## Gate G13B.1 — paired construction integrity

For every one of the 13 domains:

- paired row counts must match exactly;
- truth-visible counts must match exactly;
- useful availability must match exactly;
- no truth value may be changed by the overlay.

Required: 13 / 13 domains pass.

## Gate G13B.2 — no catastrophic shifted domain

The Phase 13A catastrophic floor is inherited unchanged.

For every domain:

- shifted lateral 95% coverage `>= 0.80`
- shifted altitude 95% coverage `>= 0.80`

Required: 13 / 13 domains pass.

## Gate G13B.3 — bounded paired coverage degradation

The allowable paired loss is derived from the gap between the already-preregistered Phase 13A honesty floor (`0.88`) and catastrophic floor (`0.80`).

For every domain and axis:

`shifted_95_coverage - control_95_coverage >= -0.08`

Required: 13 / 13 domains pass on both axes.

This is not an assertion that 8 percentage points is ideal. It is a locked boundary chosen from already-existing Phase 13A thresholds rather than from the observed Phase 13A domain values.

## Gate G13B.4 — rescue does not catastrophically lose honesty

On aggregate rescue-output rows under the shifted distribution:

- lateral 95% coverage `>= 0.80`
- altitude 95% coverage `>= 0.80`

This inherits the same catastrophic honesty floor rather than creating a new tuned target.

## Gate G13B.5 — reliability mechanism survives

On available primary-continuity shifted rows:

Spearman correlation between normalized anchor innovation and lateral absolute error must remain:

`>= 0.20`

This threshold is unchanged from Phase 13A.

## Gate G13B.6 — compound domain must stand on its own

The thirteenth domain, `latency_wind_calibration_compound`, receives no special relaxation.

It must independently satisfy:

- G13B.1 paired integrity
- G13B.2 catastrophic coverage floor
- G13B.3 paired coverage-loss floor

This prevents a global average from hiding the domain that exposed the Phase 13A local boundary.

## Gate G13B.7 — zero adaptation

Before the Phase 13B development result:

- Phase 12 candidate changed: `false`
- Phase 13 stress manifest changed: `false`
- recalibration performed: `false`
- post-hoc interval multiplier: `false`
- threshold change after exposure: `false`

Any violation fails Phase 13B by construction.

## Development pass rule

Phase 13B development passes only if G13B.1 through G13B.7 all pass.

A development failure:

- is preserved permanently;
- prohibits Phase 13B transfer exposure;
- cannot be repaired by changing the 13 overlays or the frozen Phase 12 candidate inside this lineage.

A development pass authorizes exactly one transfer exposure with seed `1313132` and no scientific changes.

## Sequential evidence rule

Development -> transfer -> protected -> final.

Each downstream stage may be exposed once only after the prior stage passes.

No downstream seed may appear in the development workflow.

Technical failures before a result is emitted must be documented; any seed that enters metric computation is retired rather than reused.

## What Phase 13B can and cannot establish

A Phase 13B pass would support only the narrower paired claim:

> Across 13 preregistered synthetic domains, the frozen Phase 12 uncertainty model kept stress-induced coverage degradation within the locked paired bounds relative to matched no-shift controls.

It would **not** erase Phase 13A's absolute-transfer failure.

It would **not** establish:

- physical UAV safety
- flight validation
- certification relevance
- production readiness
- controller improvement
- real-sensor equivalence
- operational reliability

## Claim boundary

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`
