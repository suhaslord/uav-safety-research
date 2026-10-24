# Phase 20 preregistration — Five-Factor Context Attenuation Shapley Decomposition

## Status

**PREREGISTERED BEFORE PHASE 20 DEVELOPMENT EVIDENCE.**

Phase 19 is closed as a final-holdout PASS. Phase 18 remains an immutable protected-validation FAIL. Phase 20 does not refit any coefficient and does not retry the failed Phase 18 q90 thresholds.

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`

## Motivation

Phase 19 established that the exact frozen Phase 17 simple-context latency coefficient produced a repeatable distribution-wide one-step lateral residual advantage relative to the frozen Phase 14 coefficient on RMSE and MAE across development, transfer, protected, and final evidence, while the analogous hard-context coefficient remained approximately neutral.

That result does not identify why the simple and hard contexts differ.

The two contexts differ by exactly five additional synthetic perception modifiers. Phase 20 asks which of those modifiers attenuate transfer of the frozen simple-context coefficient, without fitting or tuning anything on Phase 20 evidence.

## Scientific question

> When the five synthetic modifiers separating the simple and hard contexts are added in all possible combinations, how is the loss of distribution-wide residual advantage of the exact frozen simple-context latency coefficient attributed across those modifiers, and does the endpoint attenuation reproduce on fresh evidence?

This is a simulation-only attribution study of a synthetic transform and synthetic context construction.

## Frozen predecessor objects

Exact Phase 12 candidate SHA-256:

`e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`

Exact Phase 14 bridge SHA-256:

`0443d4e45a1966c77544c5c9965de8caec6e622c79ef8c2ce47aee82a3c95981`

Exact Phase 17 fit candidate SHA-256:

`2ca52a418f5616e0e83ef84d0c9238ee429260cd4de7a553356b0c1bba44d8e0`

Exact Phase 19 final result SHA-256:

`8c23b9b9c8c9fb2f9146bf739e52074f8709d2fe9a81c794e64fb43f360acebf`

Phase 20 must verify that the Phase 19 final result remains `phase19_pass = true`, that `phase18_failure_preserved = true`, and that `q90_is_descriptive_only = true` before generating evidence.

No coefficient is fitted in Phase 20.

## Frozen coefficients

From the exact Phase 17 fit object:

- frozen Phase 14 lateral coefficient `a14`;
- frozen Phase 17 simple-context latency coefficient `aS`;
- frozen Phase 17 hard-context latency coefficient `aH`.

The primary attenuation map uses `aS` relative to `a14` on every factorial context. `aH` is used only for the preregistered endpoint crossover check.

## Frozen intervention

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

## Factorial context construction

Shared base context:

`small_scale+temporal_dropout`

Five additional modifiers, in fixed canonical order:

1. `edge`
2. `oblique`
3. `dim`
4. `blur_noise`
5. `low_contrast`

Phase 20 evaluates the complete power set of those five modifiers: exactly `2^5 = 32` contexts.

For any subset `M`, construct the domain string by preserving this global order:

`edge` (if present) → `small_scale` → `oblique` (if present) → `dim` (if present) → `blur_noise` (if present) → `low_contrast` (if present) → `temporal_dropout`.

Therefore:

- empty subset is exactly `small_scale+temporal_dropout`;
- full subset is exactly `edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout`.

No other modifier is permitted.

## Fresh evidence partitions

| Role | Seed | Families |
|---|---:|---|
| development | `2020201` | `2121–2144` |
| transfer | `2020202` | `2145–2168` |
| protected | `2020203` | `2169–2192` |
| final | `2020204` | `2193–2216` |

Each role uses 24 fresh families split evenly across the inherited `bootstrap5`, `gap3`, `gap7`, and `gap12` strata.

Only development is authorized initially.

## Matched construction

For each of the 32 factorial contexts:

1. generate one fresh base event;
2. create an exact unchanged control copy;
3. create an exact pure-two-frame-lag copy;
4. preserve row identity, truth-visible mask, useful availability, truth, severity, and anchor innovation;
5. verify Phase 12 95% half-width identity to tolerance `1e-12`;
6. form one-to-one adjacent matched transitions where both copies begin inside the historical analysis box:
   - lateral `|e_x| <= 0.30 m`;
   - altitude `|e_z| <= 0.85 m`.

At least 500 matched transitions are required for every context.

The historical box remains an analysis region only and is not a physical invariant-set claim.

## Residual statistics

On fresh latency transitions for each factorial context compute lateral one-step signed residuals under:

- `a14`;
- `aS`;
- `aH`.

Primary statistic:

- signed residual RMSE.

Independent confirmation statistic:

- mean absolute residual (MAE).

q90 absolute residual is retained as descriptive context only and is not a Phase 20 gate.

For statistic `T ∈ {RMSE, MAE}`, define the simple-coefficient advantage:

`A_T(M) = 1 - T(residual using aS on context M) / T(residual using a14 on context M)`.

Positive values favor the frozen simple-context latency coefficient; negative values favor Phase 14.

Define total endpoint attenuation:

`Delta_T = A_T(empty) - A_T(full)`.

## Exact Shapley attribution

For each modifier `j`, compute its exact Shapley contribution to attenuation using all 32 subsets:

`phi_j = sum_{S subset of N\{j}} [ |S|! (n-|S|-1)! / n! ] * [ A_T(S) - A_T(S union {j}) ]`

with `n = 5`.

Positive `phi_j` means the modifier attenuates the simple-coefficient advantage on average across coalition orderings. Negative `phi_j` means it increases that advantage on average.

Shapley efficiency requires:

`sum_j phi_j = Delta_T`

for both RMSE and MAE to absolute tolerance `1e-12`.

No modifier is preregistered as the winner. Phase 20 is designed to identify the attribution map on fresh evidence rather than confirm a post-hoc winner.

## Gates

### A20.1 lineage integrity

Require exact hashes for Phase 12, Phase 14, Phase 17 fit, and Phase 19 final. Require the Phase 19 final result to preserve:

- `phase19_pass = true`;
- `phase18_failure_preserved = true`;
- `q90_is_descriptive_only = true`.

### A20.2 complete factorial matched construction

Require exactly 32 unique subsets and domains. Every context must have:

- exact paired-construction integrity;
- exact Phase 12 width identity;
- at least 500 matched transitions.

Require empty and full domain strings to exactly equal the frozen simple and hard contexts.

### A20.3 simple-endpoint RMSE advantage

Require:

`A_RMSE(empty) >= 0.05`.

### A20.4 RMSE endpoint attenuation

Require:

`Delta_RMSE >= 0.08`.

### A20.5 simple-endpoint MAE advantage

Require:

`A_MAE(empty) >= 0.08`.

### A20.6 MAE endpoint attenuation

Require:

`Delta_MAE >= 0.08`.

### A20.7 exact Shapley efficiency

For both RMSE and MAE:

- all five contributions must be finite;
- their sum must equal the corresponding endpoint attenuation to absolute tolerance `1e-12`.

### A20.8 frozen coefficient-context crossover

Using no refit:

At the empty/simple endpoint, require on both RMSE and MAE:

`T(aS) < T(aH)`.

At the full/hard endpoint, require on both RMSE and MAE:

`T(aH) < T(aS)`.

This gate tests context specificity of the two already-frozen coefficients, not whether either coefficient improves absolute state estimation.

### A20.9 static latency degradation remains present at both endpoints

Empty/simple endpoint lateral:

- p95 absolute level-error inflation `>= 1.10`;
- Phase 12 95% coverage delta `<= -0.01`.

Full/hard endpoint lateral:

- p95 absolute level-error inflation `>= 1.10`;
- Phase 12 95% coverage delta `<= -0.05`.

### A20.10 zero adaptation and claim boundary

Require:

- no refit;
- no coefficient clipping;
- all 32 contexts generated exactly from the frozen factor set;
- no context selected or removed after evidence exposure;
- no Phase 12 interval change;
- no Phase 14 change;
- no latency-magnitude change;
- no controller change;
- no post-hoc threshold change;
- q90 remains descriptive only;
- `simulation_only = true`;
- `safety_acceptance = false`;
- `controller_tuning_allowed = false`.

A role PASS requires **all A20.1–A20.10**.

## Progression rule

If development fails, Phase 20 closes at development and all later seeds remain unexposed.

If development passes, freeze the exact scientific SHA and result before transfer. Continue sequentially with unchanged implementation, factors, coefficients, and thresholds. Never expose a later role unless the immediately prior role passed all gates.

## Interpretation boundary

A full PASS would support only:

> In this preregistered matched synthetic factorial study, the loss of distribution-wide residual advantage of the frozen simple-context latency coefficient between the simple and hard contexts was reproducible and could be exactly allocated across the five predefined synthetic context modifiers using a complete 32-context Shapley decomposition.

The resulting Shapley values are attribution within this synthetic generator, not physical causal effects.

A PASS would not mean latency is beneficial. Static latency-induced level error must still worsen at both endpoints.

No physical-flight, real-sensor, full-simulator invariance, certification, controller-improvement, production-readiness, or operational-safety claim is authorized.