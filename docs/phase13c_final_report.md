# Phase 13C final report — Thirteen-Contrast Compound Interaction Attribution

## Final verdict

**PASS — the preregistered synthetic mechanism replicated across development, transfer, protected validation, and final unseen evidence with zero model adaptation.**

Phase 13C was created after the Phase 13A and Phase 13B failures to answer a narrower mechanism question: which constituent of the frozen thirteenth compound stress is primarily responsible for the lateral uncertainty-coverage failure on the exact hard domain-13 base distribution?

Across all four disjoint Phase 13C evidence stages, the answer was the same under both preregistered attribution rankings:

> **Component A — fixed two-frame latency was the dominant synthetic contributor.**

This does not repair the failed Phase 13A or Phase 13B lineages. It explains the synthetic failure mechanism more precisely.

## Frozen scientific identity

- scientific implementation SHA used for every Phase 13C evidence stage: `de181594cbf451f42424ef61f3139351ad0946cd`
- frozen Phase 12 scientific SHA: `8d0617a83d699cd14eae6194ce3a86a5c034dfbc`
- frozen Phase 12 candidate SHA-256: `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`
- hard base domain: `edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout`
- contrast count: exactly `13`
- model adaptation: none
- recalibration: none
- controller tuning: none

## Evidence lineage

| Stage | Seed | Families | Run | Artifact | Result |
|---|---:|---|---:|---:|---|
| Development | `1313135` | `1393–1416` | `34009627595` | `9982053254` | **PASS** |
| Transfer | `1313136` | `1417–1440` | `34009722199` | `9982081924` | **PASS** |
| Protected | `1313137` | `1441–1464` | `34009834014` | `9982114975` | **PASS** |
| Final | `1313138` | `1465–1488` | `34009901606` | `9982135289` | **PASS** |

Final artifact digest:

`sha256:4ed9a29d133a84c89032d0bf70b1b60806a474d9d3b4581cd4e0d147b1b35663`

Final result JSON SHA-256:

`65dabbb3cc30f770f988f01e13e3caf6496e8a191f83a9f6fa2c06ec56abc78a`

## All Phase 13C gates

Every evidence stage passed:

- C13.1 — construction integrity, 13 / 13 contrasts
- C13.2 — full-compound execution equivalence
- C13.3 — fresh failure-phenomenon replication
- C13.4 — attribution completeness
- C13.5 — zero adaptation

In every stage, component A — latency was also:

- the largest singleton lateral coverage loss; and
- the largest leave-one-out lateral coverage recovery.

## Replicated full-compound failure

| Stage | Control lateral coverage | Full-compound coverage | Paired loss | Full p95 error inflation |
|---|---:|---:|---:|---:|
| Development | 94.93% | 82.63% | **-12.30 pp** | `1.3835x` |
| Transfer | 94.09% | 83.80% | **-10.29 pp** | `1.3693x` |
| Protected | 96.66% | 84.14% | **-12.53 pp** | `1.4123x` |
| Final | 94.71% | 81.74% | **-12.97 pp** | `1.4319x` |

Every stage therefore reproduced the already-locked Phase 13C failure phenomenon:

- lateral paired loss at least 8 percentage points;
- shifted lateral coverage still at or above the catastrophic 0.80 floor.

The finding is a persistent local calibration failure under this synthetic hard-domain compound, not a total collapse of output availability.

## Latency attribution across all four stages

### Singleton latency loss

| Stage | Latency-only lateral coverage loss |
|---|---:|
| Development | **9.04 pp** |
| Transfer | **8.10 pp** |
| Protected | **11.86 pp** |
| Final | **10.07 pp** |

Final latency-only details:

- control lateral coverage: `0.9471014493`
- latency-only lateral coverage: `0.8463768116`
- singleton loss: **`0.1007246377`**
- latency-only lateral p95 error inflation: `1.3227028491x`

### Leave-one-out recovery when latency is removed

| Stage | Recovery from removing latency |
|---|---:|
| Development | **9.12 pp** |
| Transfer | **7.66 pp** |
| Protected | **8.30 pp** |
| Final | **9.13 pp** |

Final full-minus-latency details:

- full-compound lateral coverage: `0.8173913043`
- full-minus-latency lateral coverage: `0.9086956522`
- recovery: **`0.0913043478`**
- full-minus-latency lateral p95 error inflation: `1.1701896003x`

Both preregistered attribution views therefore independently and repeatedly identify latency.

## Final-stage component attribution

### Singleton lateral coverage losses

- A latency: **`0.1007246377`**
- B bias pair: `0.0115942029`
- C lateral wind drift: `0.0144927536`
- D measurement-noise pair: `0.0043478261`
- E innovation response: `0.0`
- F severity response: `-0.0007246377`

### Leave-one-out lateral recoveries

- A latency: **`0.0913043478`**
- B bias pair: `0.0115942029`
- C lateral wind drift: `-0.0028985507`
- D measurement-noise pair: `0.0086956522`
- E innovation response: `0.0057971014`
- F severity response: `0.0072463768`

## Interaction result

Interaction excess was not consistently positive and was never the dominant explanation:

| Stage | Interaction excess |
|---|---:|
| Development | `-0.0043415340` |
| Transfer | `-0.0058394161` |
| Protected | `-0.0385470719` |
| Final | `-0.0007246377` |

Final:

- full compound lateral loss: `0.1297101449`
- sum singleton losses: `0.1304347826`
- interaction excess: `-0.0007246377`

The preregistered decomposition therefore does **not** support a claim that the domain-13 failure is primarily a positive, super-additive six-way interaction.

The strongest supported simulation-only conclusion is instead:

> On the frozen hard domain-13 synthetic distribution, fixed two-frame estimate latency is the dominant contributor to the compound lateral-coverage failure. Bias and lateral drift provide smaller secondary contributions, while the remaining components have limited stand-alone effect under this study design.

## Execution audit

Phase 13C preserved pre-evidence technical failures rather than silently rerunning exposed evidence:

1. development run `34009501311` stopped before candidate recovery because pandas returned a read-only NumPy view in the noise-only fixture; no evidence was generated; the explicit writable-array remediation was documented before the canonical development exposure;
2. protected run `34009793243` stopped before candidate recovery because a provenance grep used a shorter phrase than the frozen report; no protected evidence was generated; only the metadata assertion was corrected.

Neither technical failure exposed its configured evaluation seed.

## Relationship to Phase 13A and Phase 13B

Phase 13A remains a failed absolute external-validity lineage.

Phase 13B remains a failed paired-degradation lineage because domain 13 exceeded the locked paired-loss bound.

Phase 13C does not convert those failures into passes. Its contribution is explanatory:

- 13A discovered that the external-validity story was more complicated than a clean zero-shot pass;
- 13B isolated the failure to the thirteenth compound domain under matched controls;
- 13C decomposed that compound and replicated the dominant latency attribution across four disjoint partitions.

That negative-result-to-mechanism sequence is retained as the scientific record.

## What Phase 13C does not establish

This study uses synthetic simulator-side stress transforms. It does not establish that real camera latency, real atmospheric wind, or real flight-stack timing would have the same quantitative effect.

It does not establish:

- physical UAV safety;
- flight validation;
- real-sensor causality;
- certification relevance;
- production readiness;
- controller improvement;
- operational reliability;
- autonomous landing safety.

## Claim boundary

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`

Supported final claim:

> Across preregistered development, transfer, protected, and final simulation-only Phase 13C evidence, the frozen thirteenth compound coverage failure replicated and fixed two-frame latency was consistently the dominant synthetic contributor by both singleton-loss and leave-one-out attribution, with no model adaptation.

## Next scientific step

Phase 13C should now close. The next phase should not tune the same synthetic domain until it passes.

A stronger Phase 14 would bridge the replicated uncertainty/latency finding to a **predeclared recoverability or invariance analysis**: treat calibrated uncertainty and timing-induced error as conservative disturbance inputs and test whether a fixed simulated recoverable set remains invariant under a frozen policy/model assumption.

That next phase must keep the same simulation-only claim boundary and must not reinterpret Phase 13C as physical flight evidence.
