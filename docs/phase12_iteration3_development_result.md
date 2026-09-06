# Phase 12 iteration 3 — permanently-seen development result

## Status

**DEVELOPMENT PASS — CANDIDATE FROZEN — TRANSFER UNEXPOSED at the time this record was written.**

Iteration 3 was preregistered before evaluation in `docs/phase12_iteration3_preregistration.md` and evaluated only on the permanently-seen debugging/development role (`907907`).

- scientific Git SHA: `8d0617a83d699cd14eae6194ce3a86a5c034dfbc`
- development workflow run: `34004695243`
- development artifact id: `9980596398`
- artifact digest: `sha256:2da746b5a287825f7a580bb7726b2cfd1abd36b7fffa5b9a0fe1fba50b44f6dd`
- frozen candidate SHA-256: `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`
- development result SHA-256: `cc502dd7adc11d92f8efb331e6d16b629e6c264f4392549d5d419e31ceb0a9e0`
- candidate determinism: **PASS** (independent rebuild byte-identical)
- targeted predecessor + Phase 12 invariant suite: **PASS**
- repository CI on frozen scientific SHA: **PASS** (`34004695207`)

## Exact development gates

| Gate | Result | Verdict |
|---|---:|---|
| group minimums | base 4762; H3 723; H4-5 980; H6-7 627; rescue 4228 | PASS |
| H1 useful availability | `0.9826388889` | PASS |
| H2 lateral 95% coverage | `0.9494699647` | PASS |
| H2 altitude 95% coverage | `0.9485865724` | PASS |
| H3 calibration MACE | `0.0035865724` | PASS |
| H4 lateral median half-width / p95 error | `0.5864862477x` | PASS |
| H4 lateral p95 half-width / p95 error | **`2.1684489335x`** | **PASS** (`<=2.25x`) |
| H4 altitude median half-width / p95 error | `0.8117241806x` | PASS |
| H4 altitude p95 half-width / p95 error | `1.7062283150x` | PASS |
| H5 primary-continuity honesty | lat cov `0.9639484979`; alt cov `0.9579399142`; lat ratio `1.4272337323x`; alt ratio `1.1502876562x` | PASS |
| H6 base-output honesty | lat cov `0.9433011340`; alt cov `0.9487610248`; lat ratio `1.4000972269x`; alt ratio `1.4181521674x` | PASS |
| H8 high-severity honesty | lat cov `0.9447776112`; alt cov `0.9430284858`; lat ratio `1.9572982803x`; alt ratio `1.4235054617x` | PASS |
| H9 rescue honesty | lat cov `0.9484389782`; alt cov `0.9432355724`; lat ratio `1.0134020204x`; alt ratio `0.9774164936x` | PASS |
| H10 rescue accuracy | lat MAE `0.0842460631`; alt MAE `0.1719935222`; lat p95 `0.2050366724`; alt p95 `0.4138573502` | PASS |
| H11 rescue effectiveness | `4228 / 4428 = 0.9548328817` | PASS |

H7 remains diagnostic and was `AUROC = 1.0`.

`all_primary_gates_pass = true`.

## Target improvement lineage

Locked lateral H4 p95 half-width / p95-error metric:

- closed Phase 11 protected P14R: `2.4354x`
- Phase 12 iteration 1 development: `2.3620x`
- Phase 12 iteration 2 development: `2.3485x`
- Phase 12 iteration 3 development: **`2.16845x`**

Iteration 3 crosses the locked `2.25x` boundary without sacrificing nominal overall coverage. Lateral 95% coverage is `94.95%`, not an undercoverage trade.

## Scientific interpretation

The improvement is consistent with the preregistered mechanism rather than a global interval shrink. The forensic analysis showed that severity/horizon strongly controlled width but did not identify the actual high-error continuity rows, while normalized lateral anchor innovation was consistently associated with error across scale fit, calibration A, calibration B, and development.

Iteration 3 used scale-fit evidence only to fit a monotone innovation-residual reliability contrast inside each continuity horizon group. After recalibration, robust lateral 95% normalized multipliers dropped from iteration-2 values (`H3 7.0109`, `H4-5 6.4671`, `H6-7 5.3463`) to iteration-3 values (`H3 4.4944`, `H4-5 4.4651`, `H6-7 4.0425`) because high-innovation rows now receive more local scale before conformal calibration. Easy continuity rows no longer inherit the same large multiplier simply because they are long-horizon/high-severity.

Base and altitude scales remain exactly iteration 2 by construction; rescue and point-estimator behavior are unchanged.

## Evidence ledger at development freeze

Still untouched/unexposed:

- Phase 12 transfer `913913`
- Phase 12 protected validation `924924`
- Phase 12 final holdout `935935`
- closed Phase 11 protected `858858` (forbidden)
- retired Phase 11 P15-v2 `869869` (forbidden)

Development reuse remains permanently limited to `907907`.

## Freeze decision

No further iteration-3 tuning is authorized. The exact candidate SHA and scientific Git SHA above are frozen.

The next authorized scientific action is a **single transfer evaluation using seed `913913` on this exact frozen candidate and exact scientific checkout**. Protected validation must remain blocked unless transfer passes every required primary gate.

## Claim boundary

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`

This is simulation-only uncertainty research, not physical-flight safety validation or certification evidence.
