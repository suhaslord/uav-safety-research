# Phase 11 P1 frozen validation result — adaptive reliability under compositional shift

## Status

**FROZEN VALIDATION RESULT — MIXED / FAILED OVERALL**

Evidence role: `phase11_p1_frozen_candidate_validation`

P1 candidate implementation commit: `445606c9b962a3452af5565c5291562369660eb8`

Pre-validation invariant-test checkpoint: `b617be6cab178b4af0df648774046c6a873ed0b9`

Validation exposure workflow commit: `1ee4ffaa426db03272f716fb7d9aba249d9295b8`

Validation workflow run: `31968903756`

Artifact ID: `9269238508`

Artifact digest: `sha256:6732711c70c52101b7eb8afe51cda024711b18cd97adf7aaca6d33199caa6588`

Validation seed `77077` is now **permanently seen** and may not be reused as hidden/frozen evidence after any method change.

The earlier workflow run `31968867982` failed before a job was created because of workflow-expression parsing. It did not execute the benchmark and did not expose the validation seed. The authoritative exposure is run `31968903756` above.

## Scope

P1 remains a controlled synthetic reliability-layer benchmark. It does **not** establish new raw-camera accuracy, external-simulator fidelity, controller performance, or physical-flight safety.

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`

## Preregistered gate result

| Gate | Frozen result | Verdict |
|---|---:|---|
| H1 lateral 95% coverage | `87.68%` | FAIL |
| H1 altitude 95% coverage | `88.94%` | FAIL |
| H2 lateral interval-efficiency ratio | `0.785x` | PASS |
| H2 altitude interval-efficiency ratio | `0.852x` | PASS |
| H3 lateral p95 error improvement | `57.22%` | PASS component |
| H3 altitude p95 error improvement | `51.16%` | PASS component |
| H3 usable availability | `43.96%` | FAIL |
| H4 trajectory-level shift AUROC | `0.9722` | PASS |

Overall preregistered result: **MIXED / FAILED**.

Coverage mean absolute calibration error across 50/68/80/90/95 targets: `0.05794`.

## Error and interval diagnostics

Accepted-observation error:

- lateral MAE: `0.03590 m`;
- lateral p95: `0.10366 m`;
- altitude MAE: `0.09746 m`;
- altitude p95: `0.29929 m`.

Before severity selection, available-output p95 error was:

- lateral: `0.24233 m`;
- altitude: `0.61286 m`.

Median 95% half-width:

- lateral: `0.08139 m`;
- altitude: `0.25500 m`.

The preselection P1 perception/bridge layer was available on `1,285 / 1,440 = 89.24%` of truth-visible validation frames. The final `43.96%` usable availability loss therefore came primarily from the frozen severity gate, not from inability to produce an estimate.

## Read-only domain forensics

These diagnostics are reported **after exposure** and are not a license to retune on seed `77077`.

The severity gate rejected every observation in two validation domains:

- `edge+small_scale+oblique`;
- `edge+oblique+blur_noise+low_contrast`.

Other domain acceptance ranged from roughly `29%` to `84%`. This shows the P1 failure is not simply missing perception: the preselection estimator remains mostly available, while the binary severity cutoff becomes too coarse under strong factor coactivation.

## Interpretation

P1 materially improves the failure mode exposed by P0:

1. **Shift detection became stronger.** Trajectory-level AUROC improved from P0's `0.9097` to `0.9722`.
2. **Tail-error selection became stronger.** Accepted p95 error fell by `57.2%` lateral and `51.2%` altitude versus accepting every available P1 output.
3. **Interval efficiency is not the problem.** Median 95% half-width is below accepted p95 error on both axes (`0.785x` / `0.852x`).
4. **Coverage is close but still outside the preregistered band.** `87.68%` / `88.94%` is an improvement over P0 but below the required `90–98%` range.
5. **The dominant failure is selection availability.** A single global severity threshold turns a useful continuous shift signal into an overly aggressive accept/reject boundary, reducing usable availability to `43.96%` despite `89.24%` preselection availability.

P1 therefore supports the next hypothesis: reliability should remain **continuous** deeper into the decision layer. High-risk observations should first receive appropriately widened uncertainty; hard abstention should be reserved for cases where an uncertainty-budget rule cannot remain useful, rather than being triggered by one global severity cutoff.

No P1 candidate constant, risk weight, threshold, bridge rule, scale model, conformal rule, or multiplier was changed after validation exposure.

## Reproducibility hashes

The authoritative GitHub Actions artifact contains the full generated result bundle. File SHA-256 hashes are:

| Artifact | SHA-256 |
|---|---|
| `fit_frames.csv` | `46908866e721f3ecfcf0217d97a27f967b2bce973c34a9366db390384cd7fd81` |
| `calibration_frames.csv` | `1509d7b08212dafa16499f4794809f35d7f0fe27c0e797e6e7324732f142b9c3` |
| `validation_frames.csv` | `1537907f98c5c28df76c905fc115c57d382731fc4fc75cec4da8efc9a7d7bf9d` |
| `calibration.json` | `6aed5d69344ed499aab1bcd0e08b04848273632d831d75990d236ddb419488ba` |
| `validation_result.json` | `cdb5b3b6c77aa184b63635d1b492408c3c9865b55be1ea15eece4fec8673569b` |
| `validation_summary.md` | `b04231179b1c43c04a544b1345b01359b62a0a43be2b6ce0bfe2ed70174a6c50` |
| `manifest.json` | `1d3958da7e04449cf9c2f29558ecd9756300444b14a32d3020a6ef24f5f187ee` |
| `workflow_receipt.json` | `e2094fdfaa31ed48a924749d6cdacc1c3674228aa0dd25bcf42efe2051fa6ad3` |

## Next scientific boundary

Do **not** tune on validation seed `77077`.

Any P2 method change requires new fit/calibration/development/validation seeds and a new freeze document before its validation is exposed. P1 stays archived exactly as this mixed/failed result.
