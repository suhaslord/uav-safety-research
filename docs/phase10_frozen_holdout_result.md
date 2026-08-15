# Phase 10 — Frozen Gazebo Camera Holdout Result

Status: **frozen holdout complete**

Evidence role: `phase10_holdout_unseen`

Frozen implementation SHA: `fb928d5b0d1fbee7459d55120d5fd6b232a4f2c6`

Freeze/evidence SHA: `5bd6be00a9f81d144170cb7950091518f54f83e7`

Workflow run: `31565714654` — success

Artifact: `phase10-gazebo-camera-holdout`

Artifact ID: `9129527772`

Artifact digest: `sha256:ca47dd023ebb295c7318d5907ad725a88d3721c8f6d855d4490af9b77c7ee88d`

## Result in one sentence

AegisT10 **did not beat the Phase 9 point-estimation baseline on the frozen holdout**, because all 15 usable observations were already high-quality ArUco detections for which the Phase 9 geometry was highly accurate; AegisT10 matched those point estimates while substantially improving the honesty of the uncertainty representation.

This is a valid negative/mixed Phase 10 result. The model and thresholds are not retuned after seeing it.

## Frozen holdout evidence

The predeclared `phase10_frozen_holdout_trajectory_v1` completed in PX4 v1.17.0 + Gazebo using `gz_x500_mono_cam_down` in the `aruco` world.

The new trajectory contained 11 fixed segments with different north/east offsets, altitude ordering, direction changes and yaw from the development trace.

The captured evidence contained:

- 65 raw camera frames with hashes verified
- 20 truth-visible frames under the unchanged Phase 9 visibility definition
- 15 front-end observations on truth-visible frames
- 5 missed visible frames
- 0 false-positive observations
- detector mix on accepted observations: **15 ArUco / 0 quad fallback**
- front-end missed-detection rate when visible: **25%**

The first Phase 10 holdout varies trajectory/view geometry while retaining the same pinned Gazebo world. It is not a lighting/world-domain-shift evaluation.

## Paired Phase 9 vs AegisT10 result

The Phase 9 front end and AegisT10 were evaluated on exactly the same holdout rows.

| Metric | Phase 9 | Simple causal smoothing | AegisT10 | Reduction vs Phase 9 |
|---|---:|---:|---:|---:|
| lateral MAE | **0.0277 m** | 0.2851 m | **0.0277 m** | ~0% |
| altitude MAE | **0.0157 m** | 0.1417 m | **0.0157 m** | 0% |
| lateral p95 abs. error | **0.0559 m** | 0.4688 m | **0.0559 m** | 0% |
| altitude p95 abs. error | **0.0293 m** | 0.2982 m | **0.0293 m** | 0% |

AegisT10 preserved 15/15 metric estimates on frames where the Phase 9 front end produced an observation, so there was no metric-availability loss and no false-positive regression.

## Why the large development gain did not reproduce

The already-seen Phase 9 development trace contained 18 ArUco measurements and 7 quad-fallback measurements. Those fallback measurements dominated the multi-meter Phase 9 metric errors, so AegisT10's temporal rejection/prediction logic produced a very large development gain.

The frozen holdout produced **no accepted quad-fallback observations at all**. Every available metric measurement was ArUco. On this subset the Phase 9 single-frame geometry was already at centimeter-scale error, and AegisT10's frozen configuration intentionally applies the ArUco geometry directly. Therefore the point estimates are numerically the same.

This means the holdout did not support the hypothesis that AegisT10 substantially reduces paired metric error. It also did not expose the fallback-geometry failure mode that motivated the temporal estimator.

## Uncertainty result

The uncertainty result is more positive.

The unchanged Phase 9 front end remained strongly overconfident on this holdout:

- median `|lateral residual| / sigma`: **13.17**
- median `|altitude residual| / sigma`: **5.11**

Using the development-frozen Phase 10 calibration, AegisT10 produced:

- median normalized lateral residual: **0.646**
- median normalized altitude residual: **0.521**
- lateral 1-sigma coverage: **60.0%**
- lateral 2-sigma coverage: **93.3%**
- altitude 1-sigma coverage: **93.3%**
- altitude 2-sigma coverage: **100%**

So Phase 10's calibrated uncertainty generalized much better than the Phase 9 reprojection-derived uncertainty proxy on this holdout, even though its point estimate did not improve.

## Predeclared substantial-win gate

The full Phase 10 minimum gate was **not passed**.

Passed:

- metric availability drop <=2 percentage points
- no false-positive regression
- median normalized lateral residual <2
- median normalized altitude residual <2

Failed:

- >=50% lateral MAE reduction
- >=50% altitude MAE reduction
- >=35% lateral p95 reduction
- >=35% altitude p95 reduction

The failure is preserved. No Phase 10 parameter was changed after the holdout was exposed.

## Interpretation

Phase 10 established three useful things:

1. The catastrophic geometry failure seen in Phase 9 development was concentrated in ambiguous fallback geometry rather than ordinary ArUco detections.
2. On a new trajectory containing only accepted ArUco measurements, the original single-frame Phase 9 PnP geometry was already very accurate, so temporal filtering had no point-estimation advantage to recover.
3. Development-only source-aware uncertainty calibration generalized substantially better than the original reprojection-derived sigma proxy.

It also exposed a new limitation: 5 of 20 truth-visible holdout frames produced no front-end observation. Phase 10 deliberately preserved the Phase 9 detector and therefore did not address this detection-generalization gap.

A future phase should target broader perception-domain coverage and evaluate temporal geometry on a preregistered challenge set that independently contains partial/ambiguous observations without tuning against this holdout.

## Provenance

- Phase 10 result SHA-256: `4a8c3cecc505e136260e9652a6fe937881b6cda1504cf2379d8fa7dc4aad94d6`
- Phase 10 per-frame CSV SHA-256: `bac965f30dd249d271fb7faf3f8c2fc68bd6598957811ebe08eb51714af11486`
- Phase 10 result-manifest SHA-256: `6549c3aa5b5da147775b1fc2916c219370b4c15b0a59c715f372ecc3fcffe2c7`
- Phase 9 front-end trace SHA-256: `4a65b0c0ea50375213cd113b303d8745f8bb62200fcdafc85bfa3608a4162786`
- detection-details SHA-256: `b6cb34f65b75bca54845fee70918db062381bbb4f86b9fa2cca829837ad07283`
- raw capture metadata SHA-256: `9b259fb35100c64e7ea8ab8a800cd311450317e2bf032d42b7e95e1bdd829f8a`
- raw ULog SHA-256: `e919444c087aa68d2d307b5ef18b78d2af73c2500886c65b0a627be21c0db3ce`
- frozen calibration SHA-256: `8934d108de1e0fa99f6985e643bb3b81145cfd6d7f901e1dcc900bb84673b6e7`

## Scope

Simulation only.

`safety_acceptance = false`

`controller_tuning_allowed = false`

This result does not validate physical UAV flight or constitute a flight-safety acceptance.
