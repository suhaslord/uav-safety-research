# Original-model research revalidation — 2026-10-03

## What was actually executed

Research continued in the integrated checkout at `040f790ef3cc5b6e568d1e8078d02de8bf171fe7`. The older August audit/UI fixes were committed separately at `cc30cb260866b3690b0b3656aa69f3bbcce979f9`; that commit and the old UI were not merged into this research checkout.

The original Phase 23 checkpoint and recovery ZIP were found locally. No alternative model was trained, substituted or relabeled. Their SHA-256 hashes are:

- Original checkpoint: `43240be969708c32b3e11340c9846b3a588baf361378398677c794d16a455310` (5,444,698 bytes).
- Recovery ZIP: `a55531930988deeadf81853d00b63c7e589c6b7fd2270f57653abdb5cdd3e55d`.
- Published result commit: `7677bacdae1f3a3b73f9473f5fa51f2059d9525a`.

The five identifiers in the recovered inference lock matched the running interpreter: Python **3.13.2**, Ultralytics **8.4.160**, Torch **2.7.0+cu118**, NumPy **2.2.3**, Pillow **11.0.0**. Phase 23 used CUDA device 0, 480 px, confidence floor 0.001, NMS IoU 0.7, maximum 300 detections, batch 16 and two workers. The baseline retained its separate 320 px CPU settings.

This identifies the recovered lock and successful replay, not proof that every original transitive package or hardware detail was recovered. Supplemental versions observed in this replay were torchvision 0.22.0+cu118, OpenCV 5.0.0.93, SciPy 1.18.1, pandas 3.0.3 and matplotlib 3.11.1; CUDA 11.8, cuDNN 90100 and an RTX 4060. These supplemental observations must not be described as independently authenticated original training-environment records.

A broad unit test initially triggered an Ultralytics optional-package auto-install that attempted to change Pillow and left its installation incomplete. Pillow **11.0.0** was restored, auto-install was disabled, and the accepted replay was rerun in the verified pinned environment. The accepted receipt is from that second run. Unit tests now disable auto-install before collection so malformed-image fixtures cannot mutate scientific dependencies.

## Data identity and aggregate reproduction

The exact official KIOS archive hash is `9d27a3e9616c188fb72a727633705735da5df168ce47efeed389dcb3455fdbdb`. The protected manifest hash is `8605cf1cbf9e8769c0324bf066078f9964f232ac3128131c8bd0b689bb7b64b7`.

The fail-closed input gate verified **1,204 data files**, the 86 protected frames (66 `land_pad`, 20 `land_pad2`), labels, both original checkpoints, all six reconstructed image inventories and the source archive. These are **516 reused KIOS views**, not independent observations or a new holdout.

`scripts/run_phase25_frame_audit.py` first reran the published aggregate checks for both models, before exporting predictions. All **24 Phase 23 aggregate metric cells matched exactly**, with maximum absolute delta **0.0**. Fresh inference then generated 1,032 model/frame/condition rows. All four raw prediction tables are byte-identical to the already retained Phase 25 tables. No historical numerical artifacts needed replacement.

The verifiable receipt is [`replay_receipt.json`](../results/research_revalidation_2026_10_03/replay_receipt.json). The raw originals remain under [`results/phase25_failure_atlas/`](../results/phase25_failure_atlas/).

## Paired outcomes: two different questions

The model-to-model comparison reproduces **49 recovered, 65 regressed, 223 both-pass and 179 both-fail** cases across 516 views. It compares the baseline and Phase 23 on the same condition/view.

The newly generated [`paired_clean_vs_stressed.csv`](../results/research_revalidation_2026_10_03/paired_clean_vs_stressed.csv) instead compares **each model against its own clean view** for five nonclean conditions: 86 frames × 5 stresses × 2 models = **860 pairs**. These must not be conflated with the 516 cross-model transitions. All pairs use the frozen IoU matching and inference floor, with no threshold selection from test outcomes.

Frame success means all annotated targets are matched at IoU ≥ 0.50; false positives are counted separately. It is not official evaluator recall at the evaluator's operating point, and it is not safe-landing success. The baseline generated 136,359 predictions and Phase 23 generated 71,420 at the low confidence floor; many are unmatched. UI display filtering never changes scoring.

## Controlled occlusion: provenance and research answer

The **ten recovered research files** were checked byte-for-byte against only [`f090da03d20b2425c5addccb4d19117c8991bcc1`](https://github.com/suhaslord/uav-safety-research/commit/f090da03d20b2425c5addccb4d19117c8991bcc1). No old branch/UI was merged. The recovered publication implementation is qualified: the lost earlier implementation-freeze/runtime receipt was not recovered.

The original raw-source attempt remains **INCONCLUSIVE — CLEAN GATE FAILED — NO TREATMENT INFERENCE RUN**. It supplies no treatment-performance curve. The separately versioned Q95-representation v2 follow-up has an actual inference freeze at `6a8623cbeb54951f43b8ca65293598e7c41a474e`, its own recorded Linux/CPU runtime and passing clean gate. That runtime is not relabeled as the Phase 23 CUDA runtime.

Offline replay verified v2's **145,169 saved predictions**, 516 frame rows, 516 target rows and paired descriptive statistics. No new controlled-occlusion detector inference was performed in this session. The new research summary/figure are derived from those authenticated saved detections, not fabricated or newly tuned model outputs.

- **Change with measured occlusion:** mean achieved annotation-box occlusion spans 0 to about 74.6%. Frame recall changes from 53/86 (**61.6%**) to 48/86 (**55.8%**). Mean all-target best-overlap confidence falls from **0.312** to **0.065**, and mean best IoU from **0.609** to **0.554**.
- **Where failures begin:** 33/86 frames already fail at zero added occlusion. Among the 53 initially successful frames, the first sampled new loss occurs for two frames at requested dose 0.15, three at 0.30 and two at 0.75. Forty-six have no sampled new loss; one frame recovers after an earlier loss. This is a descriptive first-observed-loss record, not a preregistered deployment threshold.
- **Gradual or threshold-like:** confidence/localization degrade across doses; recall is modestly and nonmonotonically lower (including a small recovery at dose 0.45). These six points do not establish an abrupt universal breakpoint. The recovered protocol specified no threshold criterion, so none is invented after inspecting outcomes.
- **Vulnerable scenes/objects:** only the `landing_pad` class is represented. `land_pad` falls from 33/66 to 28/66 matched frames; `land_pad2` retains 20/20 at every sampled dose. These are scene/sequence-specific observations, not an independently identified causal object-size effect or a claim about other object classes.

Outputs: [`controlled_occlusion/`](../results/research_revalidation_2026_10_03/controlled_occlusion/), including per-frame losses, per-sequence curves, an authenticated-source analysis record and a real-data figure. Visibility refers to annotation-box pixels, not physical pad surface area. Two dependent sequences do not support population-level significance or flight-safety claims.

## Phase 26 is a separate prospective gate

No independent dataset has been admitted. KIOS 2022 overlaps the KIOS lineage; residual KIOS frames share the two capture sessions. IMAV remains missing its usable candidate images/annotations, file manifest, capture-session provenance, ontology/annotation review, negative-frame inventory and rights documentation.

The historical protocols remain unchanged. [`phase26_admission_execution_lock.json`](phase26_admission_execution_lock.json) freezes the **next-candidate execution** and eight protocol/method hashes. It explicitly resolves the existing distance mismatch: the archived protocol requires dHash separation ≥ 10, so the generic screening CLI must be called with **`--near-distance 9`**, rejecting distances ≤ 9 rather than its weaker default ≤ 8. The wrapper rejects that weaker screen. A screening pass is still not admission or permission for test inference.

The admission lock requires independent campaign/session lineage, zero byte/pixel/name/near overlap against all 422 authenticated KIOS real frames, whole-session dev/test partitioning, compatible annotated targets, verified negatives, rights review and a committed input lock. Development-only rule selection uses the existing fixed grid and 5% accepted-error objective. No test outcomes may be opened before the rule and sealed-test manifest are committed. With fewer than five independent sessions, results are descriptive only.

## Portability and release scope

A current, nonhistorical atomic-write helper now handles Windows' lack of POSIX directory fsync: file bytes are still fsynced and atomically replaced, but POSIX directory-entry crash durability is not claimed. Exact frozen method bytes stay archived. The f090da03 runner/tests were not edited; a separate test-only adapter normalizes paths in generated Windows fixtures.

Failure Atlas now displays **real per-frame Phase 23 metrics and boxes**, with the same rendering-only subset policy as the baseline, instead of a pending/aggregate-only panel. Model VASE copy no longer describes input-resolution specialization as a demonstrated causal mechanism. The numerical evidence remains tied to its original model and protocol.

Final local maintenance checks passed **560 Python tests**, plus desktop/mobile Chrome checks of 48 displayed Phase 23 cases against the generated tables, paired real source images, overlay toggles and keyboard controls. No JavaScript exceptions or HTTP errors were captured. Source images were served from the previously verified external reconstruction workspace; this was not a production deployment test. The mechanical image warnings refer to deliberately hidden, dynamically sourced image elements, not invented image content.

The actual Model VASE simulation replay reproduced **10,000 episode rows, 20 summary rows and five paired-effect rows**. Maximum observed numeric differences were `3.55e-15`, `1.11e-16` and `7.11e-15`, within the frozen `1e-13` parity tolerance; categorical outcomes matched exactly. See [`model_vase_parity.txt`](../results/research_revalidation_2026_10_03/model_vase_parity.txt). This does not rerun every later Monte Carlo phase.

The software/citation candidate version is **1.0.0rc1**. [`frozen_manifest.json`](../results/research_revalidation_2026_10_03/frozen_manifest.json) binds the retained/generated artifact family and current method/copy bytes. It is an exact-byte snapshot, not a digital signature; the read-only validator separately authenticates recovered source against Git and replays saved matching/paired statistics.

This prepares a **scoped retrospective research release candidate**, not a tagged v1.0, independent validation, detector-to-controller validation or flight certification. See [REPRODUCE.md](../REPRODUCE.md) and the [detector report](../paper/detector_revalidation_report.md). Original imagery/model rights and version-specific citations remain separate from the repository's MIT software license.
