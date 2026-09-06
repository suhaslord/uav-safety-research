# Phase 17 fit freeze — Context-Conditional Coefficient Mismatch Audit

## Status

**FIT PASS / DEVELOPMENT AUTHORIZED BY PREREGISTRATION.**

This note freezes the exact Phase 17 fit identity before any development evidence is exposed. It does not change the preregistered intervention, contexts, coefficient form, gates, or thresholds.

## Fit evidence identity

- workflow run: `34011621058`
- artifact: `9982637646`
- artifact digest: `sha256:aba8f3e65f3b99e5c4a45c61027d8fff73ab75f68a4efd41183200bb2f31dacd`
- scientific Git SHA: `c497bb6bdfeb7a84160d67ae67fd441d18ca25bc`
- fit seed: `1717170`
- fit families: `1809–1832`
- fit candidate SHA-256: `2ca52a418f5616e0e83ef84d0c9238ee429260cd4de7a553356b0c1bba44d8e0`
- frozen Phase 12 candidate SHA-256: `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`
- frozen Phase 14 bridge SHA-256: `0443d4e45a1966c77544c5c9965de8caec6e622c79ef8c2ce47aee82a3c95981`

## Fit verdict

All preregistered fit gates passed:

- F17.1 construction integrity — **PASS**
- F17.2 finite unclipped coefficient candidate — **PASS**
- F17.3 simple-context large latency shift — **PASS**
- F17.4 hard-context Phase 14 proximity — **PASS**
- F17.5 mismatch heterogeneity — **PASS**

`fit_eligible_for_development = true`

## Frozen lateral coefficients

Frozen Phase 14 lateral coefficient:

- `a_phase14 = 0.6102677720`

### Context S — simple

Matched fit transitions: `1,359`

- control lateral `a = 0.5470675029`
- latency lateral `a = 0.8811661057`
- latency minus control = `+0.3340986028`
- absolute latency-vs-Phase14 mismatch = `0.2708983337`

### Context H — hard

Matched fit transitions: `1,216`

- control lateral `a = 0.0931675212`
- latency lateral `a = 0.5426158628`
- latency minus control = `+0.4494483416`
- absolute latency-vs-Phase14 mismatch = `0.0676519092`

Mismatch heterogeneity:

- simple mismatch minus hard mismatch = `0.2032464245`
- preregistered minimum = `0.10`

## Frozen altitude coefficients

These are retained in the exact candidate and checked for finite/unclipped transfer but are not the primary mechanism claim.

Simple:
- control altitude `a = 0.5165150242`
- latency altitude `a = 0.5434519299`

Hard:
- control altitude `a = 0.0686962953`
- latency altitude `a = 0.1303244265`

## Development authorization

The only now-authorized fresh evidence is:

- development seed `1717171`
- families `1833–1856`

The Phase 17 scientific implementation is frozen at fit SHA `c497bb6bdfeb7a84160d67ae67fd441d18ca25bc`. Before development exposure, the workflow must verify that changes after this SHA are restricted to this fit-freeze note and the development workflow itself.

No refit is permitted on development.

Transfer `1717172`, protected `1717173`, and final `1717174` remain unexposed.

## Claim boundary

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`

The fit result identifies a synthetic context-dependent coefficient pattern only. It does not establish physical latency causality, physical-flight safety, full-simulator invariance, certification relevance, controller improvement, production readiness, or operational reliability.