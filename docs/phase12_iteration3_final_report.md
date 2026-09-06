# Phase 12 iteration 3 — final replication report

## Current status

**PHASE 12 ITERATION 3 FINAL REPLICATION PASS — LINEAGE COMPLETE.**

The exact same frozen candidate passed development, transfer, protected validation, and final holdout without refitting, recalibration, coefficient changes, scale changes, feature changes, group changes, threshold changes, or scientific-code changes.

This remains simulation-only uncertainty research.

## Frozen scientific identity

- branch: `phase12/adaptive-normalized-conformal`
- PR: `#67 — Phase 12: adaptive normalized conformal uncertainty`
- frozen scientific Git SHA: `8d0617a83d699cd14eae6194ce3a86a5c034dfbc`
- frozen candidate SHA-256: `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`
- method: `continuity_lateral_innovation_residual_normalized_robust_conformal`
- candidate schema: `aegisland.phase12.adaptive-normalized-conformal.candidate.v3`

## Scientific result — final holdout

Final seed `935935` was exposed once only after the frozen candidate had passed transfer and protected validation.

- final workflow run: `34005196970`
- final artifact id: `9980716252`
- final artifact digest: `sha256:4024ecbd1eab95c5f0381d29a1a28fc95a36ec2909e3e9ecc2b8f8c54b9fc345`
- final result SHA-256: `c4c03845b30e6862f9590c0bf6439ed341ab366e1e5a83a92ed5d49b6c01974a`
- final verdict SHA-256: `4cc8785ddb067b08cb7cb05713212ac86df7ae396a7c872a4d3c3a15914bea66`
- `all_primary_gates_pass = true`
- `phase12_pass = true`

| Gate | Final result | Verdict |
|---|---:|---|
| group minimums | base 7060; H3 883; H4-5 1139; H6-7 809; rescue 4303 | PASS |
| H1 useful availability | `0.9856944444` | PASS |
| H2 lateral 95% coverage | `0.9553332394` | PASS |
| H2 altitude 95% coverage | `0.9522333380` | PASS |
| H3 calibration MACE | `0.0175141609` | PASS |
| H4 lateral median half-width / p95 error | `0.5612520782x` | PASS |
| H4 lateral p95 half-width / p95 error | **`2.2303494666x`** | **PASS** (`<=2.25x`) |
| H4 altitude median half-width / p95 error | `0.7768163165x` | PASS |
| H4 altitude p95 half-width / p95 error | `1.7291450210x` | PASS |
| H5 primary-continuity honesty | lat cov `0.9516072059`; alt cov `0.9448957965`; lat ratio `1.3005784630x`; alt ratio `1.0588382874x` | PASS |
| H6 base-output honesty | lat cov `0.9617563739`; alt cov `0.9586402266`; lat ratio `1.6847585889x`; alt ratio `1.6648710882x` | PASS |
| H8 high-severity honesty | lat cov `0.9450806263`; alt cov `0.9436784295`; lat ratio `1.7719605474x`; alt ratio `1.2491097886x` | PASS |
| H9 rescue honesty | lat cov `0.9472461074`; alt cov `0.9465489194`; lat ratio `1.0133599048x`; alt ratio `0.9792014018x` | PASS |
| H10 rescue accuracy | lat MAE `0.0827458080`; alt MAE `0.1659939473`; lat p95 `0.2050451938`; alt p95 `0.4131029626` | PASS |
| H11 rescue effectiveness | `4303 / 4509 = 0.9543135950` | PASS |

H7 remains diagnostic and was `AUROC = 0.9833333333`.

## Replication progression

The locked target was overall lateral H4 p95 half-width / p95 error `<=2.25x`.

| Evidence stage | Lateral H4 p95 ratio | Lateral 95% coverage | Status |
|---|---:|---:|---|
| Phase 11 P14R protected | `2.4354x` | nominal | FAIL H4 only |
| Phase 12 v1 development | `2.3620x` | `94.984%` | FAIL H4 only |
| Phase 12 v2 development | `2.3485x` | `95.279%` | FAIL H4 only |
| Phase 12 v3 development | **`2.1684489335x`** | `94.94699647%` | PASS |
| Phase 12 v3 transfer | **`2.0580396987x`** | `94.50354610%` | PASS |
| Phase 12 v3 protected | **`2.2124459142x`** | `95.39937906%` | PASS |
| Phase 12 v3 final | **`2.2303494666x`** | `95.53332394%` | PASS |

The final result is close to the locked boundary, which makes the protected and final replications important: the candidate was not tuned after transfer or protected evidence and still remained under the preregistered H4 limit with nominal coverage.

## Scientific interpretation

Iteration 3 succeeded because it corrected uncertainty allocation rather than globally shrinking intervals.

The permanently-seen forensic analysis showed that the widest iteration-2 rows were concentrated in long-horizon continuity outputs, but only about `20.7%` of development top-5%-width rows overlapped top-5%-error rows. Severity strongly predicted current width but had essentially zero development rank relationship with actual continuity error, while normalized lateral anchor innovation consistently tracked error across scale-fit, both calibration environments, and development.

Iteration 3 therefore retained the iteration-2 severity/horizon baseline and introduced one low-capacity continuity-only lateral reliability coordinate:

`u = log1p(p9_anchor_innovation_lateral_abs / frozen_lateral_innovation_scale)`

Its monotone residual contrast was fit only on Phase 12 scale-fit evidence, then frozen before development. Calibration A/B, their pointwise maximum, finite-sample conformal quantiles, point estimator, continuity behavior, rescue behavior, altitude uncertainty, groups, gates, and thresholds remained unchanged.

The result is consistent with the intended mechanism: width moved toward genuinely unstable estimator states instead of being assigned mainly by severity/horizon. The improvement persisted on three downstream unseen stages without scientific changes.

## Evidence ledger

Permanently seen in this completed Phase 12 lineage:

- scale fit `880880`
- calibration A `891891`
- calibration B `902902`
- development-only `907907`
- transfer `913913` — exposed once, PASS
- protected validation `924924` — exposed once, PASS
- final holdout `935935` — exposed once, PASS

Untouched / forbidden throughout Phase 12:

- Phase 11 protected seed `858858` — not reused, not reevaluated
- retired Phase 11 P15-v2 seed `869869` — not exposed

No further Phase 12 evidence seed is authorized for tuning this lineage.

## Engineering / QA state

- frozen scientific SHA: `8d0617a83d699cd14eae6194ce3a86a5c034dfbc`
- candidate SHA: `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`
- development result SHA: `cc502dd7adc11d92f8efb331e6d16b629e6c264f4392549d5d419e31ceb0a9e0`
- transfer result SHA: `55895a9eb9a11abc36b35baaeac15b5362cd56ed00e0c052b1df275b1e5b959a`
- protected result SHA: `7440152a9b90ddcf1ed14f9e9c9269da21190463ddddf8259e56a39d0588358f`
- final result SHA: `c4c03845b30e6862f9590c0bf6439ed341ab366e1e5a83a92ed5d49b6c01974a`
- candidate determinism: PASS; independent freeze rebuild byte-identical
- frozen targeted predecessor + Phase 12 suite: PASS (`35 passed` in downstream freeze checks)
- broad repository CI on frozen scientific SHA: PASS (`34004695207`), including compile, unit tests, Research Cockpit JS, trace JS, and repository smoke pipelines
- transfer one-shot workflow: PASS (`34004986381`)
- protected one-shot workflow: PASS (`34005089276`)
- final one-shot workflow: PASS (`34005196970`)

A first transfer orchestration attempt (`34004895817`) failed before seed exposure due a same-step `$GITHUB_ENV` shell-variable bug. The actual transfer command was skipped and no evidence artifact existed. The workflow-only bug was fixed; the scientific SHA and candidate remained unchanged. The successful transfer then exposed `913913` once.

## Claim boundary

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`

Phase 12 does **not** establish real-world UAV safety, physical-flight validation, certification relevance, production readiness, controller-performance improvement, real-sensor rescue equivalence, autonomous landing safety, or operational reliability.

The supported claim is narrower: in the preregistered simulation study, the frozen iteration-3 uncertainty model passed the locked Phase 12 primary gates in development, transfer, protected validation, and final unseen replication.

## Next authorized action

**Close the Phase 12 experimental lineage and finalize PR #67 as the auditable simulation-only research record. Do not tune or expose additional evidence in this lineage.**
