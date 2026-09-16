# Phase 18 development result — Residual Advantage Confirmation

## Verdict

**PASS — all 10 preregistered Phase 18 development gates passed without refitting or adaptation.**

This result confirms the narrower residual-advantage contrast that survived the failed Phase 17 all-gates study. Phase 17 remains recorded as FAIL and is not reinterpreted.

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`

## Canonical evidence identity

- workflow run: `34011884494`
- artifact: `9982715671`
- artifact digest: `sha256:c1501fe1bbf9048029db7d11c67774d8cefb9ba8c31c8b205fc85ed7f202e4b6`
- scientific Git SHA at development exposure: `2c35a7cb2803a996579d45c8494ce77cbd3b8573`
- development seed: `1818181`
- families: `1929–1952`
- result JSON SHA-256: `6b2c6ba8ba390ab5080822fc6906ab5f5c9ef680b4d63ff9ca985c1c8b555c17`

Frozen upstream objects:

- Phase 12 candidate SHA-256: `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`
- Phase 14 bridge SHA-256: `0443d4e45a1966c77544c5c9965de8caec6e622c79ef8c2ce47aee82a3c95981`
- Phase 17 fit candidate SHA-256: `2ca52a418f5616e0e83ef84d0c9238ee429260cd4de7a553356b0c1bba44d8e0`
- exact failed Phase 17 result SHA-256: `24aeed60003b3111c9d3dd24cee992f8bac539531d38923b9a205a1423e8d029`

The workflow explicitly reverified that the frozen Phase 17 result had `phase17_pass = false` before Phase 18 evidence was generated.

## Development gates

All passed:

- R18.1 lineage integrity — **PASS**
- R18.2 matched construction / exact Phase 12 width identity — **PASS**
- R18.3 simple q90 advantage vs Phase 14 — **PASS**
- R18.4 simple q90 advantage vs frozen control fit — **PASS**
- R18.5 hard q90 advantage remains limited — **PASS**
- R18.6 simple-vs-hard q90 improvement gap — **PASS**
- R18.7 independent RMSE confirmation — **PASS**
- R18.8 static latency degradation remains present — **PASS**
- R18.9 cross-statistic context ordering — **PASS**
- R18.10 zero adaptation / claim boundary — **PASS**

`phase18_pass = true`

## Context S — simple

Base domain:

`small_scale+temporal_dropout`

Matched transitions: `1,347`

Pure two-frame latency still worsened lateral level error:

- coverage delta: **`-0.0292887029`** (`-2.93 pp`)
- p95 error inflation: **`1.3862891337x`**
- median error inflation: `3.5289885107x`

Frozen-coefficient residuals on fresh latency transitions:

### q90 absolute residual

- Phase 14 coefficient: `0.1097521726 m`
- frozen Phase 17 control coefficient: `0.1158896300 m`
- frozen Phase 17 latency coefficient: **`0.0940057297 m`**

Ratios:

- latency-fit / Phase14 = **`0.8565272779`**
- latency-fit / control-fit = **`0.8111660180`**
- q90 improvement vs Phase14 = **`14.3472722142%`**

### signed residual RMSE

- Phase14: `0.0723083034 m`
- frozen latency coefficient: **`0.0670360253 m`**
- latency-fit / Phase14 = **`0.9270861325`**
- RMSE improvement = **`7.2913867456%`**

Descriptive-only fresh diagnostic lateral coefficients:

- control `a = 0.5379279119`
- latency `a = 0.8562864082`

These diagnostics were not used as Phase 18 gate inputs.

## Context H — hard

Base domain:

`edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout`

Matched transitions: `1,190`

Pure two-frame latency again worsened lateral level error:

- coverage delta: **`-0.0998563218`** (`-9.99 pp`)
- p95 error inflation: **`1.2217630097x`**
- median error inflation: `1.3416284594x`

Frozen-coefficient residuals:

### q90 absolute residual

- Phase14 coefficient: `0.2035384579 m`
- frozen Phase17 latency coefficient: `0.2012872356 m`
- latency-fit / Phase14 = **`0.9889395728`**
- q90 improvement = **`1.1060427220%`**

### signed residual RMSE

- Phase14: `0.1286098056 m`
- frozen Phase17 latency coefficient: `0.1284128465 m`
- latency-fit / Phase14 = **`0.9984685527`**
- RMSE improvement = **`0.1531447252%`**

Descriptive-only fresh diagnostic lateral coefficients:

- control `a = 0.1070317018`
- latency `a = 0.5538980170`

Again, these diagnostics were not gate inputs.

## Cross-context confirmation

The residual-advantage contrast replicated on both independently preregistered statistics.

### q90 improvement gap

- simple improvement: `0.1434727221`
- hard improvement: `0.0110604272`
- simple minus hard: **`0.1324122949`**
- locked minimum: `0.08`

### RMSE improvement gap

- simple improvement: `0.0729138675`
- hard improvement: `0.0015314473`
- simple minus hard: **`0.0713824202`**
- locked minimum: `0.05`

Thus the effect is not confined to a single upper-tail quantile.

## What this result means

Supported simulation-only statement:

> On fresh matched synthetic evidence, the frozen simple-context latency coefficient again reduced out-of-sample one-step lateral residuals materially relative to the frozen Phase14 coefficient, while the analogous hard-context coefficient produced little advantage. The contrast appeared in both q90 and RMSE, while pure latency continued to worsen static lateral level error and Phase12 interval widths remained unchanged.

This is a predictive-mechanism confirmation, not a physical latency causal claim and not a safety proof.

## Transfer authorization

Because all Phase 18 development gates passed, the following **single next evidence role** is now authorized:

- transfer seed `1818182`
- families `1953–1976`

Before transfer exposure:

- the exact Phase 18 development scientific SHA `2c35a7cb2803a996579d45c8494ce77cbd3b8573` must be frozen;
- the exact development result SHA-256 above must be reverified;
- scientific implementation and thresholds must remain unchanged;
- no coefficient may be refit.

Protected `1818183` and final `1818184` remain unexposed until sequential progression gates authorize them.

## Claim boundary

No physical-flight, real-sensor, full-simulator invariance, certification, controller-improvement, production-readiness, or operational-safety claim is made.