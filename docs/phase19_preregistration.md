# Phase 19 preregistration — Distribution-Wide Residual Advantage

## Status

**PREREGISTERED BEFORE PHASE 19 DEVELOPMENT EVIDENCE.**

Phase 18 is immutable and remains a protected-validation FAIL. Its final seed `1818184` remains permanently unexposed. Phase 19 is a new scientific lineage with fresh evidence and does not relax or rerun the failed Phase 18 q90 gates.

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`

## Motivation from the closed Phase 18 lineage

Phase 18 preregistered both an upper-tail q90 contrast and an independent distribution-wide RMSE confirmation.

Observed before Phase 19 preregistration:

- development: all Phase 18 gates passed;
- transfer: all Phase 18 gates passed;
- protected validation: two q90 gates failed;
- the independently preregistered RMSE confirmation passed at development, transfer, and protected validation.

Phase 19 does not reinterpret Phase 18 as a pass. It asks a narrower fresh-evidence question centered on the distribution-wide residual estimand that survived all three exposed Phase 18 partitions.

## Scientific question

> With the exact frozen Phase 17 latency coefficients and no refitting, does pure two-frame synthetic latency produce a reproducible distribution-wide one-step residual advantage in the simple context, while the analogous hard-context coefficient remains approximately neutral, as measured by both RMSE and mean absolute residual on fresh matched evidence?

This is a predictive-mechanism study about the synthetic transform only.

## Frozen objects

Exact Phase 12 candidate SHA-256:

`e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`

Exact Phase 14 bridge SHA-256:

`0443d4e45a1966c77544c5c9965de8caec6e622c79ef8c2ce47aee82a3c95981`

Exact Phase 17 fit candidate SHA-256:

`2ca52a418f5616e0e83ef84d0c9238ee429260cd4de7a553356b0c1bba44d8e0`

Exact failed Phase 18 protected result SHA-256:

`ad96ca1a5119fcd594a84fd72a04f8efcc377ba788383d90dda9ef7eecad4431`

Phase 19 must explicitly verify `phase18_pass = false` before generating evidence.

No coefficient is fitted in Phase 19.

## Frozen intervention and contexts

Pure latency only:

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
| development | `1919191` | `2025–2048` |
| transfer | `1919192` | `2049–2072` |
| protected | `1919193` | `2073–2096` |
| final | `1919194` | `2097–2120` |

Each role uses 24 fresh families split evenly across the inherited `bootstrap5`, `gap3`, `gap7`, and `gap12` strata.

Only development is authorized initially.

## Matched construction

For each context:

1. generate one fresh base event;
2. create an exact unchanged control copy;
3. create an exact pure-two-frame-lag copy;
4. preserve row identity, truth-visible mask, useful availability, truth, severity, and anchor innovation;
5. verify Phase 12 95% half-width identity to tolerance `1e-12`;
6. form one-to-one adjacent matched transitions where both copies begin inside the historical reference analysis box:
   - lateral `|e_x| <= 0.30 m`;
   - altitude `|e_z| <= 0.85 m`.

At least 500 matched transitions are required per context.

The historical box remains an analysis region only and is not a physical invariant-set claim.

## Frozen coefficients and residuals

On fresh latency transitions compute lateral one-step residuals under:

1. frozen Phase 14 lateral coefficient;
2. frozen Phase 17 context-control lateral coefficient;
3. frozen Phase 17 context-latency lateral coefficient.

No development diagnostic coefficient enters any Phase 19 gate.

Primary distribution-wide statistic:

- signed residual RMSE.

Independent distribution-wide confirmation statistic:

- mean absolute residual (MAE).

q90 absolute residual is retained as descriptive context only and is **not** a Phase 19 pass/fail gate. This is deliberate because the stronger Phase 18 q90 claim failed protected validation and is not being retried under new thresholds.

## Development gates

### D19.1 lineage integrity

Require exact hashes for Phase 12, Phase 14, Phase 17 fit candidate, and the failed Phase 18 protected result. The Phase 18 protected result must remain `phase18_pass = false`.

### D19.2 matched construction and width identity

Both contexts must have:

- exact paired construction integrity;
- exact Phase 12 95% width identity;
- at least 500 matched transitions.

### D19.3 simple-context RMSE advantage

Inherited unchanged from Phase 18 R18.7:

`RMSE(simple latency-fit residual) / RMSE(simple Phase14 residual) <= 0.95`.

### D19.4 hard-context RMSE neutrality

Inherited unchanged from Phase 18 R18.7:

`0.90 <= RMSE(hard latency-fit residual) / RMSE(hard Phase14 residual) <= 1.10`.

### D19.5 RMSE context-advantage gap

Inherited unchanged from Phase 18 R18.7.

Define:

`I_rmse = 1 - RMSE(latency-fit residual) / RMSE(Phase14 residual)`.

Require:

`I_rmse_simple - I_rmse_hard >= 0.05`.

### D19.6 simple-context MAE advantage

New independent distribution-wide confirmation fixed before Phase 19 evidence:

`MAE(simple latency-fit residual) / MAE(simple Phase14 residual) <= 0.95`.

### D19.7 hard-context MAE neutrality

`0.90 <= MAE(hard latency-fit residual) / MAE(hard Phase14 residual) <= 1.10`.

### D19.8 MAE context-advantage gap

Define:

`I_mae = 1 - MAE(latency-fit residual) / MAE(Phase14 residual)`.

Require:

`I_mae_simple - I_mae_hard >= 0.05`.

### D19.9 static latency degradation remains present

Inherited unchanged from Phase 17 M17.9 / Phase 18 R18.8.

Context S lateral:

- p95 error inflation `>= 1.10`;
- coverage delta `<= -0.01`.

Context H lateral:

- p95 error inflation `>= 1.10`;
- coverage delta `<= -0.05`.

### D19.10 zero adaptation and claim boundary

Require:

- no refit;
- no coefficient clipping;
- no Phase 12 interval change;
- no Phase 14 change;
- no context change;
- no latency-magnitude change;
- no controller change;
- no post-hoc threshold change;
- `simulation_only = true`;
- `safety_acceptance = false`;
- `controller_tuning_allowed = false`.

Development PASS requires **all D19.1–D19.10**.

## Progression rule

If development FAILS:

- close Phase 19 at development;
- transfer `1919192`, protected `1919193`, and final `1919194` remain unexposed.

If development PASSES:

- freeze the exact scientific SHA and development result before transfer;
- proceed sequentially with unchanged implementation and thresholds;
- never expose a later role unless the immediately prior role passed all gates.

## Interpretation boundary

A PASS would support only:

> On fresh matched synthetic evidence, the frozen simple-context latency coefficient reduced distribution-wide one-step lateral residual error relative to the frozen Phase14 coefficient on both RMSE and MAE, while the hard-context coefficient remained approximately neutral and static latency-induced level-error degradation persisted.

A PASS would not repair Phase 18's failed q90 claim and would not establish physical latency causality or physical UAV safety.

No physical-flight, real-sensor, full-simulator invariance, certification, controller-improvement, production-readiness, or operational-safety claim is authorized.