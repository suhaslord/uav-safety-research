# AegisLand

**UAV landing-perception research: synthetic tests first, then real-image transfer.**

[![CI](https://github.com/suhaslord/uav-safety-research/actions/workflows/ci.yml/badge.svg)](https://github.com/suhaslord/uav-safety-research/actions/workflows/ci.yml)
[![Real dataset](https://img.shields.io/badge/real%20dataset-422%20frames-2563eb)](https://doi.org/10.5281/zenodo.13682584)

[Research cockpit](https://aegisland-research-cockpit.vercel.app/) · [Real-data protocol](docs/real_dataset_track.md) · [Experiment archive](https://aegisland-research-cockpit.vercel.app/phases/)

AegisLand asks: **when landing perception becomes unreliable, can the system recognize that before it trusts a bad estimate?**

## Real-image dataset

The current perception track uses the **KIOS Aerial Landing Pad, Unreal Engine Dataset (2024)** and evaluates its **422-image real-video subset** with YOLO landing-pad annotations.

- **Source:** [Zenodo DOI 10.5281/zenodo.13682584](https://doi.org/10.5281/zenodo.13682584)
- **Real images used:** 422
- **Annotations:** YOLO bounding boxes
- **First test:** run the existing synthetic estimator unchanged — no retraining or tuning

Raw dataset files are downloaded from Zenodo for evaluation and are not copied into this repository or website.

## First real-image result

| Metric | Result |
| --- | ---: |
| Images evaluated | **422** |
| Valid estimate rate | **76.8%** |
| Horizontal-center MAE | **0.2176 image widths** |
| Horizontal-center P95 error | **0.5146 image widths** |
| Predicted x inside annotated pad box | **30.6%** |
| Mean confidence | **0.520** |

**Result:** the old threshold-centroid heuristic **does not transfer well to real images**. It returned no valid estimate on about 23% of frames, and only about 31% of valid predictions fell horizontally inside the annotated landing-pad box.

That negative result is useful: the synthetic benchmark was too simple to stand in for real camera imagery. The next perception baseline should be built on real images with a protected evaluation split instead of tuning the old heuristic on these same 422 frames.

Full result: [`results/real_landing_pad/summary.md`](results/real_landing_pad/summary.md)

## Pipeline

```text
real camera image → perception model → estimate + confidence → safety supervisor → landing decision
```

For every block, AegisLand documents **input → operation → output → next handoff** before adding more complexity.

## Current baseline

The first transfer test deliberately kept the Phase 5 estimator frozen. It is **rule-based, not a neural network**: it thresholds bright pixels and uses a brightness-weighted horizontal centroid.

Because it predicts only horizontal position, this first transfer test reports horizontal-center error — **not object-detection mAP**.

Implementation: [`src/uav_safety/real_landing_dataset.py`](src/uav_safety/real_landing_dataset.py)

## Earlier synthetic benchmark

Phase 5 used 1,500 generated **96×96 grayscale** images across clean, blur, low light, occlusion, and mixed conditions. That benchmark was useful as a controlled sanity check, but the real-image transfer result shows why it cannot be treated as real-world validation.

<details>
<summary>Show the old synthetic inputs</summary>

<table>
  <tr><th>Clean</th><th>Blur</th><th>Low light</th><th>Occlusion</th><th>Mixed</th></tr>
  <tr>
    <td><img src="docs/assets/readme/dataset/clean.png" width="120" alt="Synthetic clean input"></td>
    <td><img src="docs/assets/readme/dataset/blur.png" width="120" alt="Synthetic blurred input"></td>
    <td><img src="docs/assets/readme/dataset/low_light.png" width="120" alt="Synthetic low-light input"></td>
    <td><img src="docs/assets/readme/dataset/occlusion.png" width="120" alt="Synthetic occluded input"></td>
    <td><img src="docs/assets/readme/dataset/mixed.png" width="120" alt="Synthetic mixed-degradation input"></td>
  </tr>
</table>

</details>

## Reproduce the real-image test

```bash
git clone https://github.com/suhaslord/uav-safety-research.git
cd uav-safety-research
python -m pip install -e ".[dev]"
python scripts/download_kios_real_landing_dataset.py --accept-download --extract
python scripts/run_real_landing_pad_benchmark.py \
  --dataset-root data/external/kios_landing_pad/extracted \
  --path-contains real \
  --out results/real_landing_pad
```

The downloader verifies the published dataset archive checksum before evaluation.

## Next research step

Do **not** tune the old heuristic on the same real frames and call that a clean result. Next:

1. define a real-image development/test split;
2. build a proper landing-pad detector or segmenter on the development data;
3. freeze it;
4. evaluate held-out real-image performance;
5. then apply controlled blur, low light, occlusion, and noise to test real-image distribution shift.

## Research record

The earlier simulation research remains preserved through Phase 22, including failed phases rather than rewriting them after later experiments succeed.

[Project guide](docs/project_understanding_guide.md) · [Block map](docs/block_reference_map.md) · [Methodology](docs/methodology.md) · [Reproducibility](docs/reproducibility.md)

## Scope

AegisLand is still research software. The real-data result is a perception-transfer benchmark; it does **not** establish physical-flight safety, certification, or production readiness.
