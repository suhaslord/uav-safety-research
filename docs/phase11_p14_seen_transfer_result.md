# Phase 11 P14 frozen seen-transfer result — bounded primary continuity + independent rescue

## Status

**FROZEN SEEN-TRANSFER RESULT — MIXED / FAILED OVERALL — PROTECTED VALIDATION NOT EXPOSED — P15 FINAL HOLDOUT NOT EXPOSED**

P14 preregistration: `docs/phase11_p14_bounded_independent_rescue_preregistration.md`

P15 conditional final-holdout preregistration: `docs/phase11_p15_final_holdout_preregistration.md`

P14 was preregistered before any P14 evidence generation. P15 was also preregistered before P14 evidence generation and was explicitly conditional on a complete P14 transfer + protected-validation pass.

## Scientific lineage

Authoritative predecessor:

- P13 branch: `phase11-p13-severity-mondrian-conformal`
- P13 forensic head: `6a320ba85794a6aa9d597e30b7f206222f2f5ca8`

P14 branch:

- `phase11-p14-bounded-independent-rescue`
- preregistered scientific implementation frozen before P14 evidence exposure

P14 preserves the seven-frame nonrecursive P9/P13 primary continuity method and adds only a one-frame independent synthetic coarse rescue observation when the primary stack is unavailable. Rescue outputs never become primary anchors and are never recursively propagated.

## Partition freeze

Workflow:

- run: `31978541651`
- job: `95241608360`
- workflow/scientific-lineage head: `6002fe078910f35dc8b0fc3039720cdc52634a13`
- artifact: `phase11-p14-partition-freeze`
- artifact ID: `9271724570`
- artifact ZIP digest: `sha256:d7978971392621b63aca8df252ca054d22e7695d819e2efdd27d806c794e196b`
- `partition_freeze.json` SHA-256: `69744506d49868848990ac64de5cea20057946b2280b0fcfe0f3cf32c2038387`
- `manifest.json` SHA-256: `a804e1583a54b95bb26f18218f398cf7789b864f08078b675fa549870ff95192`

The workflow reran the P9 + P14 invariant suite (`10 passed`) and generated only fit + severity-partition evidence. Calibration, transfer, validation, and P15 holdout evidence did not exist at this stage.

Fit-frozen constants:

- lateral q99 velocity cap: `0.1102253257782198 m/frame`
- altitude q99 velocity cap: `0.14926026897246664 m/frame`
- lateral q95 innovation scale: `0.060891478321460794 m`
- altitude q95 innovation scale: `0.17789953050388296 m`

Partition rows / severity cutpoints:

| Group | Rows | Lower | Upper |
|---|---:|---:|---:|
| `base_output` | 9,353 | 0.236998 | 0.368071 |
| `continuity_h3` | 491 | 0.246889 | 0.369505 |
| `continuity_h45` | 460 | 0.189628 | 0.319239 |
| `continuity_h67` | 390 | 0.141761 | 0.301200 |
| `independent_coarse_rescue` | 785 | 0.242407 | 0.359384 |

All preregistered partition minima passed.

## Candidate freeze

Workflow:

- run: `31978605370`
- job: `95241762526`
- workflow head: `443140f37c5595f123d2118dcf165b8f9a573677`
- artifact: `phase11-p14-candidate-freeze`
- artifact ID: `9271746305`
- artifact ZIP digest: `sha256:1e61db34ac5b5a2ea632812c2c74abe22b715e80814673a24d36391214f9a194`
- `candidate_freeze.json` SHA-256: `9c58dcbb053dfd1e759e281e29346ae54acdadd83e5a8934a4296ee7ec3452fa`
- `manifest.json` SHA-256: `01a1c4a74065bed0a56536a869589db5be388ade7b267c52fcb610cc455c4a66`

Before calibration generation, the workflow verified:

1. the exact P14 scientific files remained unchanged from the preregistered scientific head;
2. P9 + P14 invariants still passed (`10 passed`);
3. the exact partition JSON digest matched the frozen artifact.

All 15 source/horizon x severity calibration cells passed their preregistered minima.

Calibration cell counts:

| Cell | Rows |
|---|---:|
| `base_output__low` | 4,207 |
| `base_output__mid` | 4,151 |
| `base_output__high` | 4,120 |
| `continuity_h3__low` | 213 |
| `continuity_h3__mid` | 231 |
| `continuity_h3__high` | 200 |
| `continuity_h45__low` | 201 |
| `continuity_h45__mid` | 204 |
| `continuity_h45__high` | 213 |
| `continuity_h67__low` | 168 |
| `continuity_h67__mid` | 182 |
| `continuity_h67__high` | 172 |
| `independent_coarse_rescue__low` | 323 |
| `independent_coarse_rescue__mid` | 395 |
| `independent_coarse_rescue__high` | 332 |

The exact candidate was frozen before transfer seed `737737` was generated.

## Seen transfer

Workflow:

- run: `31978732397`
- job: `95242071994`
- workflow head: `80b94a5a880109b7667a713cf5c67049636f2b7c`
- seen transfer seed: `737737` — **permanently seen**
- artifact: `phase11-p14-seen-transfer`
- artifact ID: `9271776849`
- artifact ZIP digest: `sha256:e34285304e88f0a7b9d32996f5d9cb85c093250e95ffcd1f413620f6a7d942f8`
- `transfer_result.json` SHA-256: `86cf39c7bc3f978ec6694e30e16a604ac18941e0868e2d48f6c5e54192781c91`
- `transfer_natural_diagnostic.json` SHA-256: `dede97a4b67c6f2f23029b99129b30f5a7221e8c593fe3d76525e3f7119b01ca`

The transfer workflow verified scientific-file immutability, reran the P9 + P14 invariants (`10 passed`), and verified the exact candidate JSON SHA-256 before exposing transfer.

## Preregistered seen-transfer gates

| Gate | Frozen result | Verdict |
|---|---:|---|
| H1 useful availability | **98.15%** | PASS (`>=92%`) |
| H2 lateral 95% coverage | **88.13%** | FAIL (`90–98%`) |
| H2 altitude 95% coverage | **86.61%** | FAIL (`90–98%`) |
| H3 calibration-curve MACE | **0.10292** | FAIL (`<=0.06`) |
| H4 lateral median half-width / p95 error | **0.487x** | PASS |
| H4 lateral p95 half-width / p95 error | **1.075x** | PASS |
| H4 altitude median half-width / p95 error | **0.604x** | PASS |
| H4 altitude p95 half-width / p95 error | **0.687x** | PASS |
| H5 primary-continuity lateral coverage | **79.79%** | FAIL |
| H5 primary-continuity altitude coverage | **76.20%** | FAIL |
| H5 lateral p95 width / error | **0.591x** | PASS component |
| H5 altitude p95 width / error | **0.566x** | PASS component |
| H6 base lateral coverage | **87.14%** | FAIL |
| H6 base altitude coverage | **86.41%** | FAIL |
| H6 lateral p95 width / error | **0.630x** | PASS component |
| H6 altitude p95 width / error | **0.591x** | PASS component |
| H7 severity AUROC | **1.000** | diagnostic PASS |
| H8 high-severity lateral coverage | **88.93%** | FAIL (`>=88%` passes lateral alone, but altitude fails) |
| H8 high-severity altitude coverage | **87.19%** | FAIL |
| H8 lateral p95 width / error | **1.037x** | PASS component |
| H8 altitude p95 width / error | **0.644x** | PASS component |
| H9 rescue lateral coverage | **94.91%** | PASS |
| H9 rescue altitude coverage | **93.39%** | PASS |
| H9 rescue lateral p95 width / error | **0.992x** | PASS |
| H9 rescue altitude p95 width / error | **0.929x** | PASS |
| H10 rescue lateral MAE | **0.0823 m** | PASS |
| H10 rescue altitude MAE | **0.1692 m** | PASS |
| H10 rescue lateral p95 error | **0.2089 m** | PASS |
| H10 rescue altitude p95 error | **0.4102 m** | PASS |
| H11 rescue recovery | **94.19%** (`2300 / 2442`) | PASS (`>=85%`) |

Overall preregistered verdict:

**MIXED / FAILED**

`all_primary_gates_pass = false`

`P14_VALIDATION_ELIGIBLE = false`

## Evaluation-cell power failure

The transfer split also failed its preregistered per-severity-cell minimums because fresh compounded shift pushed most evaluated rows into the high-severity regime.

Observed low-severity cells included:

- `base_output__low`: `62` vs required `120`
- `continuity_h3__low`: `10` vs required `20`
- `continuity_h45__low`: `3` vs required `15`
- `continuity_h67__low`: `0` vs required `10`
- `independent_coarse_rescue__low`: `15` vs required `20`

This gate was frozen before transfer and is not relaxed after seeing the distribution shift.

## What P14 establishes

### 1. The independent rescue mechanism solved the P13 availability bottleneck in this fresh transfer experiment

P13 seen-transfer availability was only `81.79%`. P14 reached `98.15%` while leaving the bounded seven-frame primary continuity path unchanged.

Among `2,442` truth-visible rows where the unchanged primary stack was unavailable, the independent rescue process recovered `2,300` (`94.19%`).

The rescue estimates were not arbitrarily noisy:

- lateral MAE `0.0823 m`, p95 `0.2089 m`;
- altitude MAE `0.1692 m`, p95 `0.4102 m`;
- rescue-only 95% coverage was `94.91%` lateral and `93.39%` altitude;
- rescue-only width/error efficiency also passed.

Thus P14 gives positive simulation evidence that an independent evidence source can restore availability without requiring the primary estimator to extrapolate beyond its frozen seven-frame boundary.

### 2. The uncertainty-transfer problem reappeared for the primary outputs under the harder fresh P14 composition distribution

The rescue group itself remained well calibrated, but the primary base and continuity groups undercovered substantially. Overall coverage fell below the locked target range and calibration MACE failed.

This result means P14 did **not** preserve the complete P13 calibration behavior under the new transfer distribution, despite successfully solving availability.

### 3. The fixed severity partition no longer produced balanced evaluation cells under the fresh compound shift

The transfer distribution concentrated heavily in high-severity cells. Several low-severity cells failed preregistered evaluation sample minima. That is a design/evidence-distribution finding, not a reason to pool cells after exposure.

## Exposure ledger

Permanently seen P14 evidence:

- fit seed `704704`;
- severity-partition seed `715715`;
- conformal-calibration seed `726726`;
- seen-transfer seed `737737`.

**NOT EXPOSED:**

- P14 protected-validation seed `748748`;
- P15 final-holdout seed `759759`.

Because P14 seen transfer failed preregistered primary gates and cell minimums:

- P14 protected validation is **not authorized**;
- P15 final holdout is **not authorized**;
- neither seed may be generated by this P14/P15 lineage.

The user's conditional P15 approval applied only if P14 first passed transfer and protected validation. That condition was not met.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
- no claim that any real auxiliary sensor matches the synthetic rescue process
- failed/mixed outcomes remain permanent evidence
- P14 transfer seed `737737` may never be presented as unseen evidence again
- P14 protected validation and P15 final holdout remain unexposed
