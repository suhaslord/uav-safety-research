# Phase 15 preregistration — recoverability feasibility frontier

## Status

**PREREGISTERED BEFORE ANY PHASE 15 DEVELOPMENT / TRANSFER / PROTECTED / FINAL EVIDENCE.**

Phase 15 is a new simulation-only lineage motivated by the closed Phase 14 negative result. Phase 14 remains immutable and failed. Phase 15 does not relax the Phase 14 uncertainty cap, resize the old recoverable box to manufacture a pass, or reinterpret the Phase 12 interval as a transition disturbance.

## Scientific question

When current-state uncertainty and one-step transition disturbance are kept as separate objects, what surrogate robust-positive-invariance box size is implied by the observed transition-residual distribution, and does that **feasibility frontier** replicate on fresh simulation evidence — including the fixed-two-frame latency challenge identified by Phase 13C?

Phase 15 is primarily a characterization / replication study. A Phase 15 PASS means the preregistered frontier characterization replicated. It does **not** mean the historical `±0.30 m / ±0.85 m` box became invariant.

## Immutable predecessor identities

Frozen Phase 12 candidate:

- scientific SHA: `8d0617a83d699cd14eae6194ce3a86a5c034dfbc`
- candidate SHA-256: `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`

Closed Phase 14 scientific SHA:

- `a80cd02d0781e7b3dde9ea523b2fe17ecd44002c`

Closed Phase 14 bridge candidate SHA-256:

- `0443d4e45a1966c77544c5c9965de8caec6e622c79ef8c2ce47aee82a3c95981`

Phase 14 identification artifact:

- run `34010431456`
- artifact `9982290446`
- fit seed `1414140`
- fit families `1489–1520`

These Phase 14 identification data are already permanently seen. Phase 15 may use them to freeze its frontier candidate before fresh Phase 15 evaluation. This does not constitute new evidence exposure.

## Historical reference box — fixed comparator, not a target to tune

The old merged recoverable-set benchmark remains exactly:

- lateral `r_ref,x = 0.30 m`
- altitude `r_ref,z = 0.85 m`

Phase 15 will never modify those reference values.

## Separate mathematical objects

### Object 1 — current-state uncertainty

The frozen Phase 12 95% half-width `h95` remains a current estimation-error uncertainty quantity.

Phase 15 reports the **state-uncertainty containment fraction** among transitions beginning inside the historical box:

`h95_lateral <= 0.30 m` and `h95_altitude <= 0.85 m`.

This is not used as a process-disturbance bound.

### Object 2 — one-step transition disturbance

Phase 15 keeps the Phase 14 fitted diagonal surrogate coefficients fixed:

`e[k+1] = a * e[k] + w[k]`.

No coefficient is refit on Phase 15 evaluation data.

For each axis, Phase 15 computes absolute one-step residuals

`|w[k]| = |e[k+1] - a e[k]|`

on transitions that begin inside the historical reference box.

## Frozen frontier construction

Using only the already-seen Phase 14 identification transitions, freeze finite-sample conformal absolute-residual bounds at exactly four preregistered levels:

- `q = 0.90`
- `q = 0.95`
- `q = 0.975`
- `q = 0.99`

For `n` residuals, sort ascending and use one-based rank

`k = min(n, ceil((n+1)q))`.

Let the resulting absolute-residual bound be `w_q`.

For the fixed diagonal surrogate, the corresponding minimal axis-aligned robust-positive-invariant half-width is

`r_min(q) = w_q / (1 - |a|)`.

No reserve factor is used here. Phase 15 is characterizing the direct residual-based feasibility frontier itself.

The frontier must be monotone in `q` by construction.

### Already-seen identification expectation

Because the Phase 14 identification data are already seen, it is permissible and important to state the expected frozen frontier before fresh Phase 15 evaluation.

Approximate identification values to be reproduced exactly by the freeze artifact:

Lateral:

- `r_min(0.90) ≈ 0.520 m`
- `r_min(0.95) ≈ 0.709 m`
- `r_min(0.975) ≈ 1.014 m`
- `r_min(0.99) ≈ 1.798 m`

Altitude:

- `r_min(0.90) ≈ 1.206 m`
- `r_min(0.95) ≈ 1.650 m`
- `r_min(0.975) ≈ 2.277 m`
- `r_min(0.99) ≈ 3.366 m`

Thus even the identification `q=0.90` frontier lies above the historical reference box on both axes. Phase 15 asks whether that scale mismatch replicates on fresh partitions.

## Fresh Phase 15 evidence roles

| Role | Seed | Families | Rule |
|---|---:|---:|---|
| development | `1515151` | `1617–1640` | first pass/fail evaluation; permanently seen after run |
| transfer | `1515152` | `1641–1664` | expose only if development passes |
| protected | `1515153` | `1665–1688` | expose only if transfer passes |
| final | `1515154` | `1689–1712` | expose exactly once only if protected passes |

Natural domain tuples are inherited unchanged from Phase 12:

- development → Phase 12 `DEV_DOMAINS`
- transfer → Phase 12 `TRANSFER_DOMAINS`
- protected → Phase 12 `VALIDATION_DOMAINS`
- final → Phase 12 `FINAL_DOMAINS`

Every stage also includes the exact Phase 13 `fixed_latency_2f` stress on base domain `small_scale+temporal_dropout`.

## Locked Phase 15 gates

### F15.1 — lineage integrity

Required:

- exact frozen Phase 12 candidate digest,
- exact frozen Phase 14 bridge candidate digest,
- exact frozen Phase 15 frontier candidate digest,
- historical reference box remains `0.30 / 0.85 m`,
- no scientific implementation change after frontier freeze.

### F15.2 — frontier construction integrity

For both axes:

- frozen `|a| < 1`,
- all four `w_q` finite and positive,
- all four `r_min(q)` finite and positive,
- `w_q` monotone nondecreasing in q,
- `r_min(q)` monotone nondecreasing in q.

### F15.3 — natural residual-envelope replication

For each axis and each frozen q, fresh natural residual coverage must be at least:

`q - 0.03`.

Therefore the locked minimums are:

- q90 → `>=0.87`
- q95 → `>=0.92`
- q97.5 → `>=0.945`
- q99 → `>=0.96`.

### F15.4 — natural q90 infeasibility replication

Using the **fresh diagnostic q90 conformal residual bound** with the frozen `a`, the fresh empirical minimal RPI half-width must still exceed the historical reference half-width on both axes:

- lateral `r_emp,90 > 0.30 m`
- altitude `r_emp,90 > 0.85 m`.

This is the primary fresh replication of the Phase 14 feasibility conclusion.

### F15.5 — natural state uncertainty remains a distinct, nontrivial object

Among natural transitions beginning inside the historical box, at least `25%` must satisfy both:

- Phase 12 lateral h95 `<=0.30 m`
- Phase 12 altitude h95 `<=0.85 m`.

This gate is deliberately separate from F15.4. It tests that the current-state uncertainty can still fit inside the historical box for a nontrivial subset even while the transition-residual RPI frontier remains larger.

### F15.6 — latency residual-envelope replication

On the exact fixed-two-frame latency challenge, for each axis and frozen q, residual coverage must be at least:

`q - 0.05`.

Locked minimums:

- q90 → `>=0.85`
- q95 → `>=0.90`
- q97.5 → `>=0.925`
- q99 → `>=0.94`.

### F15.7 — latency q90 infeasibility replication

Using the fresh latency diagnostic q90 residual bound with frozen `a`, the empirical minimal RPI half-width must exceed the historical reference half-width on both axes.

### F15.8 — latency state-uncertainty containment is nontrivial

At least `25%` of latency-challenge transitions beginning inside the historical box must satisfy both Phase 12 h95 half-widths within the historical reference half-widths.

### F15.9 — frontier direction is stable

For natural and latency cohorts separately, on both axes:

`r_emp(0.90) <= r_emp(0.95) <= r_emp(0.975) <= r_emp(0.99)`.

### F15.10 — zero adaptation and claim boundary

Required throughout:

- no controller tuning,
- no Phase 12 recalibration,
- no refit of `a` on Phase 15 evaluation data,
- no post-development change to q levels, residual bounds, reference box, stress magnitude, gates, or tolerances,
- `simulation_only = true`,
- `safety_acceptance = false`,
- `controller_tuning_allowed = false`.

## Stop rules

1. Freeze the frontier only from already-seen Phase 14 identification evidence.
2. Development failure closes the Phase 15 lineage; transfer/protected/final remain unexposed.
3. Transfer failure leaves protected/final unexposed.
4. Protected failure leaves final unexposed.
5. Final is exposed exactly once and never rerun for a better scientific outcome.
6. Technical failures before evidence generation may be fixed only if they are documented and do not alter the scientific definitions.

## Supported interpretation if Phase 15 passes

A PASS supports only a statement of this form:

> In the frozen AegisLand simulation generator, the transition-residual-based surrogate RPI feasibility frontier frozen from prior identification evidence replicated across the exposed fresh Phase 15 partitions, and the historical `±0.30 m / ±0.85 m` box remained below the q90 transition-residual frontier even while Phase 12 current-state uncertainty fit inside that box for a nontrivial subset of transitions.

It does **not** establish physical-flight safety, full-simulator invariance, certification relevance, controller improvement, production readiness, or operational reliability.
