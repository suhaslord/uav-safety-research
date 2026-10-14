# AegisLand showcase validation checklist — 2026-10-13

**This is a communication and execution plan, not an amendment to any frozen protocol.** Follow [Phase 26](phase26_protocol.md), [IMAV candidate specification](phase26_imav2025_preregistration.md), and the existing admission-gate scripts exactly. Historical and externally tested findings must never be mixed.

## A research claim in four lines

**Problem:** Wrong localization may be assigned high detector confidence; any-match detection metrics miss this downstream top-candidate risk.

**Research question:** On independently captured, session-disjoint real images, can confidence-based abstention decrease accepted wrong landing-pad localizations while retaining useful acceptance?

**Hypothesis:** A prediction-only accept/abstain rule chosen on separate development sessions will reject a useful subset of incorrect top-ranked detections when assessed once on independent test sessions; whether it does is unknown.

**Null/negative result:** The test could show no reduction in accepted error compared with always-accept, zero useful acceptance, or a tradeoff so severe that the method provides no practical benefit. Report any of those outcomes prominently.

## Target outcome and evaluation

- Input: highest-confidence post-NMS landing-target score from the frozen model, or zero if there is no prediction.
- Rule output: ACCEPT or ABSTAIN using only that score and the locked threshold, never test labels.
- Ground-truth evaluation: the selected top box matches a reviewed physical landing target at IoU >= 0.50; any accepted wrong or spurious top box is an accepted error.
- Primary report: accepted erroneous localizations / accepted images **together with** acceptance coverage = accepted images / all eligible images. Always show numerator and denominator, plus a baseline that accepts all top predictions and counts missing predictions as incorrect localization.
- Secondary report: false acceptance on negative images, correct detections rejected, per-condition and per-independent-session counts, risk/coverage curve *descriptively* if generated without tuning on test.
- Use the locked development 5% selection criterion from the existing Phase 26 specification; do not call it a population-level guarantee. No more than one threshold or post-hoc cherry-picked operating point.
- Units of statistical independence: **capture sessions**. An array of heavily correlated frames is not a sample of independent flights; with too few sessions, present descriptive counts only.
- Keep an explicit status flag: development audit, admitted independent test, or not admitted. No pilot/airworthiness/safety claim.

## Concrete work order and hard gates

| Priority | Deliverable | Pass criteria | Current state |
| --- | --- | --- | --- |
| 1 | External real-image source and original capture records | Permission/license, compatible labeled landing pad, negatives, true session/video identifiers | BLOCKED — no admitted collection |
| 2 | Admission and contamination audit | All 422 original KIOS frames screened; no shared session or unresolved near-duplicate, no fake source IDs | Existing tools, candidate not admitted |
| 3 | Frozen model + dev outcomes | Model/runtime/checkpoint provenance; scores calculated without labels; complete reviewed dev correctness file | Procedure exists; fresh dev data absent |
| 4 | Frozen threshold receipt | Existing development grid and 5% selection rule, code/data digests before test | Selection code exists; no new result |
| 5 | Blind held-out evaluation | Exactly one sealed evaluation; baseline and filter coverage/error with complete per-image outputs and independent-session summaries | Not run |
| 6 | Short scientific paper/poster | Abstract, question, falsifiable hypothesis, methods, evidence figures, negative findings, limits, reproducibility | Outline ready; external conclusion pending |
| 7 | Visual demonstration | Historical incorrect-top-box example clearly labeled, then *separately* held-out comparison after admission | Phase 25 atlas exists; new result absent |

**Don't substitute PX4/Gazebo H3 motor-fault results for the perception result.** The motor-fault investigation has a different input, label, system and hypothesis. A resume can mention it as a secondary project, but mixing it into this primary experiment would obscure what was actually tested.

## Suggested figure layout for a poster (only after valid data)

1. Diagram: camera image → frozen detector → maximum-score box → confidence gate → ACCEPT/ABSTAIN. Ground truth is used offline only to score correctness.
2. Retrospective case study: existing image, annotations and scored boxes; large label "previously inspected Phase 25".
3. Two-panel results: coverage versus accepted-error rate, plus negative-frame false accepts; session/group inventory in caption.
4. "Failure modes" panel: strong-confidence wrong boxes, rejected correct boxes, empty-target errors, unseen target appearance.
5. Provenance panel: code commit, model hash, original image/manifests and splits.

If no dataset passes admission, write a candid methods/negative-findings poster instead. Do not make up a success plot.

## Reviewer questions to be prepared for

**"What did you personally change?"** Show commits, the top-box diagnostic, reproducibility code, selection logic and dataset-screening work; identify any collaborators accurately.

**"Why isn't this just a YOLO project?"** Explain why detection success and confidence-ranked candidate correctness differ, and the independent evaluation of whether abstention improves usable localization.

**"What if you never find new images?"** Then this is a retrospective failure analysis with an incomplete proposed external validation, not a validated generalization result.

**"What did you learn?"** Model confidence is not necessarily localization correctness, test-frame reuse inflates evidence, and an apparent reduction in errors can hide unusably low coverage.

## Publish gate

Before changing a resume claim from "studied / audited / built" to "demonstrated that a reliability rule generalizes," require a published, hash-audited admitted dataset manifest, frozen dev threshold, untouched test receipt, complete error/coverage table, and a readable limitations section. None may be replaced by a passing unit-test badge.
