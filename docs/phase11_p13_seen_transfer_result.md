# Phase 11 P13 frozen seen-transfer result — severity-conditioned Mondrian direct conformal

## Status

**FROZEN SEEN-TRANSFER RESULT — MIXED / FAILED OVERALL — PROTECTED VALIDATION NOT EXPOSED**

P13 preregistration: `docs/phase11_p13_severity_mondrian_preregistration.md`

## Partition freeze

- workflow run: `31977619169`
- scientific head: `5abb1d96b15dcbc2f3774d00815f73ed70cada8f`
- artifact ID: `9271478158`
- artifact digest: `sha256:dc9bbf3368cd214bc79cea74c943ad2a96c2e9fff8abe3a7b7e526bac1eb6718`
- `partition_freeze.json` SHA-256: `5d74be1f335e2f3d28e9d089be822bcbdb24704bb23e170bc227e5802fb8abec`

Partition-frozen severity cutpoints:

| Base group | lower | upper | partition rows |
|---|---:|---:|---:|
| `base_output` | `0.302651` | `0.579765` | 5,265 |
| `continuity_h3` | `0.383557` | `0.575978` | 478 |
| `continuity_h45` | `0.307234` | `0.589930` | 586 |
| `continuity_h67` | `0.304220` | `0.595628` | 385 |

These cutpoints were frozen before conformal-calibration residuals were generated.

## Candidate freeze

- workflow run: `31977665287`
- candidate head: `6f3539c06fbd2d906bc5b682ca7287c7c435e4e7`
- artifact ID: `9271494076`
- artifact digest: `sha256:d7168d0e2f16af0636c4d13f04881b36a9478701d2d28c960ee3c7dacb236ad1`
- `candidate_freeze.json` SHA-256: `91795bf3502ccda6a1df623e81952f76d8adce28fc89350d7cc4a43c7a5e4f56`
- `manifest.json` SHA-256: `ddab68b4c60e2d64533fbcb1be7d6e74c1fd9a9e636dc4b7f96c896c5f5c50aa`

All 12 source/horizon x severity cells exceeded their preregistered calibration minimums. Smallest cells were the h6-7 severity cells, with `232`, `232`, and `245` rows.

## Seen transfer

- workflow run: `31977731060`
- workflow head: `bc116950f8474f079a8ef792ac04f32a1d106f40`
- seen-transfer seed: `671671` — permanently seen
- transfer artifact ID: `9271507909`
- transfer artifact digest: `sha256:fda7c773bb8b7a363d529b81562858dcf141fdc08330afe342801460b53d5889`
- `transfer_result.json` SHA-256: `08088b2c865f62b418435227b25f01de80c344066aa289694e0d35fcac297f4d`
- `transfer_natural_diagnostic.json` SHA-256: `536acf48e6113cffb94c06837e71590db71bcf0cd53fae1ecc8b6509a0bddd0b`

The workflow verified scientific-file immutability, reran all P9+P13 invariants (`9 passed`), and verified the exact candidate digest before exposing transfer.

All 12 transfer cells exceeded the preregistered cell minimums.

## Preregistered transfer gates

| Gate | Frozen result | Verdict |
|---|---:|---|
| H1 useful availability | `81.79%` | **FAIL** (`>=92%`) |
| H2 lateral 95% coverage | `93.72%` | PASS |
| H2 altitude 95% coverage | `94.11%` | PASS |
| H3 calibration MACE | `0.02590` | PASS |
| H4 lateral median half-width / p95 error | `0.763x` | PASS component |
| H4 lateral p95 half-width / p95 error | `2.463x` | **FAIL** (`<=2.25x`) |
| H4 altitude median half-width / p95 error | `0.760x` | PASS |
| H4 altitude p95 half-width / p95 error | `1.650x` | PASS |
| H5 continuity lateral 95% coverage | `93.76%` | PASS |
| H5 continuity altitude 95% coverage | `93.40%` | PASS |
| H5 continuity lateral p95 width / error | `1.522x` | PASS |
| H5 continuity altitude p95 width / error | `1.524x` | PASS |
| H6 base lateral 95% coverage | `93.70%` | PASS |
| H6 base altitude 95% coverage | `94.34%` | PASS |
| H6 base lateral p95 width / error | `1.282x` | PASS |
| H6 base altitude p95 width / error | `1.325x` | PASS |
| H7 severity AUROC | `1.000` | diagnostic PASS |
| H8 high-severity lateral 95% coverage | `92.19%` | PASS |
| H8 high-severity altitude 95% coverage | `92.74%` | PASS |
| H8 high-severity lateral p95 width / error | `2.293x` | PASS |
| H8 high-severity altitude p95 width / error | `1.398x` | PASS |

Overall preregistered result: **MIXED / FAILED**.

`all_primary_gates_pass = false`

`P13_VALIDATION_ELIGIBLE = false`

## What P13 establishes

P13 provides strong evidence for the P12 severity hypothesis on fresh data.

Compared with P12's fixed source/horizon-only direct conformal transfer failure, P13's separately frozen severity-conditioned Mondrian partition restored:

- overall 95% coverage into the target band on both axes;
- calibration-curve quality (`MACE = 0.0259`);
- continuity-specific honesty;
- base-output honesty;
- explicitly preregistered high-severity honesty.

This occurred without a learned scale model, learned correction model, post-hoc transfer multiplier, or P12-derived severity threshold.

The remaining failures are now different:

1. useful output availability is far below the preregistered floor under the harder fresh P13 composition set;
2. lateral interval-tail efficiency narrowly misses H4 even though median efficiency and all other interval-efficiency checks are acceptable.

Thus the dominant research bottleneck has moved from **uncertainty calibration under shift** to **maintaining causal estimate continuity/availability under stronger compounded outages**, with a secondary lateral tail-efficiency issue.

## Exposure ledger

Permanently seen P13 evidence:

- fit seed `638638`;
- severity-partition seed `649649`;
- conformal-calibration seed `660660`;
- seen-transfer seed `671671`.

Protected-validation seed `682682` is **NOT EXPOSED** and is retired with P13 because seen transfer failed H1/H4.

No P13 protected-validation workflow may be run.

## Next scientific boundary

Read-only P13 forensics should first separate:

- insufficient-anchor unavailable rows;
- gaps beyond the seven-frame continuity horizon;
- natural-stream availability versus event-stratified availability;
- availability by composition, gap stratum, and severity regime;
- the severity/horizon cells responsible for the lateral p95 interval-tail width.

Any P14 method change must use completely fresh evidence and a new preregistration. P14 must not simply relax H1 or H4 after seeing P13.

A final Phase 11 holdout remains unauthorized and still requires a separate explicit user approval at a future exact freeze checkpoint.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
- negative/mixed results remain permanent evidence.
