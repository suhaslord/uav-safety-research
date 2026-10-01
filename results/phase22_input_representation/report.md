# PHASE 22 INPUT REPRESENTATION + OCCLUSION V2 STUDY

**Stage A: PASS. Stage B: BLOCKED — original frozen protocol unavailable.**

## Original sweep

Original sweep: **INCONCLUSIVE — CLEAN CONTROL GATE FAILED — NO TREATMENT INFERENCE RUN**. This reported stopping result remains unchanged. The original frozen protocol and result files were unavailable in this checkout, so their preservation is by leaving existing files untouched and retaining the supplied status; this report does not authenticate absent original artifacts.

- Original gate: **FAILED**, as reported in the assignment and prior execution transcript.
- Original reported raw-source mAP50: approximately **0.423908**.
- New RAW_SOURCE measurement: **0.42390766686341674**.
- Historical baseline mAP50: **0.42662686781189296**.
- Reproduced raw discrepancy: **−0.002719200948476219**, exceeding the original 0.001 tolerance.
- No treatment comparisons with the original sweep are possible: it produced no treatment predictions.

## Stage A observed measurements

Exactly 86 authenticated source frames × five frozen representations = **430 cases**. The checkpoint is authenticated from the Phase 22 recovery release. Input images and labels match the archive-derived reconstruction lock; Q95 matches the historical clean inventory byte for byte. All transforms were repeated before inference and rechecked against the frozen manifest before evaluation.

| Representation | Precision | Recall | mAP50 | mAP50–95 | Successful frames |
|---|---:|---:|---:|---:|---:|
| RAW_SOURCE | 0.773365822 | 0.383720930 | 0.423907667 | 0.271462222 | 51/86 |
| HISTORICAL_Q95 | 0.795971366 | 0.383720930 | 0.426626868 | 0.272343156 | 51/86 |
| Q90 | 0.739938052 | 0.383720930 | 0.425284774 | 0.272964416 | 49/86 |
| Q100 | 0.777191612 | 0.383720930 | 0.424334425 | 0.272777950 | 51/86 |
| LOSSLESS_PNG | 0.773365822 | 0.383720930 | 0.423907667 | 0.271462222 | 51/86 |

Precision and recall above are the official evaluator metrics at its F1 operating point. Frame success and TP/FP/FN use the fixed 0.001 prediction floor with class-aware, confidence-ranked one-to-one IoU ≥ 0.5 matching. All ground-truth boxes must match for success; extra false positives do not invalidate this flag. At that low floor, both RAW_SOURCE and Q95 have TP=51 and FN=35, corresponding to 0.593023256 frame recall. These are different metric definitions, not interchangeable recall estimates.

| RAW_SOURCE → HISTORICAL_Q95 transition | Frames |
|---|---:|
| Raw fails / Q95 passes | 0 |
| Raw passes / Q95 fails | 0 |
| Both pass | 51 |
| Both fail | 35 |

Q95 reproduces all four historical clean aggregate cells with **zero numerical delta**. Its mAP50 exceeds raw by **0.002719200948476219** (0.271920095 percentage points). There are no primary binary outcome flips at the declared frame matching rule. Raw and lossless PNG have identical decoded RGB pixels, identical aggregate metrics, and **all 25,058 saved prediction rows match exactly**. PNG therefore supplies a pixel-preserving format control. Q90 and Q100 are descriptive secondary comparisons; no representation or threshold was selected for performance.

Q95 mean decoded pixel MAE is **0.134085968** and mean per-frame RMSE is **0.452177029**, on the 0–255 channel scale. Its aggregate file size increases by 19,035 bytes across the 86 frames. Raw and PNG have zero decoded pixel error. Per-frame MAE, RMSE, finite PSNR where applicable, subsampling, dimensions, file sizes, and byte hashes are in the representation manifest. PSNR is null for identical pixels, where its mathematical value is infinite.

## Paired statistics

Exact two-sided McNemar/binomial p = **1.0** with **zero discordant pairs**. This supplies no binary-outcome difference evidence and does not establish model equivalence. Paired percentile bootstrap uses 10,000 resamples of 86 source frame IDs, seed **20260930**. Representations stay paired within each resample.

| Difference, Q95 minus raw | Mean | Source-frame bootstrap 95% interval |
|---|---:|---:|
| Frame success | 0.000000000 | [0.000000000, 0.000000000] |
| Best IoU | -0.000117411 | [-0.002012158, 0.001650300] |
| Best-any confidence | -0.000087567 | [-0.000553743, 0.000380860] |
| Matched confidence, both-pass subset | -0.000059304 | [-0.000587288, 0.000446945] |
| FP per frame | -0.093023256 | [-0.395348837, 0.209302326] |

Matched confidence uses the 51 frames that pass in both representations; failures are not converted into matched-confidence zeros. For unconditional best-any confidence only, absent predictions are defined as zero. TP and FN differences are exactly zero for the primary comparison; FP totals change from 25,007 to 24,999. Many low-confidence predictions reach the locked max_det cap. These low-floor counts are diagnostics, not deployment precision estimates.

Descriptive Spearman association between per-frame Q95 pixel RMSE and absolute prediction change: best IoU **-0.302892**, best-any confidence **-0.621378**. No mechanism or significance claim is made from these associations.

## Interpretation

The locked detector pipeline is sensitive to the decoded pixel representation. Historical Q95 reproduces the reference, whereas the original pixels reproduce the raw-source discrepancy. Under this pipeline and population, this representation change accounts for the clean-control discrepancy. The pixel-preserving PNG control leaves predictions unchanged. The measurements do not demonstrate a specific learned JPEG-compression mechanism, a general benefit of Q95, or a new occlusion response.

## Stage B readiness and execution chain

- Stage A gate: **PASS** (all five prerequisites true).
- Stage B protocol: **NOT CREATED — original frozen protocol missing**.
- Stage B protocol SHA: **not available**.
- Stage B zero-dose gate: **NOT RUN**.
- Treatment inference: **NOT RUN**.
- Dose levels: **not authenticated; not inferred from the 516-case count or transcript range**.
- Primary occlusion result: **not measured**.
- Success / recall / IoU / confidence by dose: **not measured**.
- Threshold evidence: **NOT ASSESSED**. No gradual-versus-threshold classification was selected after seeing these representation results.
- Dose-completeness and centered-mask geometry tests: **not applicable yet; Stage B inputs have not been generated**.

Original chain: raw source → reported clean-gate failure → no treatments. New chain completed here: verified sources → frozen representation transforms → Stage A clean comparisons → eligibility PASS. The separate v2 protocol and zero-dose gate remain outstanding. A Stage A clean result is not relabeled as a Stage B gate.

**Required to continue:** recover the complete original protocol file (reported shortened SHA `e169e16e…1882d7`) and its centered-mask implementation/frozen method record. Read the dose array directly from that protocol, authenticate it, then freeze a separate v2 protocol with explicit canonical-Q95 → mask → lossless treatment serialization order, matching rules, failure conditions, and threshold criterion before any treatment inference. A summary describing six doses over 0–75% is insufficient to meet the assignment.

## Artifacts and reproducibility

- `protocol.json`: committed before inference at `9dd9293`; SHA **bd653fe22f90b2bf941909c5f96ceeeb9aab7f75dda0e58bbc9d7d785b4122bf**.
- `representation_manifest.csv`: 430 source/representation records with derived hashes and pixel differences.
- `frame_metrics.csv`: 430 actual evaluated frame records.
- `raw_predictions.csv`: **125,208** exported predictions from the official evaluator passes.
- `aggregate_metrics.json`: all five official metric sets.
- `paired_representation_analysis.json`: transitions, count changes, paired statistics, and uncertainty limits.
- `stage_a_gate.json`: five passing prerequisites.
- `analysis_summary.json`, `stage_b_readiness.json`: measured summary and explicit Stage B blocker.
- `run_manifest.json`, `provenance.json`, `artifact_replay.json`: runtime, hashes, release provenance, and replay scope.
- `docs/phase22_representation_study.md`: preparation and execution commands.
- `scripts/verify_phase22_representation_artifacts.py`: offline replay of saved boxes, matching, frame metrics, paired statistics, and recorded gate; no detector run.

Offline replay passed for all **430 frames** and **125,208 predictions**. Protocol/method/output hashes are checked; original source and label hashes, runtime, deterministic reconstruction, and checkpoint were verified before detector inference. Final test and historical release-check results are recorded separately in `verification.json`. The final result commit follows the pre-inference freeze; Git history supplies its exact SHA.

## Limitations

Only 86 frames from two temporally dependent videos; this is a retrospective follow-up on an already examined holdout. Frame bootstrap intervals condition on these sources and do not account for independent-session uncertainty. Codec/library/runtime choices are frozen for this result and may affect another environment. The detector is static, bounding-box visibility is only a proxy, synthetic centered masks remain untested in v2, and these results have no direct closed-loop flight-safety equivalence. No original protocol/result was rewritten, no Phase 23 topology study was copied, and no merge or deployment was performed.
