# AegisLand — Phase 25 top-confidence localization diagnostic (2026-10-11)

**Status:** Completed, hash-verified, retrospective descriptive audit. **This is not a new independent test, a threshold selection, or flight-safety evidence.**

**Main question:** When landing perception is unreliable, can the system recognize that *before trusting a bad estimate*?

## Result: a correct box may exist while the most confident box is wrong

This analysis compares the preexisting Phase 25 `frame_success` outcome (every annotation matched by **some** detection) with the localization of the **highest-confidence landing-target prediction** (top candidate IoU ≥ 0.50). The decision to select that top prediction is made without reading ground truth. A wrong top prediction is incorrect even if a less-confident detection would have matched the pad.

The underlying data are the frozen **86 real KIOS frames**, each reused in six clean/stressed conditions and compared with two original detectors. That gives 1,032 model/view rows but only **two original video sessions**, not 1,032 independent measurements. This is failure diagnosis on reused protected material, never a new held-out test.

| Condition | Baseline any correct | Baseline top correct | Phase 23 any correct | Phase 23 top correct |
| --- | ---: | ---: | ---: | ---: |
| Clean | 53/86 | 35/86 | 46/86 | 45/86 |
| Blur | 45/86 | 36/86 | 53/86 | 51/86 |
| Low light | 49/86 | 36/86 | 38/86 | 38/86 |
| Noise | 45/86 | 39/86 | 48/86 | 46/86 |
| **Occlusion** | **53/86** | **33/86** | **43/86** | **23/86** |
| **Mixed** | **43/86** | **21/86** | **44/86** | **22/86** |

Across all dependent views, **135 instances** were already classed as successful under the previous any-match metric but had an **incorrect highest-confidence detection**: 88 baseline and 47 Phase 23. These are repeated view-level discrepancies, not 135 independent incidents.

### An especially important warning about confidence scores

For Phase 23 **occlusion**, the illustrative 0.50 score cutoff would accept just **2 of 86 views, and both top detections would be wrong**. For Phase 23 **mixed stress**, the illustrative 0.25 cutoff accepts **zero** views. The fact that a high score can still be wrong in some already-tested scenes, and that aggressive rejection can eliminate almost all coverage, shows why detector confidence **cannot be treated as a calibrated safe-landing probability**.

Those cutoffs were computed **only for descriptive illustration** from an already used protected set. **No threshold was selected**. They must not be reused as a tuned Phase 26 rule or claimed to generalize. The Phase 26 preregistered 0.05–0.95 grid and development-only selection logic remain untouched.

## Reproduction and input provenance

- [Read-only calculation source](../scripts/diagnose_phase25_top_confidence.py).
- [Focused tests](../tests/test_phase25_top_confidence_diagnostic.py), including top-confidence versus any-match disagreement and zero-area, boundary-clipped false positives.
- [Successful CI run](https://github.com/suhaslord/uav-safety-research/actions/runs/38112934701), Python 3.12.15, checkout commit `890dc28a1adbe2f97cef11c5dce64b9ed49638e4`.
- [Archived outputs](https://github.com/suhaslord/uav-safety-research/actions/runs/38112934701/artifacts/11691644582) (GitHub Actions artifact; 90-day retention): `summary.json`, all 1,032 `top_prediction_outcomes.csv` rows, Python version and checkout commit.
- The script verifies the **byte-for-byte SHA-256** of the four Phase 25 input tables against `run_manifest.json`, with the original 86/6/2 inventory and table/target/prediction counts. It does not alter historical frozen files or run inference. The saved artifact was separately inspected and all twelve model-condition rows reconciled.

## What this proves — and what it doesn't

**Supported:** On the *previously used* KIOS image views, old frame-success counts can materially overstate whether the most confident detection itself localizes the landing pad. Under occlusion and mixed stress, this discrepancy is large for Phase 23. The read-only diagnostic is reproducible on the frozen source tables.

**Not supported:** A reliable threshold, newly calibrated confidence, safe-to-proceed decision, end-to-end Model VASE improvement, real-flight performance, generalization across sites/videos/cameras, or false acceptance on scenes without pads. The dataset has only two source videos; all frames contain labeled targets; no statistically independent trial inference is claimed.

**Next decision gate:** Phase 26 must admit a *separately captured* real-image source with annotation quality, capture-session provenance, negative frames, KIOS-compatibility, owner permission, and zero duplicate/near-duplicate contamination. Choose the reliability rule on **development data only**, then test sealed independent sessions once. Until then: **NO_DATASET_ADMITTED**.

The separate H1/H2 motor-fault experiments do not answer AegisLand's landing-perception research question and do not contribute evidence to this diagnostic.
