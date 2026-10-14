# Detector robustness: second-seed repeat and two-seed interpretation

**Research date:** 2026-10-13 PT / execution 2026-10-14 UTC  
**Project:** Existing AegisLand detector; **no new research phase**.  
**Decision:** Both runs passed an *exploratory development screen*. Preserve model candidates for offline research; **do not replace the frozen/published detector** without eligible independent camera evidence.

## Verified second execution

- [Second-seed GitHub Actions run 38514541463](https://github.com/suhaslord/uav-safety-research/actions/runs/38514541463): **SUCCESS**.
- [PR #207](https://github.com/suhaslord/uav-safety-research/pull/207) repeats the same experiment with **seed 20261014**, changing no other planned model/data or training settings.
- Both CI runs (38514541409 and 38514526698) passed.
- GitHub Actions artifact **11872036460**, `detector-photometric-repeat-seed-dev-pilot`, contains `comparison.json`, train-only data receipt, 12-epoch training CSVs and both actual `best.pt` checkpoints.
- The image count is **252 per arm** (baseline 252 original training frames, candidate 214 originals + 38 photometric train-only replacements: 13 blur, 13 low light, 12 noise). Validation is the same 64 original images in both arms; no 86-image protected test or real-flight execution.

## Development results for seed 20261014

All six stress conditions derive from the same **64 development frames**, so these are 384 dependent frame-conditions per model, **not independent datasets**.

| Condition | Baseline precision | Candidate precision | Baseline recall | Candidate recall | Baseline mAP50 | Candidate mAP50 | mAP50 gain |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Clean | 0.88636 | 0.86939 | 0.48754 | 0.73438 | 0.61955 | 0.83370 | +0.21416 |
| Blur | 0.75216 | 0.86901 | 0.42188 | 0.57812 | 0.49658 | 0.73392 | +0.23733 |
| Low light | 0.83141 | 0.86681 | 0.30834 | 0.67188 | 0.41754 | 0.82148 | +0.40393 |
| Noise | 0.96664 | 0.78828 | 0.45279 | 0.64062 | 0.55955 | 0.77331 | +0.21376 |
| Partial occlusion | 0.87844 | 0.83362 | 0.53125 | 0.76562 | 0.64963 | 0.86035 | +0.21071 |
| Mixed | 0.39285 | 0.67722 | 0.12500 | 0.48438 | 0.12164 | 0.54177 | +0.42014 |

Candidate improves development **mAP50 in all six conditions for this seed**, but precision **falls** in clean, noise, and partial occlusion. Equal-weight six-condition mAP50 delta **+0.28334**; all five fixed development-screen gates pass. This is a per-seed descriptive metric, **not a confidence interval or a safety rate**.

### Reproducibility identities

- SHA-verified historical temporal split: `32623634069c4f3082b79a6a42bca408c636f4b626e5f7691276257999544905`
- Augmentation receipt SHA-256: `fe3ac3dbb27238e00dc246e21aa55594eab28ec2f9c24753a65613cc5469f07b`
- Second-seed baseline `best.pt` SHA-256: `608dbc9fa65ba8b84ee46f24aa3134bfdacfc801717d69f2502e1e2f92ee0156`
- Second-seed photometric candidate `best.pt` SHA-256: `59070d8489ad7c3cab09f3ddd6003f0f78244f172146365519f1ffb7c9dca4cb`
- Both checkpoint digests were verified against the downloaded archived weight bytes.

## Two-seed comparison (do not cherry-pick)

The prior, otherwise identical seed **20261013** run is recorded at
[`detector_robustness_photometric_results_20261013.md`](detector_robustness_photometric_results_20261013.md)
and Actions run [38513371676](https://github.com/suhaslord/uav-safety-research/actions/runs/38513371676).

| Per-seed development mAP50 | First seed baseline | First seed candidate | Second seed baseline | Second seed candidate |
| --- | ---: | ---: | ---: | ---: |
| Clean | 0.50881 | 0.51815 | 0.61955 | 0.83370 |
| Blur | 0.44614 | 0.42636 | 0.49658 | 0.73392 |
| Low light | 0.43823 | 0.47701 | 0.41754 | 0.82148 |
| Noise | 0.44131 | 0.37599 | 0.55955 | 0.77331 |
| Partial occlusion | 0.51604 | 0.48998 | 0.64963 | 0.86035 |
| Mixed | 0.16829 | 0.29526 | 0.12164 | 0.54177 |

The **first** seed passed the pre-recorded development screen only narrowly;
blur, noise and occlusion mAP50 all regressed. The **second** seed passed much
more comfortably, and all six mAP50 values improved, but clean, noise and
occlusion precision were lower. The difference in candidate performance
between seeds is **large**. This is evidence of **optimizer/augmentation
seed sensitivity**, not proof of stable superiority or new independent-data
performance.

No independent session data was available, there are no verified
absent-pad negatives, and a developmental validation set was reused during
checkpoint selection. No inference on the historically protected KIOS test
is allowed for tuning this detector. No calibration threshold was selected.

**Next evidence needed:** additional planned fixed-seed checks and, more
importantly, genuinely independent physically captured camera sessions with
compatible target labels and verified negative frames under the unchanged
admission protocol. Until then both experiment checkpoints stay research-only,
the official original/frozen model remains untouched, and no universal
accuracy, aircraft-control, or flight-safety claim is warranted.
