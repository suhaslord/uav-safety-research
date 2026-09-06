# Phase 12 iteration 3 — permanently-seen transfer result

## Status

**TRANSFER PASS — PROTECTED AUTHORIZED.**

This record was created after the single authorized transfer evaluation of the exact frozen Phase 12 iteration-3 candidate and before any protected-validation exposure.

## Frozen identity

- scientific Git SHA: `8d0617a83d699cd14eae6194ce3a86a5c034dfbc`
- frozen candidate SHA-256: `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`
- development result SHA-256: `cc502dd7adc11d92f8efb331e6d16b629e6c264f4392549d5d419e31ceb0a9e0`
- transfer workflow run: `34004986381`
- transfer artifact id: `9980655268`
- transfer artifact digest: `sha256:c832c4a85098dbccdc2de7ed0c01146cf32974f906263e20e0aa8271777a83be`
- transfer result SHA-256: `55895a9eb9a11abc36b35baaeac15b5362cd56ed00e0c052b1df275b1e5b959a`
- transfer verdict SHA-256: `f1e5a60d66c314b2d9f2fa3ef1fd8176df511a345419f36296a96328ef6ac464`
- evaluated seed: `913913`

A first workflow attempt (`34004895817`) failed in pre-exposure authorization plumbing because a shell variable written to `$GITHUB_ENV` was read inside the same step. The actual transfer command was skipped, no transfer result/log/artifact was created, and the seed was not generated in that failed attempt. The workflow-only bug was corrected without changing the frozen scientific checkout or candidate.

## Exact transfer gates

| Gate | Result | Verdict |
|---|---:|---|
| group minimums | base 5265; H3 881; H4-5 1264; H6-7 888; rescue 5802 | PASS |
| H1 useful availability | `0.9791666667` | PASS |
| H2 lateral 95% coverage | `0.9450354610` | PASS |
| H2 altitude 95% coverage | `0.9465957447` | PASS |
| H3 calibration MACE | `0.0084893617` | PASS |
| H4 lateral median half-width / p95 error | `0.5431379718x` | PASS |
| H4 lateral p95 half-width / p95 error | **`2.0580396987x`** | **PASS** |
| H4 altitude median half-width / p95 error | `0.7618959202x` | PASS |
| H4 altitude p95 half-width / p95 error | `1.5541348907x` | PASS |
| H5 primary-continuity honesty | lat cov `0.9406528190`; alt cov `0.9502143093`; lat ratio `1.1864397713x`; alt ratio `1.0801646405x` | PASS |
| H6 base-output honesty | lat cov `0.9441595442`; alt cov `0.9413105413`; lat ratio `1.2737660609x`; alt ratio `1.2621071912x` | PASS |
| H8 high-severity honesty | lat cov `0.9446673353`; alt cov `0.9439986627`; lat ratio `1.8094001081x`; alt ratio `1.3141269371x` | PASS |
| H9 rescue honesty | lat cov `0.9481213375`; alt cov `0.9495001724`; lat ratio `1.0156265708x`; alt ratio `0.9982607392x` | PASS |
| H10 rescue accuracy | lat MAE `0.0825790166`; alt MAE `0.1642547112`; lat p95 `0.2045875759`; alt p95 `0.4052157760` | PASS |
| H11 rescue effectiveness | `5802 / 6102 = 0.9508357915` | PASS |

H7 remains diagnostic and was `AUROC = 1.0`.

`all_primary_gates_pass = true`.

## Exposure ledger

Permanently seen in Phase 12 iteration-3 lineage:

- scale fit `880880`
- calibration A `891891`
- calibration B `902902`
- development-only `907907`
- transfer `913913` — **exposed once for the frozen candidate; PASS**

Still untouched at the time this record is committed:

- protected validation `924924`
- final holdout `935935`
- closed Phase 11 protected `858858` — forbidden
- retired Phase 11 P15-v2 `869869` — forbidden

## No-change declaration

**No scientific parameter, coefficient, scale model, reliability formula, calibration rule, group boundary, point-estimator behavior, gate threshold, candidate content, or scientific code was changed after transfer.**

The exact candidate digest remains `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991` and the exact scientific checkout remains `8d0617a83d699cd14eae6194ce3a86a5c034dfbc`.

Only downstream evidence-orchestration/documentation code may be added outside the frozen scientific checkout.

## Authorization

Because every required primary transfer gate and every group minimum passed, protected seed `924924` is authorized for **one evaluation only** using the exact same frozen candidate and scientific checkout.

Final `935935` remains unauthorized until protected validation passes every required primary gate.

## Claim boundary

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`

This remains simulation-only uncertainty research. No physical-flight, certification, production, controller-performance, or operational-safety claim is supported.
