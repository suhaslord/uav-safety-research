# AegisLand

**Research question:** Can a drone recognize when its landing-pad detection is wrong?

**Hypothesis:** A confidence-based check can reduce accepted wrong landing-pad locations on new camera data without rejecting nearly every detection.

**Goal:** Know when to trust a landing-pad detection and when to hold it back.

## Why this matters

A camera can sound confident and still point to the wrong landing pad. In 86 reused test frames under occlusion, Phase 23 had a correct box somewhere in 43 views, but its top-confidence box was correct in only 23. These were previously studied images from only two source videos, **not** independent proof that a solution works.

## What I am testing

1. **Detect:** Run a frozen landing-pad detector on an image.
2. **Check:** Use its top score to accept the result or abstain. Select the threshold only on new development images.
3. **Verify:** On completely separate, never-tested camera sessions, measure **wrong accepted detections AND how many useful detections remain**. A filter that rejects everything is not a success.

Independent camera validation is still pending. The [existing Phase 26 protocol](docs/phase26_protocol.md) and [candidate admission rules](docs/phase26_imav2025_preregistration.md) control the actual experiment; this page is a simple explanation, **not a new protocol**.

## Working prototype

[Try the offline camera reliability check](https://aegisland-research-cockpit.vercel.app/prototype/). It plays back authentic **previously tested** detector outputs. The confidence score determines ACCEPT or ABSTAIN without reading an annotation; the annotation is shown after the decision for explanation. The cutoff slider is **illustrative only**, not a tuned or validated threshold. The new-camera experiment remains pending.

## Evidence so far

- [Phase 25 top-confidence audit](docs/phase25_top_confidence_results_20261011.md): the most confident box is sometimes wrong even if another box is correct. Retrospective analysis, not a new independent test.
- [Failure Atlas](https://aegisland-research-cockpit.vercel.app/failure-atlas/): explore paired clean and stressed camera views.
- [Source-based claim audit](scripts/audit_showcase_claims.py): verifies historical paired counts and reports that no independent external dataset is admitted.
- [Full methods and limitations](docs/showcase_validation_checklist_2026_10_13.md): what an external validation must contain.

**Coverage** means the fraction of eligible images for which the rule accepts a result; it must be reported beside the wrong-accepted-result rate so abstaining on everything cannot look successful.

**Not claimed:** a tested flight-safety system, an end-to-end landing controller, or proof of generalization to a new camera.

**Other engineering work** (including simulation and motor-fault studies) remains in the [research archive](https://aegisland-research-cockpit.vercel.app/phases/). It is supporting work, not proof of the camera-reliability hypothesis.

## Explain it in one sentence

**I'm studying how a drone camera can recognize when its landing-pad prediction might be wrong instead of confidently trusting a bad estimate.**
