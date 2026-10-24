# Phase 16 development result — matched latency level-error / local-dynamics decomposition

## Verdict

**FAIL — Phase 16 closes at development.**

The matched pure-two-frame-lag experiment confirmed two parts of the preregistered mechanism hypothesis and falsified the third:

1. lateral **level error worsened** under pure latency — confirmed in both contexts;
2. lateral **temporal persistence increased strongly** — confirmed in both contexts;
3. lateral **q90 local increments / frozen-surrogate residuals compressed** — **not confirmed**.

Per the preregistered stop rule, Phase 16 transfer, protected, and final evidence remain unexposed.

## Canonical evidence identity

- workflow run: `34011222331`
- artifact: `9982513112`
- artifact digest: `sha256:5149310883ecf1e70a1f34239febc5c0bfc99284464dc13aa507d37119f3015e`
- result JSON SHA-256: `c6b98f60f4da1e2e99a5821c5b2b970a1e3337faf5a9a1c6326ffd651767daf1`
- scientific SHA: `e35dd0f57d73905636b21a321b3fb5115a7dde14`
- development seed: `1616161`
- families: `1713–1736`
- frozen Phase 12 candidate SHA-256: `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`
- frozen Phase 14 bridge SHA-256: `0443d4e45a1966c77544c5c9965de8caec6e622c79ef8c2ce47aee82a3c95981`

The earlier workflow run `34011164261` stopped in pre-evidence tests on the already-known Phase 13C pandas read-only `noise_only` fixture. It never recovered either predecessor candidate and never generated or scored seed `1616161`. The inherited Phase 13C execution remediation was then applied only to the pre-evidence test harness, as documented in `docs/phase16_execution_amendment_01.md`.

## Frozen intervention

Phase 16 used only Phase 13C component A:

- exact two-frame point-estimate lag;
- no innovation response;
- no severity response;
- no bias;
- no wind/drift;
- no measurement noise;
- no Phase 12 recalibration;
- no controller change.

## Gates

Passed:

- L16.1 paired construction integrity
- L16.2 Phase 12 width identity under pure lag
- L16.3 lateral level-error degradation
- L16.4 lateral persistence increase
- L16.9 no refit / no adaptation
- L16.10 claim boundary

Failed:

- L16.5 lateral raw-increment compression
- L16.6 lateral frozen-surrogate residual compression
- L16.7 lateral q90 frontier compression
- L16.8 context-stable divergence

`phase16_pass = false`

## Construction and width identity

Both matched contexts passed all pairing checks:

- identical row counts;
- identical pair IDs;
- identical truth-visible masks;
- identical useful-availability masks;
- identical lateral truth;
- identical altitude truth.

Most importantly, the maximum matched Phase 12 95% half-width difference was exactly:

- lateral: `0.0 m`
- altitude: `0.0 m`

in **both** contexts.

Therefore the Phase 16 coverage changes are attributable within the synthetic paired design to the stale point estimate rather than a widened or narrowed Phase 12 interval.

## Context S — simple base

Base:

`small_scale+temporal_dropout`

Matched temporal transitions: `1,356`.

### Lateral level error

Control:

- 95% coverage: `0.9937150838`
- median absolute error: `0.0255448461 m`
- p95 absolute error: `0.1761554764 m`

Pure two-frame latency:

- 95% coverage: `0.9650837989`
- median absolute error: `0.0828407115 m`
- p95 absolute error: `0.2452268294 m`

Paired effect:

- coverage delta: **`-0.0286312849`** = `-2.86 pp`
- p95 error inflation: **`1.3921044885x`**
- median error inflation: **`3.2429520635x`**

L16.3 simple-context level-error requirements therefore passed.

### Lateral persistence

Control:

- diagnostic no-intercept `a = 0.5648441738`
- adjacent signed-error correlation `0.5189760705`

Latency:

- diagnostic `a = 0.8432532241`
- adjacent correlation `0.8027605740`

Increase:

- `a`: **`+0.2784090504`**
- correlation: **`+0.2837845035`**

This strongly passes the preregistered persistence gate.

### Local increment / residual result

Raw q90 one-frame increment:

- control `0.1064075606 m`
- latency `0.1043778768 m`
- latency/control ratio: **`0.9809253802`**

This is a small reduction, but not the preregistered `<=0.90` compression.

Frozen Phase 14 q90 residual using `a_x = 0.6102677720`:

- control `0.0997454334 m`
- latency `0.1158750916 m`
- latency/control ratio: **`1.1617082375`**

So the frozen-surrogate residual **increased by ~16.2%**, directly falsifying the proposed residual-compression mechanism in this context.

The corresponding q90 residual-based half-width ratio is identically `1.1617082375x` because the same frozen denominator `1-|a_x|` is used.

## Context H — hard Phase 13C base

Base:

`edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout`

Matched temporal transitions: `1,135`.

### Lateral level error

Control:

- 95% coverage: `0.9493019838`
- median absolute error: `0.0718489927 m`
- p95 absolute error: `0.2637561868 m`

Pure two-frame latency:

- 95% coverage: `0.8523144747`
- median absolute error: `0.1082744111 m`
- p95 absolute error: `0.3404977123 m`

Paired effect:

- coverage delta: **`-0.0969875092`** = `-9.70 pp`
- p95 error inflation: **`1.2909563052x`**
- median error inflation: **`1.5069718733x`**

This independently reproduces the strong hard-domain level-error degradation seen in Phase 13C.

### Lateral persistence

Control:

- diagnostic `a = 0.0581003832`
- adjacent correlation `0.0493843660`

Latency:

- diagnostic `a = 0.5816428797`
- adjacent correlation `0.5207744159`

Increase:

- `a`: **`+0.5235424965`**
- correlation: **`+0.4713900499`**

Again, the persistence increase is large and passes comfortably.

### Local increment / residual result

Raw q90 increment:

- control `0.2336533521 m`
- latency `0.2189025744 m`
- ratio: **`0.9368689657`**

The raw increment decreased by about 6.3%, but again not enough for the preregistered `<=0.90` gate.

Frozen Phase 14 q90 residual:

- control `0.1962995834 m`
- latency `0.2004264952 m`
- ratio: **`1.0210235378`**

The residual is essentially flat/slightly worse rather than compressed.

## Scientific interpretation

Phase 16 resolves an ambiguity left by Phase 15.

The matched evidence supports this narrower statement:

> In both tested simulation contexts, a pure two-frame stale estimate increased lateral absolute/level error and substantially increased adjacent error persistence while leaving Phase 12 interval widths exactly unchanged.

But the stronger post-hoc Phase 15 idea — that higher persistence necessarily makes the q90 one-step residual smaller — is false under the frozen Phase 14 coefficient.

Why can persistence increase while the frozen residual does not shrink?

The latency error process becomes more persistent, but its effective one-step coefficient moves substantially away from the frozen Phase 14 coefficient. In the simple context, for example, the latency diagnostic coefficient is `0.8433` while the frozen coefficient is only `0.6103`. A model with the wrong propagation coefficient can therefore have a larger residual even when the underlying series is more persistent.

This coefficient-mismatch explanation is **post-hoc** and must be tested in a new lineage before being treated as a replicated mechanism.

## Evidence boundary

Permanently exposed:

- Phase 16 development seed `1616161`

Remain unexposed and prohibited in this Phase 16 lineage:

- transfer `1616162`
- protected `1616163`
- final `1616164`

No threshold, coefficient, intervention, base context, or metric will be changed to make Phase 16 pass.

`simulation_only = true`
`safety_acceptance = false`
`controller_tuning_allowed = false`

No physical latency causality, physical-flight safety, full-simulator invariance, certification relevance, controller improvement, production readiness, or operational reliability claim is made.
