# Phase 10R P0 — frozen Phase 10 holdout forensics

## Evidence role and boundary

**Evidence role:** `phase10_holdout_seen_forensics`

This document is a **read-only, post-hoc forensic analysis** of the already-exposed frozen Phase 10 holdout. It is not development evidence for Phase 10R. The five misses, their image geometry, residuals, and every descriptor below are permanently considered **seen historical evidence**.

No detector threshold, ArUco parameter, fallback rule, temporal gate, calibration value, model architecture, evaluation stratum, or challenge-set inclusion rule may be selected from these frames.

## Frozen source

- workflow run: `31565714654`
- artifact: `9129527772` — `phase10-gazebo-camera-holdout`
- artifact digest: `sha256:ca47dd023ebb295c7318d5907ad725a88d3721c8f6d855d4490af9b77c7ee88d`
- workflow head SHA: `5bd6be00a9f81d144170cb7950091518f54f83e7`

The forensic script verifies these frozen file hashes before producing descriptive output:

- `phase10/per_frame.csv` — `bac965f30dd249d271fb7faf3f8c2fc68bd6598957811ebe08eb51714af11486`
- `phase10/result.json` — `4a8c3cecc505e136260e9652a6fe937881b6cda1504cf2379d8fa7dc4aad94d6`
- `phase10/result_manifest.json` — `6549c3aa5b5da147775b1fc2916c219370b4c15b0a59c715f372ecc3fcffe2c7`
- `analysis/detection_details.csv` — `b6cb34f65b75bca54845fee70918db062381bbb4f86b9fa2cca829837ad07283`
- `analysis/perception_trace.csv` — `4a65b0c0ea50375213cd113b303d8745f8bb62200fcdafc85bfa3608a4162786`
- `capture/capture_frames.csv` — `9b259fb35100c64e7ea8ab8a800cd311450317e2bf032d42b7e95e1bdd829f8a`
- `px4_gazebo_raw.ulg` — `e919444c087aa68d2d307b5ef18b78d2af73c2500886c65b0a627be21c0db3ce`
- `px4_mission_metadata.json` — `f107ae18bdc9efe0ae0c1e76f2e3c1176583bed4087f1570e2d9254a18cfc09c`

All independently recomputed hashes matched.

## Frozen result recap

The holdout contained:

- 65 analyzed raw frames;
- 20 truth-visible frames;
- 15 Phase 9 front-end observations when truth-visible;
- 15 Phase 10 metric estimates when truth-visible;
- 5 truth-visible misses;
- 0 false-positive observations;
- all 15 usable holdout detections were ArUco updates.

On the 15 usable ArUco observations, Phase 9 was already at centimeter-scale point geometry, and AegisT10 retained those point estimates:

- lateral MAE: **0.0277246 m**;
- lateral p95: **0.0558810 m**;
- altitude MAE: **0.0157325 m**;
- altitude p95: **0.0292881 m**.

The preregistered Phase 10 substantial point-error win gate therefore did **not** pass.

Uncertainty honesty improved substantially:

- Phase 9 median `|lateral residual| / sigma`: **13.1672**;
- Phase 9 median `|altitude residual| / sigma`: **5.10565**;
- Phase 10 median normalized lateral residual: **0.646205**;
- Phase 10 median normalized altitude residual: **0.520930**;
- Phase 10 lateral 2-sigma coverage: **93.33%**;
- Phase 10 altitude 2-sigma coverage: **100%**.

The result remains simulation-only with `safety_acceptance = false` and `controller_tuning_allowed = false`.

## Truth-visible miss forensics

The 20 truth-visible frame indices are:

`27, 28, 29, 30, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47`

The five misses are:

`27, 35, 36, 46, 47`

For descriptive geometry only, P0 computes:

`edge_margin_ratio = nearest image-edge distance from truth center / (sqrt(truth projected area) / 2)`

This is **not a detector threshold** and must not become one.

| frame | observation | altitude (m) | projected area (px²) | edge-margin ratio | descriptive category |
|---:|:---:|---:|---:|---:|---|
| 27 | miss | 0.293 | 923176.9 | 0.631 | truth footprint likely intersects image boundary; very near-field / extreme scale |
| 35 | miss | 2.198 | 199881.1 | 0.024 | truth footprint likely intersects image boundary |
| 36 | miss | 2.339 | 134231.8 | 1.111 | near-boundary geometry |
| 46 | miss | 2.874 | 80555.6 | 0.480 | truth footprint likely intersects image boundary |
| 47 | miss | 2.335 | 160489.8 | 0.051 | truth footprint likely intersects image boundary |

Descriptive summary:

- **4 of 5** misses have `edge_margin_ratio < 1.0`;
- the fifth miss is still near-boundary at `1.111`;
- median detected-visible edge-margin ratio: **2.656**;
- median missed-visible edge-margin ratio: **0.480**;
- median detected-visible projected area: **52,591 px²**;
- median missed-visible projected area: **134,232 px²**.

A simple crop-intensity check does **not** establish a unique photometric failure cause: median crop intensity standard deviation was about **90.83** for detected visible frames and **90.56** for misses. P0 therefore does not claim lighting or contrast as the causal mechanism.

## Interpretation

The existing holdout gives a strong reason to make **availability under edge / partial-view geometry** a Phase 10R development target. It does **not** support selecting a new threshold, changing ArUco parameters, adding a rescue rule, choosing a model, or choosing evaluation boundaries based on these five frames.

The proper next step is to preregister physical/rendering challenge conditions first, then generate new development and trajectory-held-out validation evidence independently of detector outcomes.

## P0 integrity statement

- frozen result changed: **no**
- detector/model/calibration tuning performed: **no**
- old holdout used for model selection: **no**
- old holdout status for Phase 10R: **permanently seen historical evidence**
