# Phase 13C protected validation result — mechanism confirmation

## Verdict

**PASS — protected validation independently confirmed the Phase 13C mechanism.**

The compound-failure phenomenon again replicated on a disjoint protected family partition, all Phase 13C gates passed, and component A — fixed two-frame latency — remained the largest contributor under both preregistered ranking rules.

## Evidence identity

- workflow run: `34009834014`
- artifact: `9982114975`
- artifact digest: `sha256:939f4875bf15a590a404e50ece1933c741da50a013c9ba0a506d47112a5108c6`
- scientific implementation SHA: `de181594cbf451f42424ef61f3139351ad0946cd`
- protected seed: `1313137`
- families: `1441–1464`
- result JSON SHA-256: `2932b4dc6eece2e58325455d51055b6c9721957ee3e388d75c459b7232b44149`
- frozen Phase 12 candidate SHA-256: `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`

The earlier protected workflow run `34009793243` stopped before candidate recovery because a provenance grep expected `A — latency` while the frozen report used `A — fixed two-frame latency`. No evidence was generated and seed `1313137` was not exposed in that run. The corrected run changed only that metadata assertion.

## Protected gates

All Phase 13C gates passed:

- C13.1 construction integrity: **PASS**, 13 / 13
- C13.2 full-compound execution equivalence: **PASS**
- C13.3 fresh failure-phenomenon replication: **PASS**
- C13.4 attribution completeness: **PASS**
- C13.5 zero adaptation: **PASS**

## Full-compound protected replication

Matched control:

- lateral 95% coverage: `0.9666419570`
- altitude 95% coverage: `0.9481097109`
- lateral p95 error: `0.2224616914 m`
- useful availability: `0.9368055556`

Full compound:

- lateral 95% coverage: `0.8413639733`
- altitude 95% coverage: `0.9140103781`
- lateral paired coverage delta: **`-0.1252779837`** (`-12.53 pp`)
- altitude paired coverage delta: `-0.0340993328`
- lateral p95 error: `0.3141743995 m`
- lateral p95 error inflation: `1.4122629270x`
- useful availability: unchanged at `0.9368055556`

## Protected attribution

### Largest singleton — confirmed

**A — fixed two-frame latency**

- singleton lateral coverage loss: `0.1186063751` (`11.86 pp`)
- latency-only lateral coverage: `0.8480355819`
- latency-only lateral p95 error inflation: `1.2750121402x`

### Largest leave-one-out recovery — confirmed

**A — fixed two-frame latency**

- leave-one-out recovery: `0.0830244626` (`8.30 pp`)
- full-minus-latency lateral coverage: `0.9243884359`

Protected singleton losses:

- A latency: `0.1186063751`
- B bias pair: `0.0207561156`
- C lateral wind drift: `0.0177909563`
- D measurement-noise pair: `0.0066716086`
- E innovation response: `0.0`
- F severity response: `0.0`

Protected leave-one-out recoveries:

- A latency: `0.0830244626`
- B bias pair: `0.0185322461`
- C lateral wind drift: `-0.0007412898`
- D measurement-noise pair: `0.0044477391`
- E innovation response: `0.0`
- F severity response: `-0.0007412898`

Interaction excess:

- full lateral loss: `0.1252779837`
- sum singleton losses: `0.1638250556`
- interaction excess: **`-0.0385470719`**

The protected result again does not support a positive six-way super-additive interaction as the primary explanation. Latency remains the dominant synthetic contributor on the hard domain-13 base distribution.

## Evidence boundary

At the time this result is recorded, final seed `1313138` remains unexposed.

A final run is authorized only after a separate final authorization freezes the protected-confirmed mechanism and exact scientific implementation.

## Claim boundary

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`
