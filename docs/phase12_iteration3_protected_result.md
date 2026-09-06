# Phase 12 iteration 3 — permanently-seen protected validation result

## Status

**PROTECTED PASS — FINAL HOLDOUT AUTHORIZED.**

This record was created after the single authorized protected validation of the exact frozen Phase 12 iteration-3 candidate and before any final-holdout exposure.

## Frozen identity

- scientific Git SHA: `8d0617a83d699cd14eae6194ce3a86a5c034dfbc`
- frozen candidate SHA-256: `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`
- protected workflow run: `34005089276`
- protected artifact id: `9980682102`
- protected artifact digest: `sha256:f7ae48fcb48486de2e039db0bfbb13f6937efe799c7eb80748b6368692434667`
- protected result SHA-256: `7440152a9b90ddcf1ed14f9e9c9269da21190463ddddf8259e56a39d0588358f`
- protected verdict SHA-256: `6b527e713b2ad7c37332b1444381767c2123bf5a7ffddd928bbcd7682e43b655`
- evaluated seed: `924924`

## Exact protected gates

| Gate | Result | Verdict |
|---|---:|---|
| group minimums | base 6546; H3 816; H4-5 1056; H6-7 741; rescue 5013 | PASS |
| H1 useful availability | `0.9841666667` | PASS |
| H2 lateral 95% coverage | `0.9539937906` | PASS |
| H2 altitude 95% coverage | `0.9524414338` | PASS |
| H3 calibration MACE | `0.0158233136` | PASS |
| H4 lateral median half-width / p95 error | `0.4836039376x` | PASS |
| H4 lateral p95 half-width / p95 error | **`2.2124459142x`** | **PASS** (`<=2.25x`) |
| H4 altitude median half-width / p95 error | `0.6957982089x` | PASS |
| H4 altitude p95 half-width / p95 error | `1.8198635840x` | PASS |
| H5 primary-continuity honesty | lat cov `0.9410639112`; alt cov `0.9326444700`; lat ratio `1.1445186005x`; alt ratio `0.9374094833x` | PASS |
| H6 base-output honesty | lat cov `0.9637946838`; alt cov `0.9618087382`; lat ratio `1.8521203037x`; alt ratio `1.8083034493x` | PASS |
| H8 high-severity honesty | lat cov `0.9518072289`; alt cov `0.9450164294`; lat ratio `1.8736579182x`; alt ratio `1.3368793338x` | PASS |
| H9 rescue honesty | lat cov `0.9479353680`; alt cov `0.9505286256`; lat ratio `1.0312774311x`; alt ratio `1.0079170579x` | PASS |
| H10 rescue accuracy | lat MAE `0.0830923647`; alt MAE `0.1662542649`; lat p95 `0.2014827163`; alt p95 `0.4013336186` | PASS |
| H11 rescue effectiveness | `5013 / 5241 = 0.9564968517` | PASS |

H7 remains diagnostic and was `AUROC = 0.99609375`.

`all_primary_gates_pass = true`.

## Exposure ledger

Permanently seen:

- scale fit `880880`
- calibration A `891891`
- calibration B `902902`
- development-only `907907`
- transfer `913913` — PASS
- protected validation `924924` — **exposed once for the exact frozen candidate; PASS**

Still untouched at the time this record is committed:

- final holdout `935935`
- closed Phase 11 protected `858858` — forbidden
- retired Phase 11 P15-v2 `869869` — forbidden

## No-change declaration

**No scientific parameter, coefficient, scale model, reliability formula, calibration rule, group boundary, point-estimator behavior, gate threshold, candidate content, or scientific code changed after transfer or after protected validation.**

The exact candidate digest remains `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`; the exact scientific checkout remains `8d0617a83d699cd14eae6194ce3a86a5c034dfbc`.

Only evidence-orchestration and documentation files have changed outside that frozen checkout.

## Authorization

Because every required protected primary gate and group minimum passed, final seed `935935` is authorized for **one evaluation only** using the exact same frozen candidate and scientific checkout.

No refit, recalibration, coefficient update, scale adjustment, feature change, threshold change, group change, domain change, or scientific-code change is authorized.

## Claim boundary

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`

This remains simulation-only uncertainty research. No physical-flight, certification, production, controller-performance, or operational-safety claim is supported.
