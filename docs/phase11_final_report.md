# Phase 11 final report — independent rescue + robust uncertainty transfer

## Final status

**PHASE 11 STUDY CLOSED — MIXED / NEGATIVE FINAL GATE — P15 FINAL HOLDOUT NOT EXPOSED**

Phase 11 is finished as a scientific study under its frozen protocol. It is **not** recorded as a full-pass confirmation.

The final P14R candidate passed every required seen-transfer gate, then passed every protected-validation requirement except one locked tail-efficiency component. Because protected validation did not pass overall, the preregistered P15-v2 final holdout was not authorized and seed `869869` remains untouched.

No post-validation retuning is permitted under this Phase 11 lineage.

## Final candidate

P14R method: robust groupwise conformal envelope over the unchanged P14 bounded estimator + independent coarse rescue.

Frozen scientific head:

- `58b06089a621264afb886f6aee2acaacf8a8709c`

Exact candidate SHA-256:

- `bba1b7be7565b470af80db502e6fa5d969bc86c712e322557c06b30e49bd9c86`

Candidate artifact:

- artifact ID `9271909463`
- ZIP SHA-256 `fa03951653efac6ec545987b293473d842c440afa985bdf6f948f8e4784fbe37`

The point estimator and rescue mechanism were unchanged after candidate freeze.

## What P14 established

P14 directly attacked the availability failure left by P13 without extending the primary seven-frame extrapolation boundary.

Its independent synthetic rescue observation recovered `94.19%` of primary-unavailable truth-visible rows and lifted useful availability to `98.15%`. Rescue-only uncertainty honesty and rescue accuracy passed.

P14 nevertheless failed seen transfer overall because its severity-Mondrian uncertainty cells undercovered under the harder fresh compound-shift distribution and several low-severity evaluation cells became underpowered.

That failure motivated exactly one P14R change: uncertainty calibration moved from brittle source/horizon × severity cells to five output groups, with the final radius in each group/axis/coverage target defined before evaluation as the pointwise maximum of two disjoint fresh direct-conformal calibration environments.

## P14R seen transfer — full pass

Evidence:

- seed `847847` — permanently seen
- workflow run `31979250287`
- job `95243501105`
- archived transfer receipt: `results/phase11_p14r_seen_transfer_receipt.json`

The scientific evaluation completed before a later GitHub output-formatting error. The transfer seed was **not rerun**. The exact printed gate result was archived and the continuation workflow verified its digest before protected validation.

### Transfer primary results

| Gate | Result | Verdict |
|---|---:|---|
| H1 useful availability | **97.72%** | PASS |
| H2 lateral 95% coverage | **94.76%** | PASS |
| H2 altitude 95% coverage | **94.79%** | PASS |
| H3 calibration MACE | **0.00512** | PASS |
| H4 lateral median width / p95 error | **0.762×** | PASS |
| H4 lateral p95 width / p95 error | **2.169×** | PASS (`<=2.25×`) |
| H4 altitude median width / p95 error | **1.098×** | PASS |
| H4 altitude p95 width / p95 error | **1.808×** | PASS |
| H5 primary-continuity lateral coverage | **94.03%** | PASS |
| H5 primary-continuity altitude coverage | **94.39%** | PASS |
| H6 base lateral coverage | **94.79%** | PASS |
| H6 base altitude coverage | **94.75%** | PASS |
| H8 high-severity lateral coverage | **92.64%** | PASS |
| H8 high-severity altitude coverage | **93.03%** | PASS |
| H9 rescue lateral coverage | **95.06%** | PASS |
| H9 rescue altitude coverage | **95.01%** | PASS |
| H10 rescue lateral MAE | **0.0825 m** | PASS |
| H10 rescue altitude MAE | **0.1656 m** | PASS |
| H11 rescue recovery | **94.83%** | PASS |

All preregistered group-power minimums passed. H7 shift AUROC was `1.000` and remained diagnostic only.

**Seen-transfer verdict: PASS.**

This is the strongest positive result in the Phase 11 sequence: the robust envelope repaired P14's transfer undercoverage while preserving high availability and rescue accuracy.

## P14R protected validation — mixed / failed overall

Evidence:

- protected seed `858858` — permanently seen after this run
- workflow run `31979476262`
- job `95243864056`
- validation artifact ID `9271959023`
- artifact ZIP SHA-256 `14515fcfeac370335f7de2099384a85dd7821d5998ee009531d4752689af0112`
- `validation_result.json` SHA-256 `abaa2af55c53321d894a9dfdb83291ca2961621f0de42ae97bc0d49ca3196f1e`
- archived validation receipt: `results/phase11_p14r_protected_validation_receipt.json`

### Protected-validation results

| Gate | Result | Verdict |
|---|---:|---|
| Group minimums | all groups strongly powered | PASS |
| H1 useful availability | **98.53%** | PASS |
| H2 lateral 95% coverage | **96.17%** | PASS |
| H2 altitude 95% coverage | **95.82%** | PASS |
| H3 calibration MACE | **0.03678** | PASS |
| H4 lateral median width / p95 error | **0.855×** | PASS |
| H4 lateral p95 width / p95 error | **2.435×** | **FAIL** (`<=2.25×`) |
| H4 altitude median width / p95 error | **1.113×** | PASS |
| H4 altitude p95 width / p95 error | **1.833×** | PASS |
| H5 primary-continuity lateral coverage | **96.29%** | PASS |
| H5 primary-continuity altitude coverage | **95.57%** | PASS |
| H6 base lateral coverage | **96.93%** | PASS |
| H6 base altitude coverage | **96.51%** | PASS |
| H8 high-severity lateral coverage | **93.89%** | PASS |
| H8 high-severity altitude coverage | **93.19%** | PASS |
| H9 rescue lateral coverage | **94.56%** | PASS |
| H9 rescue altitude coverage | **94.64%** | PASS |
| H10 rescue lateral MAE | **0.0840 m** | PASS |
| H10 rescue altitude MAE | **0.1650 m** | PASS |
| H11 rescue recovery | **94.63%** | PASS |

H7 shift AUROC was `0.99921875` and remained diagnostic only.

**Protected-validation verdict: MIXED / FAILED OVERALL.**

The sole required failure was the lateral **p95 interval-width / p95-error ratio**: `2.4354×` versus the frozen `2.25×` maximum. The candidate therefore became too conservative in the lateral tail on this protected distribution even though its empirical coverage, calibration curve, base/continuity honesty, high-severity honesty, rescue honesty, accuracy, and availability all remained inside the locked gates.

The miss is about **tail interval efficiency**, not a return of P14's undercoverage problem.

## P15-v2 final holdout

Final seed:

- `869869`

Status:

**NOT EXPOSED.**

The preregistered rule required both P14R seen transfer and P14R protected validation to pass before P15-v2 could run. Protected validation failed H4, so the workflow skipped the final job automatically.

The final holdout is not burned, is not reclassified as validation, and will not be exposed under this failed Phase 11 candidate.

Because this study is now closed, seed `869869` is retired untouched rather than recycled into a replacement Phase 11 attempt.

## Final scientific conclusion

Phase 11 produced three durable findings.

1. **Independent evidence can solve the bounded-continuity availability problem without extending primary extrapolation.** The rescue mechanism repeatedly recovered roughly `95%` of primary-unavailable rows while retaining sub-gate error and honest rescue intervals.

2. **A robust groupwise conformal envelope can repair severe transfer undercoverage.** P14R moved the system from P14's failed `88.13% / 86.61%` overall 95% coverage to `94.76% / 94.79%` on fresh seen transfer, with MACE dropping from `0.10292` to `0.00512`.

3. **The remaining failure is narrow but real: tail efficiency under unseen distribution shift.** Protected validation preserved approximately `96%` overall coverage and passed every honesty/accuracy/availability gate, but the lateral p95 interval-width ratio widened to `2.435×`, beyond the preregistered `2.25×` limit.

Therefore the complete Phase 11 system is **not claimed to have achieved final unseen replication**. The correct final claim is narrower:

> In this simulation benchmark, bounded primary continuity plus independent rescue achieved high availability and robust uncertainty coverage across fresh transfer and protected validation, but the final protected test exposed excessive lateral tail-interval width, preventing final confirmation.

That negative boundary is part of the result, not something to tune away after exposure.

## Exposure ledger

P14R permanently seen:

- fit `814814`
- calibration A `825825`
- calibration B `836836`
- seen transfer `847847`
- protected validation `858858`

Retired untouched:

- P15-v2 final holdout `869869`

Older failed-lineage protected/final seeds remain retired according to their original records and are not reused.

## Study-stop rule

Phase 11 scientific tuning stops here.

Any future attempt to improve lateral tail efficiency must be a **new preregistered phase with fresh development, transfer, and protected evidence**. It may cite Phase 11 as motivation, but it cannot relabel any Phase 11 seen data as unseen evidence or expose `869869` as a replacement Phase 11 final confirmation.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no claim that a real auxiliary sensor follows the synthetic rescue distribution
- no new raw-camera accuracy claim
- no final unseen-replication claim
- negative/mixed protected-validation outcome is frozen evidence
