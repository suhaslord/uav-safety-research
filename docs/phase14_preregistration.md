# Phase 14 preregistration — uncertainty-gated recoverability bridge

## Status

**PREREGISTERED BEFORE ANY PHASE 14 EVALUATION EVIDENCE.**

Phase 14 is a new simulation-only lineage. It does not modify or reinterpret the closed Phase 12 uncertainty model, the failed Phase 13A/13B external-validity lineages, or the replicated Phase 13C latency-attribution result.

The Phase 13C head from which this branch starts is `8aa2f7c274b6824b765e7a46e2d9ec4c4767e635`.

The exact frozen Phase 12 Iteration-3 predecessor remains:

- scientific SHA: `8d0617a83d699cd14eae6194ce3a86a5c034dfbc`
- candidate SHA-256: `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`

## Scientific question

Can the frozen Phase 12 uncertainty half-width be translated, through a predeclared data-derived one-step surrogate, into a **conditional bounded-disturbance invariant-set statement** that survives fresh simulation evidence — including the exact fixed two-frame latency stress identified by Phase 13C?

The result is intentionally conditional and narrow. Phase 14 does **not** attempt to prove the full simulator, PX4/Gazebo, a physical UAV, or any controller safe.

## Locked recoverable set

Phase 14 inherits the recoverable box from the already-merged simplified invariance benchmark and will not retune it after seeing Phase 14 data:

- lateral signed estimation error: `|e_x| <= 0.30 m`
- altitude signed estimation error: `|e_z| <= 0.85 m`

where

- `e_x = estimate_lateral_x - truth_lateral_x`
- `e_z = estimate_altitude - truth_altitude`.

The prior hand-selected surrogate `A = diag(0.65, 0.70)` and prior hand-selected disturbance bounds `0.05 m / 0.12 m` are **not** carried forward as scientific inputs. Phase 14 replaces them with a frozen identification procedure.

## Frozen Phase 14 identification procedure

Phase 14 first exposes one explicit **surrogate-fit** role. This role is training/identification evidence, not a pass/fail evaluation role.

Surrogate-fit identity:

- seed: `1414140`
- families: `1489–1520` inclusive
- domains: the frozen Phase 12 scale-fit domain tuple

Only this role may be used to fit the Phase 14 bridge candidate.

For each sequence, form adjacent one-frame transitions where:

1. both rows are truth-visible,
2. both rows are usable under the inherited Phase 14/Phase 12 availability rule,
3. `frame_index[k+1] = frame_index[k] + 1`, and
4. the current signed error is inside the fixed recoverable box on the fitted axis.

For each axis independently, fit the no-intercept diagonal one-step surrogate

`e[k+1] = a * e[k] + w[k]`

using ordinary least squares through the origin:

`a = sum(e[k] * e[k+1]) / sum(e[k]^2)`.

No clipping or forced stabilization is allowed. If the denominator is numerically degenerate or `|a| >= 1`, the candidate is invalid and Phase 14 stops before downstream evidence.

### Uncertainty-normalized disturbance score

For each fitted transition, compute the frozen Phase 12 95% half-width `h[k]` at the current row and the one-step residual

`w[k] = e[k+1] - a * e[k]`.

Define

`s[k] = |w[k]| / max(h[k], 1e-9)`.

For each axis, freeze `gamma` as the finite-sample 99% conformal upper quantile of `s`:

- sort `n` scores ascending,
- rank `k = ceil((n + 1) * 0.99)`, capped at `n`,
- `gamma = score[k]` using one-based rank.

No development evidence may change `a`, `gamma`, the recoverable box, or this fitting rule.

### Algebraic uncertainty-admission cap

Phase 14 reserves 10% of the one-step contraction budget and derives the maximum admissible Phase 12 half-width

`h_cap = 0.90 * ((1 - |a|) * r) / gamma`

for each axis, where `r` is the fixed recoverable-set half-width.

A transition is **Phase14-admitted** only when both current-axis Phase 12 half-widths satisfy their frozen caps.

For the fitted surrogate, admitted rows satisfy the analytic bounded-disturbance envelope

`|w_i| <= gamma_i * h_i <= 0.90 * (1 - |a_i|) * r_i`.

Therefore the analytic one-step image bound is

`|a_i| r_i + gamma_i h_cap_i <= r_i`,

with a nominal 10% reserve of the contraction budget.

This is a conditional surrogate statement only. The normalized-residual envelope itself must survive fresh evidence.

## Fresh evaluation roles

The bridge candidate is immutable after surrogate-fit.

| Role | Seed | Families | Evidence rule |
|---|---:|---:|---|
| development | `1414141` | `1521–1544` | first pass/fail evaluation; permanently seen after run |
| transfer | `1414142` | `1545–1568` | expose only if development passes |
| protected | `1414143` | `1569–1592` | expose only if transfer passes |
| final | `1414144` | `1593–1616` | expose once only if protected passes |

Natural evaluation domains are inherited without retuning:

- development: frozen Phase 12 `DEV_DOMAINS`
- transfer: frozen Phase 12 `TRANSFER_DOMAINS`
- protected: frozen Phase 12 `VALIDATION_DOMAINS`
- final: frozen Phase 12 `FINAL_DOMAINS`

Every stage also contains one separately scored **latency challenge cohort** generated from the exact frozen Phase 13 `fixed_latency_2f` profile and its frozen base domain `small_scale+temporal_dropout`.

The latency challenge changes no controller parameter and no Phase 12 interval parameter. It is an evaluation stress only.

## Locked Phase 14 gates

A stage passes only if every gate below passes. Thresholds are frozen before development evidence.

### P14.1 — Candidate and lineage integrity

- exact Phase 12 candidate SHA-256 matches the frozen predecessor,
- recoverable half-widths are exactly `0.30 / 0.85 m`,
- bridge candidate was fitted only on seed `1414140` / families `1489–1520`,
- downstream scientific implementation matches the frozen bridge scientific SHA.

### P14.2 — Contractive fitted surrogate

For both axes:

- finite `a`,
- `|a| < 1`,
- finite positive `gamma`,
- finite positive `h_cap`.

### P14.3 — Conditional analytic robust-positive-invariance check

For both axes:

`|a| * r + gamma * h_cap <= r`

with nonnegative numerical margin.

This gate verifies only the frozen surrogate under its frozen uncertainty-admission rule.

### P14.4 — Natural normalized-residual envelope survival

Among natural evaluation transitions that begin inside the fixed recoverable box and are Phase14-admitted:

- lateral normalized-residual coverage `>= 0.985`
- altitude normalized-residual coverage `>= 0.985`

where coverage means `|w| <= gamma * h`.

### P14.5 — Natural empirical one-step containment

Among the same natural admitted transitions:

- lateral next-state containment within `|e_x[k+1]| <= 0.30 m` `>= 0.99`
- altitude next-state containment within `|e_z[k+1]| <= 0.85 m` `>= 0.99`.

### P14.6 — Natural admission is nontrivial

At least `50%` of eligible natural transitions must satisfy both frozen half-width caps.

### P14.7 — Latency normalized-residual envelope survival

On the exact fixed-two-frame-latency challenge cohort, among transitions that begin inside the fixed recoverable box and are Phase14-admitted:

- lateral normalized-residual coverage `>= 0.95`
- altitude normalized-residual coverage `>= 0.95`.

### P14.8 — Latency empirical one-step containment

On the same latency-admitted transitions:

- lateral next-state containment `>= 0.97`
- altitude next-state containment `>= 0.97`.

### P14.9 — Latency admission is not vacuous

At least `30%` of eligible latency transitions must remain Phase14-admitted.

### P14.10 — Zero adaptation and claim boundary

Required throughout:

- no controller tuning,
- no Phase 12 recalibration or interval widening,
- no post-development changes to `a`, `gamma`, `h_cap`, recoverable-set size, stress magnitude, or gates,
- `simulation_only = true`,
- `safety_acceptance = false`,
- `controller_tuning_allowed = false`.

## Stop rules

1. If surrogate-fit cannot produce a valid contractive candidate, Phase 14 stops before development.
2. If development fails any gate, transfer/protected/final remain unexposed and Phase 14 closes as a negative result.
3. If transfer fails, protected/final remain unexposed.
4. If protected fails, final remains unexposed.
5. Final is exposed exactly once and is never rerun for a better scientific outcome.
6. Technical failures before candidate recovery/evidence generation may be fixed only if documented and demonstrated not to change scientific definitions.

## Interpretation boundary

A Phase 14 PASS would support only the following form of statement:

> Under the frozen AegisLand simulation generator, a preregistered diagonal error surrogate fitted on separate identification evidence, and a frozen uncertainty-admission rule derived from the Phase 12 95% half-width, the fixed `±0.30 m / ±0.85 m` recoverable box satisfied the preregistered conditional surrogate-invariance and empirical one-step checks across the exposed Phase 14 evidence roles.

It would **not** establish:

- physical-flight safety,
- PX4/Gazebo closed-loop invariance as a theorem,
- certification relevance,
- real-sensor disturbance bounds,
- autonomous landing safety,
- controller improvement,
- production readiness,
- operational reliability.
