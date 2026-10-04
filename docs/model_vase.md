# Model VASE — unified AegisLand research system

**VASE** means **Vision, Auxiliary evidence, State reliability, Escalation**.
Model VASE is AegisLand's versioned system architecture for answering one
question:

> **When landing perception becomes unreliable, can the system recognize that
> before it trusts a bad estimate?**

## What the model does

Model VASE gives the research program one system architecture and one evidence
map. The components do **not** share a single learned checkpoint, and their
reported metrics are not pooled. The architecture connects the research
components through explicit evidence roles and future data handoffs:

1. **Vision:** an image estimator supplies a state estimate or target detection.
2. **Auxiliary evidence:** an independent, imperfect estimate can expose
   persistent disagreement that one visual stream cannot see by itself.
3. **State reliability:** temporal consistency, confidence, uncertainty, and
   estimate freshness describe which parts of the state remain usable.
4. **Escalation:** the supervisory layer combines the available evidence and
   chooses `PROCEED`, `HOLD`, or `ABORT` in the simulation.
5. **Evidence record:** input hashes, frozen rules, paired outcomes, and
   external-trace checks bound what the reported result means.

The executable safety-decision path currently implemented in Model VASE is a
thin orchestration wrapper around the frozen V3 fusion and supervisor in
`src/uav_safety/model_vase.py`. The simulator
still supplies the same observation streams in the same order. The wrapper
does not fit a new model, change a threshold, draw random numbers, or alter V3's
fusion and decision equations. The test suite checks direct-call parity, and
the full frozen V3 episode table is reproduced before release. The parity
check requires episode outcomes and paired transitions to match exactly;
continuous measurements allow only `1e-13` relative/absolute tolerance for
last-bit runtime rounding.

Run `python scripts/verify_model_vase_parity.py` from an editable installation to replay all
10,000 frozen episodes and compare the episode table, summaries, and paired
effects. Pass `--replay-dir PATH` to verify an already generated run.

## Evidence map

| Evidence block | Frozen result | What it contributes to Model VASE |
|---|---|---|
| Phases 1–5, V1–V3 | Static risk thresholds reduced some unsafe touchdowns by aborting too often. V2 restored availability but mixed-condition unsafe touchdowns remained 84.0%. V3 reduced the mixed rate to 2.4% (97.6% success, 0% abort); under occlusion it reduced unsafe touchdowns from 34.6% to 1.4%. | Direct simulation evidence that a noisy independent estimate and persistent disagreement can add information beyond confidence thresholding or single-stream temporal smoothing. |
| Phase 6 / 6B | In the frozen synthetic-image landing evaluation, Phase 6B achieved 99% success and 1% unsafe touchdowns under mixed degradation; low-light success was 97% with 3% timeouts. Its separate frame audit showed weak rejection of bad mixed-condition lateral estimates. | Image-to-controller integration evidence; keeps the cost of component-selective fallback visible. |
| Phases 7–9 | Stronger-plant development exposed sensitivity. The frozen PX4/Gazebo comparison was `diagnostic_mismatch`. A genuine camera trace was collected as seen external-perception evidence. | External checks identify simulator-to-simulator and perception gaps. They do not validate the safety supervisor on an aircraft. |
| Phase 10R | Partial-view mean geometry error improved, while the protected run failed its tail-efficiency, availability, and uncertainty-coverage gates. | A concrete warning that lower average error does not guarantee reliable tails or calibrated uncertainty after shift. |
| Phase 11 | Transfer passed, but protected validation failed the lateral p95 interval-width gate (`2.435×` versus `2.25×`); final holdout was not exposed. | Preserves an honest failure in uncertainty efficiency under distribution shift. |
| Phase 12 | The frozen adaptive-normalized conformal candidate passed its registered simulation gates through final replication, including lateral 95% coverage of `95.53%` and the p95 width/error ratio of `2.230×`. | A positive result for state-uncertainty estimation in its defined simulation lineage. It has not been connected to the V3 landing decision path. |
| Phase 22 | The frozen simulation transfer study passed all 10 locked gates. | Supports the bounded transfer claim in that simulation protocol; it is not physical-flight evidence. |
| Phases 23–24 | On the KIOS real-image split, macro mAP50 rose by 3.4 points, while the equal-weight occlusion + mixed average fell by 13.3 points. | Real-image detector evidence shows where the visual front end remains weak. It does not measure a landing response. |
| Phase 25 | On 86 protected frames × 6 conditions (516 paired views), the authenticated Phase 23 checkpoint produced 49 recovered, 65 regressed, 223 both-pass, and 179 both-fail frame transitions. Blur and noise improved (+9.3 pp and +3.5 pp recall); clean, low-light, and occlusion regressed (−8.1 pp, −12.8 pp, −11.6 pp). A fresh original-runtime replay reproduced all 24 aggregate metric cells exactly and all four prediction tables byte-for-byte. | Authenticated retrospective outcomes, not a demonstrated causal explanation of the training/resolution tradeoff. |
| Phase 26 | KIOS 2022 archive rejected (100% byte-duplicate overlap). KIOS 2024 residual real frames rejected (same two sessions, cross-split collision). IMAV 2025 candidate blocked pending images, manifest, and provenance. No independent evaluation set has been admitted. | The admission gate is preserved; the next candidate must supply session-level provenance and pass zero-overlap screening. |

These rows are complementary studies, not a meta-analysis or a single joint
evaluation. The detailed phase pages retain the frozen denominators, protocols,
and failures.

Full source reports, protocols, manifests, and known failures are linked in the
[research archive](README.md) and the [phase archive](https://aegisland-research-cockpit.vercel.app/phases/).

## Current answer to the research question

**Within the defined planar simulations, the evidence supports a conditional
yes.**
The strongest direct result is V3: adding a noisy independent state estimate
and checking persistent disagreement sharply reduced unsafe mixed and
occlusion touchdowns without relying on a high abort rate. Phase 6B provides a
separate synthetic-image integration result with similar gains in the hardest
conditions, plus a measurable low-light completion cost and weak
mixed-lateral frame rejection.

**Across real-camera imagery and physical flight, the question remains open.**
The recovered Phase 23 detector's paired study records 65 regressed views
versus 49 recovered views, with condition-specific tradeoffs. A separate
860-row table pairs each model's clean and stressed views. These are distinct
comparisons: model-to-model regressions do not establish a causal training or
input-resolution mechanism. Controlled occlusion reveals gradual confidence
loss and a modest nonmonotonic recall decline in its frozen baseline study;
it does not establish a universal failure threshold. Phase 8 found a mismatch against
the available PX4/Gazebo trace; and Phase 26 has no admitted independent test
set. The evidence does not establish a validated real-world fallback or
flight safety.

## Why the historical numbers stay fixed

Model VASE is the integration layer for the research record. Each reported
number remains attached to its original frozen model, dataset, protocol, and
evidence role. V3's wrapper must reproduce the committed V3 episode rows; Phase
6B remains a different synthetic-image evaluation; Phase 12 remains an
uncertainty study; and Phases 23–25 remain a separate real-image detector
track. A future end-to-end composition that feeds the KIOS detector or Phase
12 intervals into the landing supervisor would be a new Model VASE version and
would require a preregistered paired evaluation before it could claim combined
performance.

Latest replay, controlled-occlusion answers and independence boundaries:
[research revalidation](research_revalidation_2026_10_03.md). The ten recovered
controlled-occlusion source files are authenticated only against
`f090da03d20b2425c5addccb4d19117c8991bcc1`; the separately frozen v2 inference
is not relabeled as the failed historical attempt.

## Scope and next test

Model VASE is research software evaluated in simulation and retrospective
image benchmarks. It is not a flight controller approval, safety certification,
or real-aircraft validation.

The Phase 23 checkpoint has been recovered and authenticated. Offline feasibility
analysis of candidate reliability signals from the Phase 25 evidence (`scripts/analyze_vase_signals.py`)
identified a retrospective scale-conditioned confidence signal (AUROC 0.8111 overall, 0.7390 severe).
However, controlled ablation (`scripts/ablate_vase_signals.py`) revealed that this improvement
is driven by ground-truth annotation area (`target_area_ratio`, scale-only AUROC 0.8369).
Because ground-truth bounding box area is unavailable at runtime and predicted boxes collapse
during severe detection failures, this signal does not survive ablation as a viable runtime
supervisory signal. Evaluating signal selection on the holdout test set also represents a post-hoc
analysis that cannot substitute for validation on a distinct split.

The next scientific test remains the admission of genuinely separate, session-screened data under
Phase 26's frozen protocol, followed by runtime-feasible signal formulation and evaluation on a
dedicated validation split. Only after those gates should an end-to-end detector-to-supervisor
composition be evaluated as a new version.
