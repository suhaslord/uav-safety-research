# Phase 15 latency-frontier forensics

## Scope

This is post-hoc analysis of the already-seen Phase 15 development artifact only. It does not expose transfer, protected, or final evidence and does not reopen Phase 15.

## Why F15.7 failed

The fresh fixed-two-frame latency cohort produced a much smaller transition-residual frontier than the frozen natural identification frontier.

Fresh latency q90 minimal RPI half-width:

- lateral `0.2982139604 m` vs historical `0.30 m`
- altitude `0.5549244860 m` vs historical `0.85 m`

At the same time the frozen Phase 15 residual bounds substantially overcovered the latency residuals:

- lateral q90 frozen-bound coverage `97.88%`
- altitude q90 frozen-bound coverage `98.54%`

That is why the preregistered latency-infeasibility hypothesis failed.

## Suggestive temporal pattern in the already-seen artifact

The following comparison is **not causal** because the Phase 15 natural cohort uses the Phase 12 development-domain mixture while the latency cohort uses the dedicated `small_scale+temporal_dropout` base domain. It is recorded only to motivate a fresh matched-pair experiment.

Among transitions beginning inside the historical reference box:

### Lateral

Natural cohort:

- median `|e[k+1]-e[k]|`: `0.07073 m`
- p90 `|e[k+1]-e[k]|`: `0.23551 m`
- p90 frozen-surrogate residual: `0.21060 m`
- diagnostic no-intercept one-step coefficient: `0.5615`
- adjacent signed-error correlation: `0.3181`

Latency cohort:

- median `|e[k+1]-e[k]|`: `0.03358 m`
- p90 `|e[k+1]-e[k]|`: `0.10085 m`
- p90 frozen-surrogate residual: `0.11569 m`
- diagnostic no-intercept one-step coefficient: `0.8886`
- adjacent signed-error correlation: `0.8260`

This pattern is consistent with a hypothesis that stale two-frame estimates can create **more persistent level error** while reducing frame-to-frame innovation / residual magnitude.

## Important limitation

The altitude cross-cohort comparison does not show the same simple pattern, and neither axis is a matched causal comparison in Phase 15. The latency cohort's base domain is different from the natural cohort's domain mixture.

Therefore Phase 15 does **not** support a causal claim that latency smooths residuals.

## Next preregistered question

A new lineage should compare, on the **same seed, families, base domain, truth rows, and useful-availability mask**:

1. exact no-latency control, versus
2. exact frozen `fixed_latency_2f` overlay.

The next experiment should separately score:

- absolute/level estimation error,
- Phase 12 uncertainty coverage,
- adjacent signed-error persistence,
- raw one-frame increment magnitude,
- frozen Phase 14 one-step residual magnitude,
- residual-based q90 feasibility frontier.

That matched design can test whether latency worsens level accuracy while making the error trajectory more temporally persistent / locally smoother.

`simulation_only = true`
`safety_acceptance = false`
`controller_tuning_allowed = false`
