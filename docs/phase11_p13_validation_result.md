# Phase 11 P13 protected validation result — two-stage three-group conformal

## Status

**FROZEN PROTECTED VALIDATION RESULT — MIXED / FAILED OVERALL**

Evidence role: `phase11_p13_frozen_candidate_validation`

P13 candidate / development boundary:

- scientific freeze head: `0d3244191062ea13fd23c0bf8d461058106ede6d`
- frozen candidate SHA-256: `4198efff7d58c478efa6e173a7a1ad4a750540ced515a06fe1392f1429ce9a46`
- development run: `31975070771`
- development artifact ID: `9270836536`
- development artifact digest: `sha256:aa58e3fa71af2f2766f3453e28d19a09209ccd193b1fa68cf7711b7ba9baf561`
- seen challenge seed `616616` passed every preregistered H1-H6 gate before protected validation.

Protected validation:

- validation seed: `627627`
- validation families: `496..515`
- first / authoritative validation run: `31975236550`
- validation workflow head: `cf6d43ea39c478b097b3821c888d92c486f82a24`
- validation artifact ID: `9270879335`
- validation artifact digest: `sha256:376ab16e286c3f8a002f1506c5ce566af3bfb76b844fdc407f3b5a9cf8fea702`
- `validation_frames.csv` SHA-256: `71a2bbe8465f006c141b17893e11bfe617f5a09038df765abcc11d04d1a54f48`
- `validation_result.json` SHA-256: `98bfaf81902c8ac1a42285d31adeb06b6bfb680b0ea8a39615b961848f5f3f17`

The validation workflow regenerated the candidate from the frozen scientific commit and verified its SHA-256 byte-for-byte before seed `627627` was generated. It also reproduced the previously seen challenge result SHA before the protected split was touched.

Seed `627627` is now **permanently seen** and may never be reused as hidden evidence after a method change.

## Preregistered gate result

| Gate | Frozen result | Verdict |
|---|---:|---|
| H1 useful availability | `80.02%` | **FAIL** (`>=92%`) |
| H2 lateral 95% coverage | `92.72%` | PASS |
| H2 altitude 95% coverage | `92.51%` | PASS |
| H3 calibration-curve MACE | `0.02647` | PASS |
| H4 lateral median half-width / p95 error | `0.591x` | PASS |
| H4 lateral p95 half-width / p95 error | `1.593x` | PASS |
| H4 altitude median ratio | `0.750x` | PASS |
| H4 altitude p95 ratio | `0.888x` | PASS |
| H5 continuity lateral 95% coverage | `89.72%` | PASS |
| H5 continuity altitude 95% coverage | `85.28%` | **FAIL** (`>=88%`) |
| H5 continuity lateral p95 width / error | `0.768x` | PASS |
| H5 continuity altitude p95 width / error | `0.606x` | PASS |
| H6 base lateral 95% coverage | `93.28%` | PASS |
| H6 base altitude 95% coverage | `93.85%` | PASS |
| H6 base lateral p95 width / error | `0.860x` | PASS |
| H6 base altitude p95 width / error | `0.879x` | PASS |
| H7 trajectory-level shift AUROC | `1.000` | diagnostic PASS |

Overall preregistered result: **MIXED / FAILED** because H1 and H5-altitude failed.

## Validation diagnostics

- truth-visible rows: `9,600`;
- available rows: `7,682`;
- unavailable rows: `1,918`;
- all-available lateral p95 error: `0.55788 m`;
- all-available altitude p95 error: `1.10843 m`;
- continuity rows: `1,196`;
- continuity lateral p95 error: `1.15727 m`;
- continuity altitude p95 error: `1.62488 m`.

Read-only forensic classification of unavailable rows from the frozen artifact:

- `insufficient_anchors`: `1,515`;
- `gap_beyond_horizon`: `403`.

Among the `1,515` insufficient-anchor rows:

- `1,103` occurred before **any** genuine primary candidate had been observed in that sequence;
- `412` occurred with exactly one genuine primary candidate observed so far.

There were `11` validation sequences with **zero primary candidate detections across the entire sequence**, all in the hardest multi-factor validation composition. This shows that merely extending the existing two-anchor continuity horizon cannot recover the dominant availability loss.

## Interpretation

P13 establishes an important separation of responsibilities:

1. **Two-stage grouped conformal transfer works for base output.** Base-output coverage, calibration, and efficiency remain strong under protected unseen compositions.
2. **Overall uncertainty transfer largely works.** Overall 95% coverage and calibration-curve quality pass.
3. **The dominant protected failure is observation availability.** Most missing estimates occur before the continuity layer has the two genuine anchors it requires.
4. **Longer extrapolation alone cannot solve the main failure.** Only `403/1,918` unavailable rows are beyond the current horizon; `1,515/1,918` lack sufficient anchors.
5. **Continuity altitude remains a secondary weakness.** The intervals are efficient but under-cover altitude continuity at `85.28%`, suggesting the continuity population is harder than the transfer-calibration population even after the second conformal stage.

## Next revision

P14 should not retune P13 on seed `627627` and should not simply extend the continuity horizon.

The next preregistered hypothesis should add a genuinely independent, simulation-only **coarse auxiliary observation channel** that can produce a low-fidelity state observation when the fragile primary visual candidate is unavailable. The channel must be generated by a declared stochastic observation model using truth only to synthesize the simulated measurement; truth itself may never be passed to the estimator.

P14 should:

- preserve the primary candidate generator unchanged;
- preserve the P13/P9 soft genuine-anchor continuity method for primary-anchor gaps;
- add an independent coarse auxiliary lateral/altitude observation with its own fresh stochastic noise/dropout process;
- never use future information or controller state;
- explicitly mark auxiliary observations as a separate source;
- calibrate uncertainty separately for base, primary continuity, and auxiliary-observation outputs;
- test whether the auxiliary modality recovers anchorless extreme-shift sequences without making intervals dishonest or excessively wide;
- use entirely fresh fit/calibration/transfer/challenge/validation evidence.

This is a simulation-only multimodal-redundancy hypothesis, not evidence that any specific physical sensor would achieve the modeled performance.

## Retuning / final-holdout boundary

No P13 method or calibration constant may be changed and then evaluated again on seed `627627` as unseen evidence.

P13 failed internal protected validation, so the final Phase 11 frozen holdout is **not authorized** and is not exposed.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
- no claim that a real auxiliary sensor matches a future P14 simulation model
