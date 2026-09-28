# Phase 13C preregistration — Thirteen-Contrast Compound Interaction Attribution

## Status

**PREREGISTERED BEFORE ANY PHASE 13C DEVELOPMENT EVIDENCE IS GENERATED OR EXPOSED.**

Phase 13C is a new scientific lineage created only after the Phase 13B paired-degradation development result was permanently recorded as a failure.

Phase 13A and Phase 13B remain immutable failed lineages. Phase 13C does not replace, repair, reinterpret, or relax either result.

## Why Phase 13C exists

Phase 13B resolved the main ambiguity from Phase 13A: matched control and shifted events were construction-identical, and twelve of thirteen stress domains stayed within the locked paired coverage-loss bound.

The sole failure was the thirteenth domain, `latency_wind_calibration_compound`:

- lateral control coverage: `0.9487554905`
- lateral shifted coverage: `0.8323572474`
- paired lateral coverage delta: `-0.1163982430`
- lateral p95 error inflation: `1.4128019049x`

The next-largest lateral paired loss among the other twelve Phase 13B domains was only about `-0.0293`.

That result motivates a mechanism question, not a remediation question:

> On the exact hard base domain used by domain 13, which constituent parts of the frozen compound overlay create the observed lateral coverage loss, and is the failure attributable to a single component or to interaction among components?

Phase 13C changes no model parameter and seeks no better passing score.

## Frozen predecessor identity

Phase 13C retains exactly:

- Phase 12 scientific SHA: `8d0617a83d699cd14eae6194ce3a86a5c034dfbc`
- Phase 12 candidate SHA-256: `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`
- all Phase 12 uncertainty parameters
- point estimator
- continuity behavior
- independent coarse rescue
- output groups
- conformal targets and half-width logic
- simulation-only claim boundary

No calibration, widening, multiplier fitting, threshold fitting, controller change, or candidate modification is permitted.

## Frozen domain-13 base environment

Every Phase 13C contrast uses the exact base domain of Phase 13A/B domain 13:

`edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout`

All contrasts in a stage are cloned from the same predecessor base event before the contrast transform is applied.

Truth trajectories and predecessor availability are invariant across every contrast and the matched control.

## Six frozen compound components

The Phase 13A/B thirteenth overlay is decomposed into six preregistered components. Their magnitudes are copied from the already-frozen domain-13 definition and are not tunable.

### A — latency

- fixed estimate lag: `2 frames`

### B — bias pair

- lateral bias: `+0.04 m`
- altitude bias: `+0.08 m`

### C — lateral wind drift

- sequence lateral drift amplitude: `0.07 m`

### D — measurement-noise pair

- lateral Gaussian sigma: `0.02 m`
- altitude Gaussian sigma: `0.04 m`
- deterministic stream derived from stage seed, base sequence, frame, and the original compound-domain stream tag

### E — innovation response

When active, after physical estimate perturbation:

`innovation_out = max(0, innovation_in * 1.35 + 0.45 * lateral_estimate_delta_abs)`

When inactive, anchor innovation is unchanged.

### F — severity response

Define:

`response = clip((lateral_estimate_delta_abs + 0.5 * altitude_estimate_delta_abs) / 0.30, 0, 1)`

When active:

`severity_out = clip(severity_in + 0.12 + 0.18 * response, 0, 1)`

When inactive, severity is unchanged.

## Exactly thirteen contrast overlays

The number 13 remains a scientific constraint.

A separate no-shift matched control is retained but is **not** counted as one of the thirteen contrast overlays.

### Six singleton contrasts

1. `latency_only` = A
2. `bias_only` = B
3. `wind_only` = C
4. `noise_only` = D
5. `innovation_response_only` = E
6. `severity_response_only` = F

### Six leave-one-out contrasts

7. `full_minus_latency` = B+C+D+E+F
8. `full_minus_bias` = A+C+D+E+F
9. `full_minus_wind` = A+B+D+E+F
10. `full_minus_noise` = A+B+C+E+F
11. `full_minus_innovation_response` = A+B+C+D+F
12. `full_minus_severity_response` = A+B+C+D+E

### Frozen full compound

13. `full_compound` = A+B+C+D+E+F

The full-compound transform must be execution-equivalent to the original Phase 13 domain-13 transform for the same base event and stage seed.

No contrast may be added, removed, renamed, or altered after development exposure.

## Fresh Phase 13C evidence

Phase 13C evidence is disjoint from all Phase 13A/B evaluation evidence.

### Development

- seed: `1313135`
- families: `1393–1416`
- role: permanently seen Phase 13C development mechanism-discovery evidence

### Transfer

- seed: `1313136`
- families: `1417–1440`
- remains unexposed unless the development phenomenon-replication and construction gates pass

### Protected validation

- seed: `1313137`
- families: `1441–1464`
- remains unexposed unless a transfer-confirmation rule is separately frozen after development and transfer is authorized

### Final

- seed: `1313138`
- families: `1465–1488`
- remains unexposed unless all earlier Phase 13C stages authorize it

Each stage uses 24 families split evenly across the existing `bootstrap5`, `gap3`, `gap7`, and `gap12` intervention strata.

## Primary measurements

For the matched control and each of the thirteen contrasts, compute:

- lateral 95% coverage
- altitude 95% coverage
- lateral coverage delta versus control
- altitude coverage delta versus control
- lateral p95 absolute error
- altitude p95 absolute error
- p95 error inflation versus control
- median 95% half-width
- p95 95% half-width
- useful availability

For every contrast, useful availability and truth must remain identical to control.

## Attribution measurements

### Singleton loss

For components A–F:

`singleton_loss(component) = control_lateral_coverage - singleton_lateral_coverage`

This estimates the component's stand-alone effect on the exact domain-13 base environment.

### Leave-one-out recovery

For components A–F:

`leave_one_out_recovery(component) = leave_one_out_lateral_coverage - full_compound_lateral_coverage`

A larger positive recovery means removing that component from the full compound improves coverage more strongly, making it more necessary to the observed full interaction.

### Interaction excess

Define:

`full_loss = control_lateral_coverage - full_compound_lateral_coverage`

`sum_singleton_losses = sum(singleton_loss(A..F))`

`interaction_excess = full_loss - sum_singleton_losses`

Positive interaction excess means the complete compound loses more coverage than the additive sum of singleton losses on the same base distribution.

This is an attribution statistic, not a physical causal claim about real aircraft or sensors.

## Gate C13.1 — construction integrity

For matched control plus all thirteen contrast overlays:

- exact row-count equality
- exact truth-visible equality
- exact useful-availability equality
- exact lateral-truth equality
- exact altitude-truth equality

Required: all 13 contrast pairs pass.

## Gate C13.2 — full-compound execution equivalence

Before interpreting attribution, a deterministic fixture test must verify that the Phase 13C `full_compound` transform reproduces the existing frozen Phase 13 domain-13 transform for the same input, seed, and inference-visible state to numerical equality.

This is an implementation gate and must pass before development evidence generation.

## Gate C13.3 — fresh failure-phenomenon replication

On fresh Phase 13C development evidence, the full compound must reproduce the previously defined paired-failure phenomenon:

- full-compound lateral coverage delta versus matched control `<= -0.08`
- full-compound shifted lateral coverage `>= 0.80`

The first condition means the paired loss again exceeds the already-preregistered Phase 13B allowance. The second preserves the distinction between local interaction failure and catastrophic collapse.

If this gate fails, Phase 13C records that the Phase 13B failure did not reproduce on the fresh mechanism-study partition and stops before transfer.

## Gate C13.4 — attribution completeness

All six singleton losses, all six leave-one-out recoveries, and the interaction-excess statistic must be finite and based on non-empty available rows.

Required: complete attribution for A–F.

This gate does not require any particular component to win. Phase 13C must be allowed to falsify the idea that one component dominates.

## Gate C13.5 — zero adaptation

Before the development result:

- Phase 12 candidate changed: `false`
- domain-13 base domain changed: `false`
- component magnitudes changed: `false`
- interval recalibration: `false`
- post-hoc multiplier: `false`
- controller tuning: `false`

Any violation fails Phase 13C by construction.

## Development interpretation rule

Phase 13C development is a mechanism-discovery stage.

If C13.1, C13.2, C13.3, C13.4, and C13.5 pass:

1. preserve the full development result permanently;
2. identify the largest singleton loss using the deterministic preregistered ranking rule;
3. identify the largest leave-one-out recovery using the deterministic preregistered ranking rule;
4. record interaction excess;
5. before any transfer exposure, freeze a separate transfer-confirmation note stating the discovered component names and exact development effect sizes;
6. make no scientific or transform changes before transfer.

If C13.3 fails, development is still scientifically informative but transfer is prohibited because the compound-failure phenomenon did not reproduce.

If any construction or zero-adaptation gate fails, no attribution claim is valid.

Ties in component ranking are broken alphabetically by component label A–F; this is fixed before evidence.

## No-remediation rule

Phase 13C may not:

- change Phase 12 intervals;
- remove the latency component;
- reduce noise, bias, or drift magnitudes;
- strengthen innovation or severity response after seeing results;
- change the hard base domain;
- redefine the 13 contrasts;
- use Phase 13C development to choose a better model.

A later remediation architecture, if scientifically justified, must be a new phase with a new identity and new evidence.

## Claim boundary

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`

A Phase 13C development result may support only an attribution statement about the preregistered synthetic compound transform on the synthetic domain-13 base distribution.

It cannot establish:

- physical UAV safety
- physical wind or sensor causality
- real-flight behavior
- certification relevance
- production readiness
- controller improvement
- real-sensor equivalence
- operational reliability
