# AegisLand — research in one page

**Question:** Can a vision system recognize when its landing-pad localization is unreliable under image degradation, *before* a downstream system relies on that localization?

**Working hypothesis (not yet externally validated):** On new, independently captured landing-pad imagery, a rule that accepts or abstains using only a frozen detector's confidence score can reduce the fraction of accepted localizations that are incorrect compared with accepting every top-ranked prediction, without abandoning useful coverage.

The research is not "make a drone land safely." It is a measurable **perception reliability** question. A bounding-box confidence value is not a probability of a safe landing, and abstention is not a tested flight-control intervention.

## Why I started investigating this

A detector may produce a correct candidate but still rank a wrong candidate as its most confident. On the already-used KIOS landing-pad images, our read-only Phase 25 diagnostic found **135 model/view instances** where the existing any-match success metric passed but the **top-confidence** box was incorrect (88 for the original baseline and 47 for Phase 23). There are 86 original frames reused across six image conditions and two detectors; only **two original video sessions**. These 135 are dependent comparisons, not independent incidents.

That finding motivates a different question from simply improving mAP: **when should an image estimate be withheld rather than trusted?** It does not establish that a new confidence threshold works.

[Inspect the full per-condition evidence](docs/phase25_top_confidence_results_20261011.md) · [Reproduce the hashed retrospective audit](docs/phase25_top_confidence_diagnostic.md)

## What the proposed method actually does

1. Keep the original detector and its frozen preprocessing/NMS settings.
2. Take its highest-confidence landing-target prediction, or score zero if none exists. **Do not use ground-truth labels in this score.**
3. On a separate *development* collection only, use the previously specified 0.05–0.95 grid to pick one positive accept/abstain threshold maximizing coverage subject to a development accepted-error rate no higher than 5%. If none qualifies, abstain on all images and report that the development gate failed.
4. Lock the code, model, threshold, inputs, and session identities. On a disjoint, sealed *evaluation* collection, report accepted localization error, coverage, rejected correct detections, empty-target false accepts and per-session results. Do not tune after inspecting the evaluation.
5. Compare against always accepting the top prediction. Report the tradeoff rather than selecting the most flattering number.

This is the existing [Phase 26 protocol](docs/phase26_protocol.md) and [candidate-specific rule](docs/phase26_imav2025_preregistration.md), **not a new preregistration** or permission to reuse Phase 25 test images for threshold selection.

## Where the evidence stands

| Claim | Evidence | Honest status |
| --- | --- | --- |
| Detector failure patterns change across blur, darkness, occlusion, and mixed perturbations | [Phase 25 paired record](results/phase25_failure_atlas/paired_analysis_summary.json) and [failure analysis](results/phase25_failure_atlas/paired_study_report.md) | Retrospective, dependent image views |
| The highest-confidence box can be wrong despite any-match success | [Top-confidence diagnostic](docs/phase25_top_confidence_results_20261011.md) | Observed on previously used frames; not an independent performance estimate |
| A simple accept/abstain score and development selection implementation exist | [Phase 26 rule](scripts/phase26_reliability.py) and [development lock](scripts/freeze_phase26_development_rule.py) | Implemented, not externally validated |
| A new holdout proves improved localization reliability | [Dataset admission](docs/phase26_admission_report.json) | **NOT YET. No independent dataset admitted.** |
| Model VASE improves real UAV landing safety | [Model VASE architecture](docs/model_vase.md) | **NOT CLAIMED**: not demonstrated end-to-end on a physical aircraft |

The motor-fault H1/H2 experiments and pending H3 PX4/Gazebo study are a separate fault-diagnosis track. They do not validate this primary perception-reliability hypothesis.

## What would make this a strong, showable research result?

**The critical missing experiment is a clean external test**, not another website redesign or a new threshold on old images.

- **Acquire:** new, licensed, independently recorded *real-camera* sessions of a compatible physical landing target, including frames where no target is visible. Preserve original images, source session IDs and annotations. No user needs to fly a drone to reproduce this work: published or appropriately shared, provenance-verifiable recordings are acceptable.
- **Audit:** check against all 422 KIOS real images and between development/test for hashes, near-duplicates, capture sessions, label semantics and permission. If this fails, document the rejection, not a fabricated test.
- **Freeze:** run the existing development-only score and threshold selection, save its input/configuration hashes and chosen threshold, and do not change either on the new test.
- **Test once:** export complete per-image results and a session-level comparison of coverage and accepted errors against always-accept. Report failures and insufficient session counts without invented confidence bounds.
- **Explain visually:** show one verifiable false-high-confidence example, its annotation and detection boxes, then a small risk-versus-coverage comparison. Label each example as retrospective or independent.

### Evidence that anyone can check

Run this standard-library command from the repository root:

~~~bash
python scripts/audit_showcase_claims.py
~~~

It validates the committed paired counts/rates and the independent-data admission status, and prints a machine-readable claim snapshot. It **does not** claim to reproduce model inference or the separate top-confidence audit.

## The one-minute explanation

"I was looking at why a drone vision system can be confident about the wrong landing-pad location. I audited the same frames under different corruptions and found examples where a detection metric said the frame was successful even though the highest-confidence box was wrong. Now I'm building a fail-closed reliability check and designing a completely separate, session-held-out test to see whether it rejects those errors without rejecting everything. The independent test hasn't been completed yet."

**Resume-safe description today:** Independent UAV landing-perception research; built reproducible, checksum-audited evaluation pipelines for detector behavior under image degradation and identified a mismatch between any-match detection success and top-confidence localization on retrospective real-camera views.

Do not claim a published paper, a validated flight-safety system, an independently confirmed 5% error rate, or a trained end-to-end Model VASE without evidence.

### Prior research

- Geifman & El-Yaniv, *Selective Classification for Deep Neural Networks* (NeurIPS 2017): https://arxiv.org/abs/1705.08500 — the coverage/error tradeoff of rejecting uncertain predictions.
- Ovadia et al., *Can You Trust Your Model's Uncertainty?* (NeurIPS 2019): https://papers.neurips.cc/paper_files/paper/2019/hash/8558cb408c1d76621371888657d2eb1d-Abstract.html — uncertainty estimates under distribution shift.

These are context and precedents, **not** claims that AegisLand reproduces their experimental methods or guarantees.
