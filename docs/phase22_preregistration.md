# Phase 22 preregistration — Frozen Additive Context Transfer

## Status

**PREREGISTERED BEFORE ANY PHASE 22 EVIDENCE.**

Phase 21 is closed as a final-holdout PASS. Phase 20 is closed as a final-holdout PASS. Phase 18 remains an immutable protected-validation FAIL.

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`

## Motivation

Phase 21 established on four fresh complete 32-cell synthetic factorial roles that the context dependence of the frozen Phase 17 simple-context latency coefficient was predominantly first-order under an exact Walsh–Hadamard decomposition. First-order variance share exceeded 70% on both RMSE and MAE in development, transfer, protected validation, and final holdout.

That result is descriptive. It does not yet show that a first-order model frozen on one fresh context cube can predict the complete response surface on new cubes without refitting.

Phase 22 asks that predictive question.

## Scientific question

> Can an intercept-plus-five-main-effect model, frozen from one fresh complete 32-cell synthetic factorial fit cube, predict the context-specific distribution-wide residual advantage of the exact frozen Phase 17 simple-context latency coefficient on wholly fresh development, transfer, protected, and final context cubes without refitting?

This is a simulation-only predictive-transfer study of a frozen synthetic response surface. It is not a physical causal model.

## Frozen predecessor objects

Exact Phase 12 candidate SHA-256:

`e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`

Exact Phase 14 bridge SHA-256:

`0443d4e45a1966c77544c5c9965de8caec6e622c79ef8c2ce47aee82a3c95981`

Exact Phase 17 fit candidate SHA-256:

`2ca52a418f5616e0e83ef84d0c9238ee429260cd4de7a553356b0c1bba44d8e0`

Exact Phase 20 final result SHA-256:

`f2a0cf4e1cf0765c3194025eb29072f9663f27e3cdd13b0594cde4643f33934e`

Exact Phase 21 final result SHA-256:

`bc85a746cf1b770fb4119feb3979789975ed5201065d94de47c6dcc3a051d9ee`

Phase 22 must verify `phase21_pass = true`, `phase20_final_pass_preserved = true`, `phase19_final_pass_preserved_via_phase20 = true`, `phase18_failure_preserved_via_phase20 = true`, `q90_is_descriptive_only = true`, `no_refit = true`, and `zero_adaptation = true` in the exact Phase 21 final object before exposing evidence.

## Frozen intervention and context cube

The intervention is unchanged pure latency only:

- exact two-frame lag;
- no innovation response;
- no severity response;
- no bias;
- no wind;
- no measurement-noise injection;
- no Phase 12 recalibration;
- no controller change.

Shared base context:

`small_scale+temporal_dropout`

Five factors in frozen canonical order:

1. `edge`
2. `oblique`
3. `dim`
4. `blur_noise`
5. `low_contrast`

Every Phase 22 role evaluates the same complete `2^5 = 32` context power set used by Phases 20–21.

For every context, paired control and pure-latency copies must preserve row identity, truth, truth-visible mask, useful availability, severity, anchor innovation, and Phase 12 95% interval widths. At least 500 matched transitions are required in every context.

## Residual advantage

For statistic `T ∈ {RMSE, MAE}` and context subset `M`, define exactly as before:

`A_T(M) = 1 - T(residual using frozen Phase 17 simple latency coefficient) / T(residual using frozen Phase 14 coefficient)`.

Positive advantage favors the frozen Phase 17 simple-context coefficient for local one-step residual prediction. It does not mean latency improves absolute state estimation.

q90 absolute residual remains descriptive only and is not a Phase 22 gate.

## Additive model

Use effect coding for each factor `j`:

- `x_j(M) = +1` when factor `j` is present;
- `x_j(M) = -1` when factor `j` is absent.

On the **fit role only**, compute the exact Walsh grand mean and the five first-order Walsh coefficients for each statistic:

`b0_T = mean_M A_T(M)`

`b_j,T = mean_M [A_T(M) * x_j(M)]`

Freeze only these six values per statistic. All interaction coefficients are deliberately discarded.

For every later context subset:

`Ahat_T(M) = b0_T + sum_j b_j,T * x_j(M)`.

No coefficient may be changed, clipped, shrunk, recalibrated, or refitted after the fit artifact is created.

## Fresh evidence partitions

| Role | Seed | Families |
|---|---:|---|
| fit | `2222220` | `2313–2336` |
| development | `2222221` | `2337–2360` |
| transfer | `2222222` | `2361–2384` |
| protected | `2222223` | `2385–2408` |
| final | `2222224` | `2409–2432` |

Each role uses 24 fresh families split evenly across inherited `bootstrap5`, `gap3`, `gap7`, and `gap12` strata.

Only the fit role is authorized initially. Development is prohibited unless the fit artifact passes every fit gate and is frozen by exact SHA-256. Transfer is prohibited unless development passes. Protected is prohibited unless transfer passes. Final is prohibited unless protected passes.

## Fit gates

### F22.1 lineage integrity

Require exact Phase 12, Phase 14, Phase 17, Phase 20 final, and Phase 21 final identities and all required predecessor PASS/failure-boundary fields.

### F22.2 complete matched factorial construction

Require exactly 32 unique subsets/domains, exact paired integrity and Phase 12 width identity in every cell, at least 500 matched transitions per cell, and exact simple/hard endpoint domain strings.

### F22.3 fit endpoint phenomenon remains present

Require on the fit cube:

- RMSE simple advantage `>= 0.05`;
- RMSE simple→hard attenuation `>= 0.08`;
- MAE simple advantage `>= 0.08`;
- MAE simple→hard attenuation `>= 0.08`.

### F22.4 first-order fit structure

Require first-order centered variance share `>= 0.70` for both RMSE and MAE.

### F22.5 balanced factor direction

Require all five first-order coefficients to be strictly negative for both RMSE and MAE.

### F22.6 finite frozen candidate

Require finite intercept and all five finite first-order coefficients for each statistic and exact factor order.

### F22.7 static latency degradation persists at fit endpoints

Simple endpoint:

- lateral p95 absolute level-error inflation `>= 1.10`;
- Phase 12 95% coverage delta `<= -0.01`.

Hard endpoint:

- lateral p95 absolute level-error inflation `>= 1.10`;
- Phase 12 95% coverage delta `<= -0.05`.

### F22.8 zero adaptation and claim boundary

Require no controller change, no Phase 12 change, no coefficient clipping, no interaction term retained in the candidate, and no post-hoc threshold change.

The fit candidate is eligible only if all F22 gates pass.

## Confirmation metrics

For every post-fit role and statistic, compare the frozen predictions `Ahat_T(M)` with fresh observed `A_T(M)` over all 32 cells.

### Cellwise coefficient of determination

`R2_T = 1 - sum_M (A_T(M)-Ahat_T(M))^2 / sum_M (A_T(M)-mean(A_T))^2`

### Cellwise absolute prediction error

`MAEpred_T = mean_M |A_T(M)-Ahat_T(M)|`

This is prediction error in advantage units, not the residual MAE statistic itself.

### Stable-sign classification

For cells with fresh observed `|A_T(M)| >= 0.02`, compare the sign of observed and predicted advantage. At least 10 eligible cells are required for each statistic.

### Endpoint attenuation error

For each statistic:

`D_T = A_T(empty) - A_T(full)`

`Dhat_T = Ahat_T(empty) - Ahat_T(full)`

Evaluate `|D_T - Dhat_T|`.

## Confirmation gates

### P22.1 lineage and frozen candidate integrity

Require exact predecessor hashes and exact fit-candidate SHA-256. Require fit eligibility to be true. No refit is permitted.

### P22.2 complete fresh matched construction

Require the exact complete 32-cell cube, paired integrity, Phase 12 width identity, at least 500 matched transitions per context, and exact endpoint domain identities.

### P22.3 RMSE cellwise predictive transfer

Require fresh `R2_RMSE >= 0.65`.

### P22.4 RMSE absolute prediction error

Require fresh `MAEpred_RMSE <= 0.025`.

### P22.5 MAE cellwise predictive transfer

Require fresh `R2_MAE >= 0.65`.

### P22.6 MAE absolute prediction error

Require fresh `MAEpred_MAE <= 0.025`.

### P22.7 stable-sign transfer

For both RMSE and MAE:

- at least 10 cells must have fresh `|A_T(M)| >= 0.02`;
- sign agreement on eligible cells must be `>= 0.90`.

### P22.8 endpoint phenomenon and attenuation transfer

Require fresh endpoint phenomenon to remain present:

- RMSE simple advantage `>= 0.05`;
- RMSE observed attenuation `>= 0.08`;
- MAE simple advantage `>= 0.08`;
- MAE observed attenuation `>= 0.08`.

Also require absolute predicted-vs-observed attenuation error `<= 0.07` for both statistics.

### P22.9 static latency degradation persists at fresh endpoints

Simple endpoint:

- lateral p95 absolute level-error inflation `>= 1.10`;
- Phase 12 95% coverage delta `<= -0.01`.

Hard endpoint:

- lateral p95 absolute level-error inflation `>= 1.10`;
- Phase 12 95% coverage delta `<= -0.05`.

### P22.10 zero adaptation and claim boundary

Require no refit, no interaction term activation, no threshold change, no controller change, no Phase 12 recalibration, and all safety boundary flags unchanged.

A stage passes only if all P22 gates pass.

## Prior-data boundary

The already-seen Phase 21 development/transfer/protected/final cubes may motivate this model class and conservative thresholds only. They are not Phase 22 fit, development, transfer, protected, or final evidence and cannot satisfy a Phase 22 gate.

## Stop rules

- If fit eligibility fails, Phase 22 stops permanently and development remains unexposed.
- If development fails, transfer/protected/final remain unexposed.
- If transfer fails, protected/final remain unexposed.
- If protected fails, final remains unexposed.
- Any failed role remains failed; thresholds or model form cannot be changed inside Phase 22.
- Every role may be exposed exactly once.

## Claim boundary

Phase 22 may support only a statement about predictive transfer of a frozen additive approximation across fresh synthetic context cubes.

It cannot support claims of:

- physical-flight safety;
- physical latency causality;
- physical modifier causality;
- real-sensor equivalence;
- full-simulator invariance;
- certification relevance;
- controller improvement;
- production readiness;
- operational reliability or safety.
