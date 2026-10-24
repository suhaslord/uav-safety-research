# Phase 18 preregistration — Residual Advantage Confirmation

## Status

**PREREGISTERED BEFORE PHASE 18 DEVELOPMENT EVIDENCE.**

Phase 17 remains an immutable all-gates FAIL. Phase 18 does not relax Phase 17 coefficient-transfer or coefficient-proximity thresholds and does not rerun its prohibited downstream evidence.

Phase 18 asks a narrower question based on the Phase 17 residual gates that independently passed.

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`

## Scientific question

> With the exact frozen Phase 17 fit coefficient object and no refitting, does the simple-context latency coefficient again produce a substantial out-of-sample residual advantage over the frozen Phase 14 coefficient while the analogous hard-context advantage remains negligible, even though pure latency continues to worsen lateral level error in both contexts?

This is a simulation-only predictive-mechanism replication. It is not a controller or uncertainty-model promotion.

## Frozen objects

Exact Phase 12 candidate SHA-256:

`e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`

Exact Phase 14 bridge SHA-256:

`0443d4e45a1966c77544c5c9965de8caec6e622c79ef8c2ce47aee82a3c95981`

Exact Phase 17 fit candidate SHA-256:

`2ca52a418f5616e0e83ef84d0c9238ee429260cd4de7a553356b0c1bba44d8e0`

The Phase 17 fit object is used only as a frozen diagnostic coefficient source. Its use does **not** convert Phase 17 into a pass.

Frozen lateral coefficients:

- Phase 14 `a = 0.6102677720` approximately, read from exact candidate;
- simple control fit `a = 0.5470675029`;
- simple latency fit `a = 0.8811661057`;
- hard control fit `a = 0.0931675212`;
- hard latency fit `a = 0.5426158628`.

No coefficient is refit in Phase 18.

## Frozen intervention and contexts

Pure latency intervention only:

- exact 2-frame lag;
- Phase 13C component A;
- no innovation response;
- no severity response;
- no bias;
- no wind;
- no measurement-noise injection;
- no Phase 12 recalibration;
- no controller change.

Context S:

`small_scale+temporal_dropout`

Context H:

`edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout`

## Fresh evidence partitions

| Role | Seed | Families |
|---|---:|---|
| development | `1818181` | `1929–1952` |
| transfer | `1818182` | `1953–1976` |
| protected | `1818183` | `1977–2000` |
| final | `1818184` | `2001–2024` |

Each role uses exactly 24 fresh families split evenly across `bootstrap5`, `gap3`, `gap7`, and `gap12`.

Only development is authorized initially.

## Matched construction

For each context:

1. generate one fresh base event;
2. clone exact control and pure-two-frame-lag copies;
3. preserve row identity, truth-visible mask, useful-availability mask, truth, severity, and anchor innovation;
4. verify exact Phase 12 95% half-width identity to `1e-12`;
5. form one-to-one adjacent matched transitions where both copies begin inside the historical reference analysis box:
   - lateral `|e_x| <= 0.30 m`;
   - altitude `|e_z| <= 0.85 m`.

At least 500 matched temporal transitions are required per context.

The box remains an analysis region only, not a physical invariant-set claim.

## Frozen residual estimands

On fresh latency transitions compute lateral residuals under:

1. frozen Phase 14 lateral coefficient;
2. frozen Phase 17 context-control lateral coefficient;
3. frozen Phase 17 context-latency lateral coefficient.

Primary statistic:

- finite-conformal q90 absolute residual.

Independent confirmation statistic:

- signed residual RMSE.

No development coefficient or residual quantile is fitted.

Development diagnostic coefficients may be reported descriptively but **are not gate inputs**. This is intentional: Phase 18 tests predictive residual advantage, not exact coefficient location.

## Development gates

### R18.1 lineage integrity

Require exact hashes for Phase 12, Phase 14, and Phase 17 fit candidate, and verify that Phase 17 remains recorded as a FAIL.

### R18.2 matched construction / width identity

Both contexts must have:

- exact paired construction integrity;
- exact Phase 12 width identity;
- at least 500 matched transitions.

### R18.3 simple q90 advantage versus Phase 14

Inherited unchanged from Phase 17 M17.6:

`q90(simple latency-fit residual) / q90(simple Phase14 residual) <= 0.90`.

### R18.4 simple q90 advantage versus control fit

Inherited unchanged from Phase 17 M17.6:

`q90(simple latency-fit residual) / q90(simple control-fit residual) <= 0.95`.

### R18.5 hard q90 advantage remains limited

Inherited unchanged from Phase 17 M17.7:

`0.90 <= q90(hard latency-fit residual) / q90(hard Phase14 residual) <= 1.10`.

### R18.6 simple-vs-hard q90 improvement gap

Inherited unchanged from Phase 17 M17.8.

Define:

`I_q90 = 1 - q90(latency-fit residual) / q90(Phase14 residual)`.

Require:

`I_q90_simple - I_q90_hard >= 0.08`.

### R18.7 independent RMSE confirmation

New preregistered confirmation metric, motivated by the prior q90 result but fixed before Phase 18 evidence.

Simple context:

`RMSE(simple latency-fit residual) / RMSE(simple Phase14 residual) <= 0.95`.

Hard context:

`0.90 <= RMSE(hard latency-fit residual) / RMSE(hard Phase14 residual) <= 1.10`.

Define:

`I_rmse = 1 - RMSE(latency-fit residual) / RMSE(Phase14 residual)`.

Require:

`I_rmse_simple - I_rmse_hard >= 0.05`.

### R18.8 static latency degradation remains present

Inherited unchanged from Phase 17 M17.9.

Context S lateral:

- p95 error inflation `>= 1.10`;
- coverage delta `<= -0.01`.

Context H lateral:

- p95 error inflation `>= 1.10`;
- coverage delta `<= -0.05`.

### R18.9 cross-statistic context ordering

The simple residual advantage must be larger than the hard residual advantage on **both** q90 and RMSE.

No exact development coefficient-location threshold is used.

### R18.10 zero adaptation / claim boundary

Require:

- no refit;
- no coefficient clipping;
- no context change;
- no latency-magnitude change;
- no Phase 12 interval change;
- no Phase 14 change;
- no controller change;
- no post-hoc threshold change;
- `simulation_only = true`;
- `safety_acceptance = false`;
- `controller_tuning_allowed = false`.

Phase 18 development PASS requires **all R18.1–R18.10**.

## Progression rule

If development FAILS:

- close Phase 18 at development;
- transfer `1818182`, protected `1818183`, and final `1818184` remain unexposed.

If development PASSES:

- freeze the exact Phase 18 development scientific SHA and result identity before exposing transfer;
- do not refit or alter the frozen coefficients.

## Claim boundary

A PASS would support only:

> On fresh matched synthetic evidence, the frozen simple-context latency coefficient again reduced out-of-sample one-step residuals materially relative to the frozen Phase14 coefficient, while the hard-context coefficient produced little advantage; the contrast appeared in both q90 and RMSE and did not erase static latency-induced level-error degradation.

No physical latency causality, physical-flight safety, full-simulator invariance, certification relevance, controller improvement, production readiness, or operational-safety claim is authorized.