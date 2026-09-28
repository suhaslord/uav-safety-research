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

Run `PYTHONPATH=src:. python3 scripts/verify_model_vase_parity.py` to replay all
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
| Phase 25 | The Phase 22 detector baseline was audited on 86 reused frames × 6 reconstructed conditions. The exact Phase 23 checkpoint/runtime remains unavailable, so paired per-frame transitions remain pending. | Makes baseline image failures inspectable while protecting the comparison from invented Phase 23 predictions. |
| Phase 26 | No independent evaluation set or frozen reliability rule has been admitted yet. | Defines the next evidence needed to test whether these patterns transfer to separate imagery. |

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
The KIOS detector's occlusion and mixed-stress metrics regress; the Phase 23
checkpoint is missing for paired frame outcomes; Phase 8 found a mismatch
against the available PX4/Gazebo trace; and Phase 26 has no admitted independent
test set. The evidence does not establish a validated real-world fallback or
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

## Scope and next test

Model VASE is research software evaluated in simulation and retrospective
image benchmarks. It is not a flight controller approval, safety certification,
or real-aircraft validation.

The next scientific test is to recover and reconcile the exact Phase 23 model
and runtime, then admit genuinely separate, session-screened data under Phase
26's frozen protocol. Only after those gates should an end-to-end detector-to-
supervisor composition be evaluated as a new version.
