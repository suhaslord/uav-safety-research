# Real-image dataset track

## Dataset

**KIOS Aerial Landing Pad, Unreal Engine Dataset (2024)**  
Zenodo DOI: https://doi.org/10.5281/zenodo.13682584

The archive contains simulated landing-pad imagery plus a **422-image real-video subset** with YOLO-format landing-pad annotations. AegisLand uses only paths belonging to the real-video subset for the first real-image transfer test.

Raw dataset files are downloaded from Zenodo for evaluation and are **not committed to this repository**.

## Question

Does the existing synthetic `ThresholdPadEstimator` transfer at all to real landing-pad images **without tuning or retraining**?

This is intentionally a first transfer test, not a new trained model.

## Frozen baseline

The baseline is the existing threshold/brightness-weighted-centroid estimator from:

`src/uav_safety/image_perception.py`

For each real image:

1. convert to grayscale;
2. resize to the baseline's 96×96 input size;
3. run the unchanged estimator;
4. compare its predicted horizontal center with the annotated landing-pad box.

## Metrics

Because the frozen baseline outputs a horizontal position rather than a full detection box, this test reports:

- valid-estimate rate;
- normalized horizontal-center mean absolute error;
- normalized horizontal-center 95th-percentile error;
- fraction of predictions whose x-coordinate falls inside the annotated landing-pad box;
- mean confidence.

It does **not** report object-detection mAP because the current baseline does not output a bounding box.

## Evidence rule

The first real-image result is diagnostic. We do not tune the old estimator after seeing the result and then call that same data a clean test.

If the synthetic heuristic transfers poorly, the next stage will create a proper development/test split for a real-image detector or segmentation baseline, freeze that model, and only then evaluate robustness to blur, low light, occlusion, noise, and related distribution shifts on held-out real images.

## Reproduce

```bash
python scripts/download_kios_real_landing_dataset.py --accept-download --extract
python scripts/run_real_landing_pad_benchmark.py \
  --dataset-root data/external/kios_landing_pad/extracted \
  --path-contains real \
  --out results/real_landing_pad
```

The downloader verifies the published archive MD5 before evaluation.

## Citation

Soteriou, C., Kyrkou, C., & Kolios, P. S. (2024). *Aerial Landing Pad, Unreal Engine Dataset*. Zenodo. https://doi.org/10.5281/zenodo.13682584

The dataset accompanies *Closing the Sim-to-Real Gap: Enhancing Autonomous Precision Landing of UAVs with Detection-Informed Deep Reinforcement Learning* (DeLTA 2024).
