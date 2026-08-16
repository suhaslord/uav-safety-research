# Phase 11 P12 frozen seen-transfer result — event-stratified rare-gap direct conformal

## Status

**FROZEN SEEN-TRANSFER RESULT — MIXED / FAILED OVERALL — PROTECTED VALIDATION NOT EXPOSED**

P12 preregistration: `docs/phase11_p12_event_stratified_direct_conformal_preregistration.md`

## Candidate freeze

Freeze workflow:

- run: `31977243560`
- scientific freeze head: `38dc3c661083b1a9e4b4ae4a839e6fecc27dca41`
- candidate artifact ID: `9271385056`
- candidate artifact digest: `sha256:19deda69542a98ce6c5b5ffd60ccdeebfebe6a4d40f6dae2a28514dbe737c8d0`
- `candidate_freeze.json` SHA-256: `b9a4526565c6697fbba9c0736c55a96f46fb815f8ea5d945314ac5bece86c9f2`
- `manifest.json` SHA-256: `242ced5890b6c692b6eb18bff2629ab636a84346abe18792b825cd5f67fc9cc6`

The freeze workflow passed all P9 + P12 invariant tests and generated only natural fit plus event-stratified grouped-calibration evidence. Transfer and validation were absent at freeze.

### Calibration power result

The P12 event-stratified design decisively solved the rare-group power problem:

| Group | Rows | P12 preregistered power minimum | Ratio |
|---|---:|---:|---:|
| `base_output` | 9,925 | 2,000 | 4.96x |
| `continuity_h3` | 608 | 240 | 2.53x |
| `continuity_h45` | 614 | 120 | 5.12x |
| `continuity_h67` | 305 | 60 | 5.08x |

Fit-frozen motion/reliability constants:

- lateral q99 velocity cap: `0.11068131383640177 m/frame`;
- altitude q99 velocity cap: `0.15810449600400786 m/frame`;
- lateral q95 innovation scale: `0.060113244043831095 m`;
- altitude q95 innovation scale: `0.17710602656554073 m`.

## Seen transfer

Transfer workflow:

- run: `31977294230`
- workflow head: `1a9685550ea40da0f4c14313db2b3ee3855efe30`
- seen transfer seed: `605605` — now permanently seen
- transfer artifact ID: `9271399986`
- transfer artifact digest: `sha256:73d0886a3f72858fbfb909ef976089c4951965f38e0377602ba3aab8068da8ff`
- `transfer_result.json` SHA-256: `fc65da16455b516afea55746962d7e3a6c5c98c59dc0523927d965363758c5de`
- `transfer_natural_diagnostic.json` SHA-256: `76bfb17ff6a68971d28ba08c83d6c561efa3dda086beee09a257a70d2e53305b`

Before transfer exposure, the workflow verified:

1. the exact frozen P12 scientific files were unchanged from the freeze head;
2. all P9 + P12 invariant tests still passed (`9 passed`);
3. the exact candidate JSON matched SHA-256 `b9a4526565c6697fbba9c0736c55a96f46fb815f8ea5d945314ac5bece86c9f2`.

## Seen-transfer power

All event-study transfer power margins passed strongly:

| Group | Rows | Preregistered P12 transfer minimum | Ratio |
|---|---:|---:|---:|
| `base_output` | 4,315 | 1,200 | 3.60x |
| `continuity_h3` | 449 | 150 | 2.99x |
| `continuity_h45` | 466 | 75 | 6.21x |
| `continuity_h67` | 247 | 30 | 8.23x |

The original P9 transfer minimums also all passed.

## Preregistered seen-transfer gates

| Gate | Frozen result | Verdict |
|---|---:|---|
| H1 useful availability | `95.09%` | PASS |
| H2 lateral 95% coverage | `85.50%` | FAIL |
| H2 altitude 95% coverage | `84.79%` | FAIL |
| H3 calibration-curve MACE | `0.18446` | FAIL |
| H4 lateral median half-width / p95 error | `0.378x` | PASS |
| H4 lateral p95 half-width / p95 error | `1.069x` | PASS |
| H4 altitude median half-width / p95 error | `0.480x` | PASS |
| H4 altitude p95 half-width / p95 error | `0.749x` | PASS |
| H5 continuity lateral 95% coverage | `87.61%` | FAIL (`>=88%` required) |
| H5 continuity altitude 95% coverage | `81.50%` | FAIL |
| H5 continuity lateral p95 width / error | `0.875x` | PASS component |
| H5 continuity altitude p95 width / error | `0.690x` | PASS component |
| H6 base lateral 95% coverage | `84.94%` | FAIL |
| H6 base altitude 95% coverage | `85.68%` | FAIL |
| H6 base lateral p95 width / error | `0.519x` | PASS component |
| H6 base altitude p95 width / error | `0.522x` | PASS component |
| H7 trajectory shift AUROC | `0.9989` | diagnostic PASS |

Overall preregistered verdict: **MIXED / FAILED**.

`all_primary_gates_pass = false`

`P12_VALIDATION_ELIGIBLE = false`

## Interpretation

P12 separates two previously confounded questions.

### 1. Rare-event calibration power is solved

P9, P10, and P11 could not reliably populate all horizon groups by scaling random trajectory families. P12's truth-independent 3/5/7-frame outage intervention produced hundreds of examples in every continuity bucket without lowering thresholds, pooling away the h6-7 regime, cherry-picking rows, or using truth/error to schedule events.

### 2. The fixed four-group direct-conformal method does not transfer across compositional severity shift

Once power was no longer the bottleneck, the frozen uncertainty method undercovered decisively on fresh transfer compositions. The intervals were not too wide: H4 efficiency passed comfortably. They were **too narrow for the shifted residual distribution**.

The failure was not continuity-only. Base outputs also undercovered (`84.94%` lateral / `85.68%` altitude), while continuity was worse, especially altitude (`81.50%`). Therefore horizon/source grouping alone is insufficient to describe the transfer change.

At the same time, trajectory-level inherited severity separated calibration-regime and transfer-regime trajectories almost perfectly (`AUROC = 0.9989`). This suggests that an inference-visible shift/severity variable contains information the fixed group-only conformal radii currently ignore.

This is descriptive motivation only. P12 transfer seed `605605` may not be used to choose, fit, or tune a later severity transformation, cutpoint, coefficient, group rule, or threshold.

## Exposure ledger

Permanently seen P12 evidence:

- fit seed `583583`;
- event-stratified calibration seed `594594`;
- seen-transfer seed `605605`.

Protected validation seed `616616` is **NOT EXPOSED** and is retired with P12 because the transfer gates failed.

No P12 protected-validation workflow may be run.

## Next scientific boundary

P13 must use entirely fresh seeds/families and preregister before generation.

A principled P13 direction is to retain P12's event-stratified rare-gap study design and the P9 soft continuity estimator, but let direct conformal uncertainty condition on a **predeclared inference-visible severity regime** in addition to source/horizon.

P13 must avoid returning to the stacked learned-scale/correction/multiplier architecture that made P8 intervals excessively conservative. Candidate designs should remain simple and auditable, such as a fixed low/medium/high Mondrian severity partition with cutpoints frozen from fresh calibration evidence only, or a fixed analytic monotone severity normalization followed by direct conformal calibration.

Protected validation and any final Phase 11 holdout remain unauthorized until a future exact candidate freeze satisfies the preregistered development gates and the user separately approves final-holdout exposure.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
- event-stratified and natural-stream evidence must not be conflated
- failed/mixed outcomes remain permanent evidence
