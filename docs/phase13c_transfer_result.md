# Phase 13C transfer result — mechanism confirmation

## Verdict

**PASS — the Phase 13C development mechanism transferred to fresh evidence.**

The preregistered compound-failure phenomenon replicated, attribution remained complete, zero adaptation remained true, and component A — fixed two-frame latency — was again the largest contributor under both frozen ranking rules.

## Evidence identity

- workflow run: `34009722199`
- artifact: `9982081924`
- artifact digest: `sha256:1eaf792f28d3b4f96e5e8f38eeb609199f821b9c005298881ee7ee0f99e1a12c`
- scientific implementation SHA: `de181594cbf451f42424ef61f3139351ad0946cd`
- transfer seed: `1313136`
- families: `1417–1440`
- result JSON SHA-256: `718f6ade7f6dfecd05c577ac632e02cab5eb1d83d51078a27996a43b5363d23c`
- frozen Phase 12 candidate SHA-256: `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`

## Transfer gates

All Phase 13C gates passed:

- C13.1 construction integrity: **PASS**, 13 / 13
- C13.2 full-compound execution equivalence: **PASS**
- C13.3 fresh failure-phenomenon replication: **PASS**
- C13.4 attribution completeness: **PASS**
- C13.5 zero adaptation: **PASS**

## Full-compound replication

Matched control:

- lateral 95% coverage: `0.9408759124`
- altitude 95% coverage: `0.9401459854`
- lateral p95 error: `0.2325164774 m`
- useful availability: `0.9513888889`

Full compound:

- lateral 95% coverage: `0.8379562044`
- altitude 95% coverage: `0.9007299270`
- lateral paired coverage delta: **`-0.1029197080`** (`-10.29 pp`)
- altitude paired coverage delta: `-0.0394160584`
- lateral p95 error: `0.3183781498 m`
- lateral p95 error inflation: `1.3692713449x`
- useful availability: unchanged at `0.9513888889`

The full compound again exceeded the locked eight-point paired-loss threshold while remaining above the catastrophic 0.80 floor.

## Attribution confirmation

### Largest singleton loss — confirmed

**A — fixed two-frame latency**

- transfer singleton lateral loss: `0.0810218978` (`8.10 pp`)
- latency-only lateral coverage: `0.8598540146`
- latency-only lateral p95 error inflation: `1.2837942665x`

### Largest leave-one-out recovery — confirmed

**A — fixed two-frame latency**

- transfer leave-one-out recovery: `0.0766423358` (`7.66 pp`)
- full-minus-latency lateral coverage: `0.9145985401`

### Transfer singleton losses

- A latency: `0.0810218978`
- B bias pair: `0.0116788321`
- C lateral wind drift: `0.0094890511`
- D measurement-noise pair: `0.0072992701`
- E innovation response: `0.0`
- F severity response: `-0.0007299270`

### Transfer leave-one-out recoveries

- A latency: `0.0766423358`
- B bias pair: `0.0138686131`
- C lateral wind drift: `-0.0021897810`
- D measurement-noise pair: `-0.0029197080`
- E innovation response: `0.0`
- F severity response: `-0.0014598540`

### Interaction excess

- full loss: `0.1029197080`
- sum singleton losses: `0.1087591241`
- interaction excess: **`-0.0058394161`** (`-0.58 pp`)

The transfer result therefore supports the same narrow simulation-only interpretation as development: fixed two-frame latency is the dominant synthetic contributor on this hard base domain, while the aggregate loss is not primarily a positive super-additive six-component interaction.

## Evidence boundary

Protected seed `1313137` and final seed `1313138` remain unexposed at the time this result is recorded.

No scientific implementation changed between development and transfer.

## Claim boundary

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`
