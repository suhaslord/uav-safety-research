# Phase 18 transfer result — Residual Advantage Confirmation

## Verdict

**PASS — all 10 preregistered Phase 18 transfer gates passed without refitting or adaptation.**

The exact Phase 18 development PASS and all frozen upstream identities were reverified before transfer evidence exposure. Phase 17 remains recorded as FAIL.

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`

## Canonical evidence identity

- workflow run: `34011964305`
- artifact: `9982741075`
- artifact digest: `sha256:714eb8e2f6cd6f8c552879003c0aa63f20bede252b5235c5358f2e9533c20de1`
- scientific Git SHA at transfer exposure: `01a96d664e1e2471211bd223fcc732ce70d899ad`
- transfer seed: `1818182`
- families: `1953–1976`
- result JSON SHA-256: `7968f24419476bf9b491b745e4a947011ed9d4bbc548f2e79f3292fcd1e8386e`

Frozen development identity reverified before exposure:

- Phase 18 development scientific SHA: `2c35a7cb2803a996579d45c8494ce77cbd3b8573`
- Phase 18 development result SHA-256: `6b2c6ba8ba390ab5080822fc6906ab5f5c9ef680b4d63ff9ca985c1c8b555c17`

Frozen upstream objects remained unchanged:

- Phase 12 candidate SHA-256: `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`
- Phase 14 bridge SHA-256: `0443d4e45a1966c77544c5c9965de8caec6e622c79ef8c2ce47aee82a3c95981`
- Phase 17 fit candidate SHA-256: `2ca52a418f5616e0e83ef84d0c9238ee429260cd4de7a553356b0c1bba44d8e0`
- failed Phase 17 result SHA-256: `24aeed60003b3111c9d3dd24cee992f8bac539531d38923b9a205a1423e8d029`

## Gates

All passed:

- R18.1 lineage integrity — **PASS**
- R18.2 matched construction / width identity — **PASS**
- R18.3 simple q90 advantage vs Phase 14 — **PASS**
- R18.4 simple q90 advantage vs control fit — **PASS**
- R18.5 hard q90 advantage remains limited — **PASS**
- R18.6 simple-vs-hard q90 improvement gap — **PASS**
- R18.7 independent RMSE confirmation — **PASS**
- R18.8 static latency degradation remains present — **PASS**
- R18.9 cross-statistic context ordering — **PASS**
- R18.10 zero adaptation / claim boundary — **PASS**

`phase18_pass = true`

## Context S — simple

Matched transitions: `1,325`

Static latency effect:

- coverage delta: `-0.0368823939` (`-3.69 pp`)
- p95 error inflation: `1.5071094276x`
- median error inflation: `3.5608333781x`

Frozen-coefficient residual advantage:

- latency-fit / Phase14 q90 = **`0.8570841714`**
- q90 improvement = **`14.2915828641%`**
- latency-fit / frozen control-fit q90 = **`0.8246877933`**
- latency-fit / Phase14 RMSE = **`0.9078284496`**
- RMSE improvement = **`9.2171550438%`**

## Context H — hard

Matched transitions: `1,187`

Static latency effect:

- coverage delta: `-0.0929041697` (`-9.29 pp`)
- p95 error inflation: `1.2229200507x`
- median error inflation: `1.4257198577x`

Frozen-coefficient residual advantage:

- latency-fit / Phase14 q90 = **`0.9788347246`**
- q90 improvement = **`2.1165275423%`**
- latency-fit / Phase14 RMSE = **`1.0003792292`**
- RMSE relative improvement = `-0.0379229196%`

## Cross-context replication

q90 improvement gap:

- simple: `0.1429158286`
- hard: `0.0211652754`
- simple minus hard: **`0.1217505532`** >= locked `0.08`

RMSE improvement gap:

- simple: `0.0921715504`
- hard: `-0.0003792292`
- simple minus hard: **`0.0925507796`** >= locked `0.05`

The simple-vs-hard residual-advantage ordering therefore replicated on a second fresh evidence partition and on both statistics.

## Protected-validation authorization

Because transfer passed all gates, the single next authorized role is:

- protected seed `1818183`
- families `1977–2000`

Before protected exposure:

- exact transfer scientific SHA `01a96d664e1e2471211bd223fcc732ce70d899ad` must be frozen;
- exact transfer result SHA-256 `7968f24419476bf9b491b745e4a947011ed9d4bbc548f2e79f3292fcd1e8386e` must be reverified;
- scientific implementation, coefficients, intervention, and thresholds must remain unchanged.

Final seed `1818184` remains unexposed until protected validation passes.

## Claim boundary

No physical-flight, real-sensor, full-simulator invariance, certification, controller-improvement, production-readiness, or operational-safety claim is made.