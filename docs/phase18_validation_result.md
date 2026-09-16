# Phase 18 protected validation result — Residual Advantage Confirmation

## Verdict

**FAIL — the Phase 18 lineage closes at protected validation.**

Development and transfer both passed all 10 preregistered gates. Protected validation preserved the matched construction, static latency degradation, hard-context limited advantage, and independent RMSE confirmation, but failed two q90 gates. The locked thresholds are not relaxed.

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`

## Canonical evidence identity

- workflow run: `34012030160`
- artifact: `9982760510`
- artifact digest: `sha256:e3f64a1aa4dc2173d3283360db3a65e4cd3fdee650fb72ec6a2891f1b623fd64`
- scientific Git SHA at protected exposure: `feab0da2edcdfea70a365fe2440560cb383308d1`
- protected seed: `1818183`
- families: `1977–2000`
- result JSON SHA-256: `ad96ca1a5119fcd594a84fd72a04f8efcc377ba788383d90dda9ef7eecad4431`

Frozen transfer result reverified before protected exposure:

- transfer run: `34011964305`
- transfer scientific SHA: `01a96d664e1e2471211bd223fcc732ce70d899ad`
- transfer result SHA-256: `7968f24419476bf9b491b745e4a947011ed9d4bbc548f2e79f3292fcd1e8386e`

Frozen upstream objects remained unchanged:

- Phase 12 candidate SHA-256: `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`
- Phase 14 bridge SHA-256: `0443d4e45a1966c77544c5c9965de8caec6e622c79ef8c2ce47aee82a3c95981`
- Phase 17 fit candidate SHA-256: `2ca52a418f5616e0e83ef84d0c9238ee429260cd4de7a553356b0c1bba44d8e0`
- failed Phase 17 result SHA-256: `24aeed60003b3111c9d3dd24cee992f8bac539531d38923b9a205a1423e8d029`

## Protected gates

PASS:

- R18.1 lineage integrity
- R18.2 matched construction / exact Phase 12 width identity
- R18.4 simple q90 advantage vs frozen control fit
- R18.5 hard q90 advantage remains limited
- R18.7 independent RMSE confirmation
- R18.8 static latency degradation remains present
- R18.9 cross-statistic context ordering
- R18.10 zero adaptation / claim boundary

FAIL:

- **R18.3 simple q90 advantage vs Phase 14**
- **R18.6 simple-vs-hard q90 improvement gap**

`phase18_pass = false`

## Context S — simple

Matched transitions: `1,330`

Static latency effect remained strong:

- coverage delta: `-0.0334494774` (`-3.34 pp`)
- p95 error inflation: `1.4136564911x`
- median error inflation: `3.3400067982x`

### q90 residual

- frozen latency-fit / Phase14 ratio: **`0.9096067166`**
- relative improvement: **`9.0393283364%`**
- locked R18.3 requirement: ratio `<= 0.90`
- miss: `0.0096067166` in ratio, or about `0.96` percentage point of required improvement

The same latency coefficient still beat the frozen context-control coefficient:

- latency-fit / control-fit q90: `0.8767486325`
- R18.4: **PASS**

### RMSE residual

- latency-fit / Phase14 RMSE: **`0.9409685634`**
- relative RMSE improvement: **`5.9031436619%`**
- locked simple RMSE requirement: ratio `<= 0.95`
- verdict: **PASS**

## Context H — hard

Matched transitions: `1,197`

Static latency effect:

- coverage delta: `-0.0983965015` (`-9.84 pp`)
- p95 error inflation: `1.2851930863x`
- median error inflation: `1.4250914198x`

### q90 residual

- latency-fit / Phase14 ratio: `0.9850568950`
- relative improvement: `1.4943105037%`
- locked hard range: `[0.90, 1.10]`
- verdict: **PASS**

### RMSE residual

- latency-fit / Phase14 RMSE: `0.9950010064`
- relative improvement: `0.4998993560%`
- locked hard range: `[0.90, 1.10]`
- verdict: **PASS**

## Failed q90 improvement-gap gate

Protected q90 relative improvements:

- simple: `0.0903932834`
- hard: `0.0149431050`
- simple minus hard: **`0.0754501783`**
- locked R18.6 minimum: `0.08`
- shortfall: **`0.0045498217`**

The threshold is not changed after exposure.

## What survived across Phase 18

The distribution-wide RMSE contrast passed on all three exposed Phase 18 partitions:

| Evidence | Simple RMSE improvement | Hard RMSE improvement |
|---|---:|---:|
| development | `7.29%` | `0.15%` |
| transfer | `9.22%` | approximately `0%` |
| protected | `5.90%` | `0.50%` |

The q90 contrast was stronger on development and transfer but did not satisfy the exact protected thresholds.

This does **not** permit retroactively replacing the Phase 18 primary q90 gates with RMSE. Phase 18 remains FAIL.

## Scientific interpretation

The strongest supported conclusion after Phase 18 is narrower than the preregistered all-gates hypothesis:

> Across development, transfer, and protected simulation partitions, the frozen simple-context latency coefficient showed a repeated distribution-wide RMSE residual advantage relative to the frozen Phase14 coefficient while the hard-context advantage remained near zero; however, the stronger preregistered q90 advantage thresholds did not survive protected validation.

A future lineage may test the distribution-wide residual contrast as a new primary estimand using fresh evidence. It must not reuse Phase 18 final evidence or reinterpret this lineage as a pass.

## Evidence boundary

Permanently exposed in Phase 18:

- development seed `1818181`
- transfer seed `1818182`
- protected seed `1818183`

Permanently unexposed and now prohibited in Phase 18:

- final seed `1818184`
- families `2001–2024`

No Phase 18 rerun, threshold widening, coefficient refit, or final exposure is permitted.

## Claim boundary

No physical latency causality, physical-flight safety, real-sensor equivalence, full-simulator invariance, certification relevance, controller improvement, production readiness, or operational-safety claim is made.