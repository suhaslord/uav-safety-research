# Phase 21 preregistration — Orthogonal Context Spectrum

## Status

**PREREGISTERED BEFORE PHASE 21 DEVELOPMENT EVIDENCE.**

Phase 20 is closed as a final-holdout PASS. Phase 18 remains an immutable protected-validation FAIL through the preserved Phase 19/20 lineage. Phase 21 does not refit any coefficient, does not retry q90, and does not name a winning modifier.

A non-scientific maintenance repair inherited by the Phase 21 branch only adds `.copy()` to two historical Phase 13C Pandas/NumPy slices so the existing deterministic noise fixture remains writable under the current dependency stack. No scientific constant, seed, transform, threshold, candidate, or evidence artifact is changed by that repair.

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`

## Motivation

Phase 20 evaluated the exact `2^5 = 32` synthetic context cube separating the frozen simple and hard contexts. It established reproducible endpoint attenuation and exact Shapley allocation across five predefined modifiers, while correctly declining to claim a universally dominant factor.

Shapley attribution allocates an endpoint difference but does not answer whether the complete response surface is primarily additive/first-order or interaction-driven.

Post-Phase-20 analysis of already-seen Phase 20 evidence motivated a fresh preregistered test of that structural question. Those already-seen analyses are not Phase 21 evidence.

## Scientific question

> On fresh complete 32-context matched synthetic evidence, is the distribution-wide residual-advantage surface of the exact frozen simple-context latency coefficient predominantly explained by first-order modifier effects under an orthogonal Walsh–Hadamard decomposition, while all five first-order effects point toward attenuation and static latency-induced level-error degradation remains present?

This is a simulation-only structural decomposition of a synthetic context surface.

## Frozen predecessor identities

Exact Phase 12 candidate SHA-256:

`e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`

Exact Phase 14 bridge SHA-256:

`0443d4e45a1966c77544c5c9965de8caec6e622c79ef8c2ce47aee82a3c95981`

Exact Phase 17 fit candidate SHA-256:

`2ca52a418f5616e0e83ef84d0c9238ee429260cd4de7a553356b0c1bba44d8e0`

Exact Phase 20 final result SHA-256:

`f2a0cf4e1cf0765c3194025eb29072f9663f27e3cdd13b0594cde4643f33934e`

Phase 21 must verify that the Phase 20 final result remains:

- `phase20_pass = true`;
- `phase19_final_pass_preserved = true`;
- `phase18_failure_preserved_via_phase19 = true`;
- `q90_is_descriptive_only = true`;
- `no_refit = true`;
- `zero_adaptation = true`.

No coefficient is fitted in Phase 21.

## Frozen intervention and coefficient

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

The primary response surface uses the exact frozen Phase 17 simple-context latency coefficient `aS` relative to the exact frozen Phase 14 coefficient `a14`.

## Frozen five-factor context cube

Shared base:

`small_scale+temporal_dropout`

Factors, in exact canonical order:

1. `edge`
2. `oblique`
3. `dim`
4. `blur_noise`
5. `low_contrast`

Exactly all 32 subsets are evaluated. Context construction, token ordering, paired control/latency construction, analysis box, width-identity tolerance, and minimum matched-transition count are inherited unchanged from Phase 20.

Each context must have at least 500 matched adjacent transitions.

## Fresh evidence partitions

| Role | Seed | Families |
|---|---:|---|
| development | `2121211` | `2217–2240` |
| transfer | `2121212` | `2241–2264` |
| protected | `2121213` | `2265–2288` |
| final | `2121214` | `2289–2312` |

Each role uses exactly 24 fresh families split evenly across the inherited `bootstrap5`, `gap3`, `gap7`, and `gap12` strata.

Only development is authorized initially.

## Response surfaces

For statistic `T ∈ {RMSE, MAE}`, on every subset `S` define the frozen simple-coefficient advantage exactly as in Phase 20:

`A_T(S) = 1 - T(residual using aS on context S) / T(residual using a14 on context S)`.

q90 remains descriptive only.

Endpoint attenuation is retained unchanged:

`Delta_T = A_T(empty) - A_T(full)`.

## Orthogonal Walsh–Hadamard decomposition

For each factor `j`, encode:

- `x_j(S) = +1` when modifier `j` is present;
- `x_j(S) = -1` when modifier `j` is absent.

For every subset of factors `U`, define the orthogonal coefficient:

`beta_U = (1 / 32) * sum_S A_T(S) * product_{j in U} x_j(S)`.

`beta_empty` is the grand mean.

For nonempty `U`, orthogonality gives the centered surface variance decomposition:

`V_T = sum_{U != empty} beta_U^2`.

Direct population variance across the 32 equally weighted cells must equal `V_T` by Parseval identity.

Define order-specific variance mass:

`V_{T,k} = sum_{|U|=k} beta_U^2`, for `k = 1..5`.

Define first-order share:

`F_T = V_{T,1} / V_T`.

Define interaction share:

`I_T = 1 - F_T`.

A negative first-order coefficient means that adding that modifier decreases the frozen simple-coefficient advantage on average across the balanced factorial cube, i.e. it points toward attenuation.

## Locked gates

### O21.1 lineage integrity

Require exact hashes for Phase 12, Phase 14, Phase 17 fit, and Phase 20 final. Require all preserved Phase 20 lineage flags listed above.

### O21.2 complete factorial matched construction

Require exactly 32 unique subsets and domains. Every context must have:

- exact paired construction integrity;
- exact Phase 12 95% width identity to tolerance `1e-12`;
- at least 500 matched transitions.

Require exact empty/simple and full/hard endpoint domain identities.

### O21.3 endpoint attenuation remains present

Inherited from Phase 20:

- `A_RMSE(empty) >= 0.05`;
- `Delta_RMSE >= 0.08`;
- `A_MAE(empty) >= 0.08`;
- `Delta_MAE >= 0.08`.

### O21.4 exact orthogonal closure

For both RMSE and MAE:

- all 32 Walsh coefficients finite;
- direct centered population variance finite and positive;
- `abs(sum_{U != empty} beta_U^2 - direct_variance) <= 1e-12`;
- order shares `k=1..5` sum to 1 within `1e-12`.

### O21.5 RMSE first-order dominance

Require:

`F_RMSE >= 0.70`.

### O21.6 MAE first-order dominance

Require:

`F_MAE >= 0.70`.

### O21.7 all five RMSE first-order effects point toward attenuation

For every predefined modifier `j`:

`beta_{j,RMSE} < 0`.

No factor ranking or minimum individual magnitude is required.

### O21.8 all five MAE first-order effects point toward attenuation

For every predefined modifier `j`:

`beta_{j,MAE} < 0`.

No factor ranking or minimum individual magnitude is required.

### O21.9 static latency degradation remains present at both endpoints

Inherited unchanged from Phase 20.

Empty/simple endpoint lateral:

- p95 absolute level-error inflation `>= 1.10`;
- Phase 12 95% coverage delta `<= -0.01`.

Full/hard endpoint lateral:

- p95 absolute level-error inflation `>= 1.10`;
- Phase 12 95% coverage delta `<= -0.05`.

### O21.10 zero adaptation and claim boundary

Require:

- no refit;
- no coefficient clipping;
- no Phase 12 interval change;
- no Phase 14 change;
- no factor-set change;
- no context-construction change;
- no latency-magnitude change;
- no controller change;
- no post-hoc threshold change;
- q90 descriptive only;
- `simulation_only = true`;
- `safety_acceptance = false`;
- `controller_tuning_allowed = false`.

A stage passes only if **all O21.1–O21.10 pass**.

## Sequential progression

If development fails, Phase 21 closes at development and seeds `2121212`, `2121213`, and `2121214` remain unexposed.

If development passes, freeze the exact scientific SHA and result before transfer. Proceed sequentially with no scientific implementation or threshold changes. A later role may be exposed only after the immediately previous role passes all gates.

## Interpretation boundary

A full PASS would support only:

> Across fresh complete matched synthetic factorial evidence, the context dependence of the frozen simple-context latency coefficient's distribution-wide one-step lateral residual advantage was predominantly first-order under an exact orthogonal five-factor decomposition, with each predefined modifier's balanced first-order effect pointing toward attenuation on both RMSE and MAE, while latency-induced absolute level-error degradation persisted.

It would not mean latency is beneficial, would not establish physical causal effects of the modifiers, and would not establish physical UAV safety.

No physical-flight safety, physical latency causality, real-sensor equivalence, full-simulator invariance, certification relevance, controller improvement, production readiness, or operational-safety claim is authorized.
