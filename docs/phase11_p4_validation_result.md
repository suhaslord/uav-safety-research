# Phase 11 P4 protected validation result — all-available calibrated uncertainty

## Status

**FROZEN PROTECTED VALIDATION RESULT — MIXED / FAILED OVERALL**

Evidence role: `phase11_p4_frozen_candidate_validation`

Candidate-freeze workflow:

- run: `31970592820`
- freeze head: `79e85654516cfec27aaf017f4119e90820e6f9d7`
- candidate artifact ID: `9269679511`
- candidate artifact digest: `sha256:390ce0ecfa56fcc01357b58b96b45ffb80a2fd0a2dd37ae7adf3af648e4cffd2`

Protected validation:

- validation seed: `198198`
- validation families: `69..71`
- first/authoritative validation run: `31970692023`
- validation workflow head: `3e9c4dc4c8c39c7f70d02ee3fdb6ebaa29572c01`
- validation artifact ID: `9269703172`
- validation artifact digest: `sha256:fad305133163e6908199a9062caaad365cab3b3fb987674a93dde2befae6aac7`
- `validation_frames.csv` SHA-256: `275c2c30622f5d158aecaf79bc3fbda209433120e57d8fee4a110a2248399172`
- `validation_result.json` SHA-256: `a55f630e3f29e03ba390750da69543e1efe54f14fcf8c62f0cd0543dc150b09e`

Validation seed `198198` is now **permanently seen** and may never be reused as hidden or protected evidence after a method change.

## Preregistered gate result

| Gate | Frozen result | Verdict |
|---|---:|---|
| H1 lateral 95% coverage | `93.98%` | PASS |
| H1 altitude 95% coverage | `92.73%` | PASS |
| H2 calibration-curve MACE | `0.01972` | PASS |
| H3 lateral median half-width / p95 error | `0.632x` | PASS |
| H3 altitude median ratio | `0.614x` | PASS |
| H3 lateral p95 half-width / p95 error | `1.177x` | PASS |
| H3 altitude p95 ratio | `1.030x` | PASS |
| H4 preselection availability | `83.13%` | **FAIL** (`>=90%`) |
| H5 trajectory-level shift AUROC | `0.94271` | PASS |

Overall preregistered result: **MIXED / FAILED** because H4 failed.

## Validation diagnostics

All-available point-error diagnostics:

- lateral MAE: `0.07395 m`;
- lateral p95: `0.25347 m`;
- altitude MAE: `0.17733 m`;
- altitude p95: `0.69015 m`.

95% interval diagnostics:

- lateral median half-width: `0.16010 m`;
- lateral p95 half-width: `0.29828 m`;
- altitude median half-width: `0.42362 m`;
- altitude p95 half-width: `0.71057 m`.

Full calibration curve:

| Target | lateral coverage | altitude coverage |
|---|---:|---:|
| 50% | `47.37%` | `47.79%` |
| 68% | `66.83%` | `64.66%` |
| 80% | `78.28%` | `77.44%` |
| 90% | `88.47%` | `88.72%` |
| 95% | `93.98%` | `92.73%` |

The primary reliability layer therefore transferred substantially better than P0/P1 and remained efficient under protected unseen compositions. The only failed primary gate was the fraction of truth-visible frames on which the inherited perception + short temporal bridge produced an estimate.

## Interpretation

P4 changes the Phase 11 bottleneck:

1. **Coverage transfer passes.** Unlike P0, the uncertainty envelope remains within the preregistered 90–98% 95%-coverage band on both axes.
2. **Calibration-curve quality passes.** MACE is `0.0197`, well inside the `0.06` limit.
3. **Interval efficiency passes with margin.** P95 half-width is only about `1.18x` lateral and `1.03x` altitude relative to observed p95 point error.
4. **Shift discrimination remains strong.** AUROC is `0.943`.
5. **Availability is now the dominant failure.** The reliability method did not reject estimates; the underlying perception + bounded bridge simply produced an estimate on `83.13%` of truth-visible validation frames, below the preregistered `90%` floor.

Therefore P4 does not justify retuning the calibrated uncertainty method on seed `198198`. The next revision should preserve the P4 reliability layer concept and investigate a new, separately preregistered **perception-continuity layer** on entirely new evidence.

## Retuning boundary

No P4 scale basis, standardization, winsorization, prediction guard, ridge lambda, conformal rule, transfer multiplier, target, or gate was changed after validation exposure.

Any attempt to improve availability requires P5 with new fit/calibration/development/validation seeds and trajectory families. P4 seed `198198` may be used only for read-only descriptive forensics.

Passing a future P5 internal validation would still not authorize the final Phase 11 frozen holdout. That final holdout requires a separate explicit user approval checkpoint.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
