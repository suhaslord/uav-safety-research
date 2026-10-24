# Phase 17 development result — Context-Conditional Coefficient Mismatch Audit

## Verdict

**FAIL — the Phase 17 lineage closes at development.**

This is a valid scientific failure, not an execution failure.

The fit stage passed all preregistered eligibility gates and froze an exact context/cohort coefficient candidate. Development then used fresh evidence without refitting. Eight of ten development gates passed. Two preregistered gates failed and are not relaxed.

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`

## Canonical evidence identity

### Fit

- workflow run: `34011621058`
- artifact: `9982637646`
- artifact digest: `sha256:aba8f3e65f3b99e5c4a45c61027d8fff73ab75f68a4efd41183200bb2f31dacd`
- scientific Git SHA: `c497bb6bdfeb7a84160d67ae67fd441d18ca25bc`
- fit seed: `1717170`
- families: `1809–1832`
- fit candidate SHA-256: `2ca52a418f5616e0e83ef84d0c9238ee429260cd4de7a553356b0c1bba44d8e0`

### Development

- workflow run: `34011708070`
- artifact: `9982663704`
- artifact digest: `sha256:9871a38d8d9049b8bade1c1d3c17e7ce1a6a666e2dbbb658a2746f00c34021ae`
- scientific Git SHA: `bb74fe625f1555df651efb0b697a70964c9ec4ce`
- development seed: `1717171`
- families: `1833–1856`
- result JSON SHA-256: `24aeed60003b3111c9d3dd24cee992f8bac539531d38923b9a205a1423e8d029`

Frozen predecessors:

- Phase 12 candidate SHA-256: `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`
- Phase 14 bridge SHA-256: `0443d4e45a1966c77544c5c9965de8caec6e622c79ef8c2ce47aee82a3c95981`
- Phase 14 lateral coefficient: `0.6102677720`

## Fit result

All fit gates passed.

### Simple context

Matched transitions: `1,359`

- control lateral `a = 0.5470675029`
- latency lateral `a = 0.8811661057`
- latency-control shift: `+0.3340986028`
- absolute latency-vs-Phase14 mismatch: `0.2708983337`

### Hard context

Matched transitions: `1,216`

- control lateral `a = 0.0931675212`
- latency lateral `a = 0.5426158628`
- absolute latency-vs-Phase14 mismatch: `0.0676519092`

The fit partition therefore satisfied the preregistered context-heterogeneity pattern and authorized development.

## Development gates

| Gate | Result | Key value |
|---|---|---|
| M17.1 lineage / matched construction | **PASS** | exact paired integrity, width diff `0.0 m` |
| M17.2 coefficient transfer | **FAIL** | hard control altitude transfer error `0.1117093195 > 0.10` |
| M17.3 simple mismatch replication | **PASS** | simple latency `a = 0.8784938249` |
| M17.4 hard proximity replication | **FAIL** | `|0.5018253930 - 0.6102677720| = 0.1084423790 > 0.10` |
| M17.5 context heterogeneity | **PASS** | simple mismatch remains much larger |
| M17.6 simple out-of-sample mismatch penalty | **PASS** | latency-fit / Phase14 q90 = `0.8680048232` |
| M17.7 hard limited coefficient advantage | **PASS** | latency-fit / Phase14 q90 = `0.9978865457` |
| M17.8 simple advantage > hard advantage | **PASS** | improvement gap ≈ `0.12988` |
| M17.9 latency level-error degradation persists | **PASS** | both contexts degrade |
| M17.10 zero adaptation / claim boundary | **PASS** | unchanged |

`phase17_pass = false`

## Main positive finding preserved inside the failed lineage

The strongest preregistered residual-mechanism predictions **did replicate out of sample**.

### Context S — simple

Matched transitions: `1,356`

Fresh development diagnostic coefficients:

- control lateral `a = 0.6176956615`
- latency lateral `a = 0.8784938249`

Frozen fit transfer error:

- control lateral: `0.0706281586`
- latency lateral: `0.0026722808`

Pure latency still worsened lateral level error:

- control coverage: `0.9979108635`
- latency coverage: `0.9700557103`
- coverage delta: **`-0.0278551532`** (`-2.79 pp`)
- p95 error: `0.1660755981 → 0.2453179916 m`
- p95 inflation: **`1.4771465187x`**
- median-error inflation: `3.3546439915x`

But the separately frozen simple-latency coefficient reduced the fresh latency residual:

- Phase 14 q90 residual: `0.1173435729 m`
- Phase 17 control-fit q90 residual: `0.1205924991 m`
- Phase 17 latency-fit q90 residual: **`0.1018547873 m`**
- latency-fit / Phase14: **`0.8680048232`**
- latency-fit / control-fit: **`0.8446195911`**
- relative q90 improvement vs Phase14: **`13.20%`**

So the simple-context coefficient-mismatch penalty is a real out-of-sample predictive effect under this synthetic matched design.

### Context H — hard

Matched transitions: `1,174`

Fresh development diagnostic coefficients:

- control lateral `a = 0.0670690985`
- latency lateral `a = 0.5018253930`

Pure latency again worsened lateral level error:

- control coverage: `0.9467153285`
- latency coverage: `0.8576642336`
- coverage delta: **`-0.0890510949`** (`-8.91 pp`)
- p95 error: `0.2610684055 → 0.3168811695 m`
- p95 inflation: **`1.2137859764x`**

But changing the coefficient had almost no q90 residual advantage:

- Phase 14 q90 residual: `0.2026993890 m`
- Phase 17 latency-fit q90 residual: `0.2022709931 m`
- latency-fit / Phase14: **`0.9978865457`**
- relative q90 improvement: **`0.21%`**

This strongly preserves the preregistered context-conditional residual distinction even though the exact hard-coefficient proximity threshold missed by `0.0084423790`.

## Why Phase 17 still fails

The study was preregistered as an all-gates confirmation, not a selective-success report.

Two conditions did not replicate exactly:

1. **M17.2 coefficient transfer** failed because the hard-context control altitude coefficient moved from fit `0.0686962953` to development `0.1804056148`, an absolute change of `0.1117093195`, just beyond the locked `0.10` transfer tolerance.
2. **M17.4 hard-context Phase14 proximity** failed because the hard latency lateral coefficient was `0.5018253930`, which is `0.1084423790` from the frozen Phase14 coefficient, just beyond the locked `0.10` proximity tolerance.

Neither threshold is widened after seeing the data.

## Scientific interpretation

Phase 17 does **not** support the precise preregistered claim that every coefficient transfers within `0.10` and the hard latency coefficient remains within exactly `0.10` of Phase14.

It does support a narrower repeated observation that should be tested in a new lineage:

> On fresh matched simulation evidence, the coefficient learned on simple-context latency data produced a substantial out-of-sample q90 residual reduction relative to the frozen Phase14 coefficient, while the analogous hard-context coefficient produced almost no residual advantage; static latency-induced level-error degradation remained in both contexts and Phase12 widths stayed identical.

That residual-advantage contrast is more stable than the exact coefficient-location thresholds and should be treated as a new estimand, not used to retroactively pass Phase 17.

## Evidence boundary

Permanently exposed in Phase 17:

- fit seed `1717170`
- development seed `1717171`

Now prohibited in Phase 17:

- transfer seed `1717172`
- protected seed `1717173`
- final seed `1717174`

No rerun, refit, threshold widening, coefficient clipping, context change, or intervention change is allowed in this lineage.

## Claim boundary

Supported claim only:

> In the preregistered simulation-only Phase 17 matched study, the exact all-gates coefficient-transfer hypothesis failed, while the independently preregistered simple-versus-hard out-of-sample residual-advantage contrast replicated without adaptation.

No physical latency causality, physical-flight safety, full-simulator invariance, certification relevance, controller improvement, production readiness, or operational-safety claim is made.