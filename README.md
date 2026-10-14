# AegisLand

**Can a drone recognize when its landing-pad detection is wrong?**

A confidence-based check can reduce accepted wrong landing-pad locations on new camera data without rejecting nearly every detection.

AegisLand is a research project about **knowing when a camera prediction can be trusted**. The goal is not to make the detector look perfect; it is to see whether a simple accept-or-abstain check catches bad landing-pad locations **without rejecting almost everything**.

**Website:** https://aegisland-research-cockpit.vercel.app/  
**Short research summary:** [PROJECT_SHOWCASE.md](PROJECT_SHOWCASE.md)  
**Explore real-image failure cases:** [Failure Atlas](https://aegisland-research-cockpit.vercel.app/failure-atlas/)

## The finding that started it

In 86 reused test frames under occlusion, Phase 23 had a correct box somewhere in 43 views, but its top-confidence box was correct in only 23. These are **reused images from two videos**, not new independent test evidence. [See the measured diagnostic](docs/phase25_top_confidence_results_20261011.md).

## The experiment

**Detect → Check → Verify**

1. Run the existing frozen detector.
2. Use the highest detection confidence to accept or abstain; choose the threshold using separate development images only.
3. Test once on new independent camera sessions. Report both wrong accepted predictions **and** accepted coverage, compared with always trusting the top prediction.

**Current status: Independent camera validation is still pending.** Phase 26 has not admitted an independent real-camera dataset. Do not treat the earlier frame comparisons as proof of generalization. [Frozen protocol](docs/phase26_protocol.md) · [Admission report](docs/phase26_admission_report.json).

## Explore and reproduce

- [Phase 25 camera Failure Atlas](results/phase25_failure_atlas/summary.md) and [confidence diagnostic](docs/phase25_top_confidence_results_20261011.md)
- [Frozen Phase 26 score and threshold-selection code](scripts/phase26_reliability.py)
- [Reproduction guide](REPRODUCE.md)
- [Research question, hypothesis and limits](PROJECT_SHOWCASE.md)
- [Original experiments and negative results](EXPERIMENT_SUMMARY.md) · [archive on the website](https://aegisland-research-cockpit.vercel.app/phases/)

Run the repository's small claims check with `python scripts/audit_showcase_claims.py`. This checks archived counts and admission status; it **does not** rerun detector inference.

The simulation, Model VASE, and motor-fault studies remain available in the archive. They are separate supporting investigations, not evidence that this camera reliability rule has been validated.

**Research only; not a demonstrated flight-safety system.**
