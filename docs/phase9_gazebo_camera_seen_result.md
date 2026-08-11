# Phase 9 genuine Gazebo camera — first valid seen result

## Status

The first Phase 9 genuine PX4/Gazebo downward-camera trace that passed the preregistered evidence-completeness and provenance gates is recorded as **`external_perception_seen`**.

This is a descriptive simulator-perception result. It is **not** held-out evidence, a resemblance acceptance, a controller-safety result, or physical-aircraft validation.

No detector behavior, target-visibility definition, Phase 6B/Phase 8 logic, or Phase 9 acceptance threshold was changed to obtain this result.

## Exact evidence identity

- AegisLand evidence head: `33c5c73768757b508f5c613b2fba73f94e3fd5a6`
- provenance fix included in ancestry: `fae622cfa448e4945174e8c03982686c7b1b0e3a`
- workflow: `Phase 9 Gazebo Camera Evidence`
- workflow run: `31523496671`
- workflow attempt: `1`
- artifact: `phase9-gazebo-camera-evidence-seen`
- artifact ID: `9114281248`
- artifact digest: `sha256:bd2387f9518c7feb0bb5b8d7d02ccc7cbf416a73cd13e150ebeab06551b041a6`
- PX4 release: `v1.17.0`
- PX4 source SHA: `d6f12ad1c4f70ad3230afd7d86e971421e02fef4`
- simulator model: `gz_x500_mono_cam_down`
- simulator world: `aruco`
- camera topic: `/world/aruco/model/x500_mono_cam_down_0/link/camera_link/sensor/imager/image`
- pose topic: `/world/aruco/pose/info`

## Provenance and completeness audit

The run selected **68** raw 1280×960 image payloads. The first selected frame did not yet have a valid synchronized camera pose and was excluded rather than zero-filled or guessed. The scientific trace therefore contains **67** pose-linked raw frames.

Independent post-run rechecking confirmed:

- 67/67 analyzed raw frame files exist and match the SHA-256 recorded in the perception trace;
- each raw image payload is 3,686,400 bytes;
- the capture metadata SHA-256 matches the evidence receipt;
- the mission metadata SHA-256 matches the evidence receipt;
- the ULog SHA-256 matches the evidence receipt;
- the frozen Phase 7 surrogate SHA-256 matches the evidence receipt;
- the perception-trace, scientific-result, and result-manifest hashes match the evidence receipt;
- every file listed by `analysis/result_manifest.json` matches its declared byte count and SHA-256;
- the completed mission contains the nine preregistered simulation-only visibility-sweep segments;
- `vehicle_local_position_groundtruth` contains 1,237 samples spanning **24.684 s**, above the unchanged **20.0 s** completeness minimum;
- the corrected camera world pose varies across the trace rather than remaining a fixed local-link transform;
- image-to-latest-pose receive-time offset across the 67 analyzed frames had median approximately **0.063 s**, p95 approximately **0.110 s**, and maximum approximately **0.123 s**.

The analyzer blob at the evidence head is byte-identical to the analyzer at implementation head `353bf45bc8dcad5c7875570b91011d062014ab59` (`ad2b75efac09e9004cf440dabd4188aa60d4e95c`). The successful rerun therefore did not change the preregistered detector or descriptive analysis after seeing the rejected attempts.

A comparison from Phase 9 parent main `babd4d9849c4792ff1cc002c51cc5dbbc6ed0221` to the evidence head shows no edits to the protected Phase 8 or Phase 6B implementation/evidence paths.

## Descriptive scientific result

The 67-frame trace spans **21.78 s** of Gazebo image timestamps.

### Visibility and detection

- truth-visible frames: **25**
- truth-not-visible frames: **42**
- true positives: **25**
- false negatives: **0**
- false positives: **0**
- true negatives: **42**
- missed-detection rate when truth-visible: **0.0**
- false-positive rate when truth-not-visible: **0.0**
- observation-available rate: **25/67 = 0.3731**
- detector breakdown on detections: **18 ArUco**, **7 fixed quad fallback**
- ArUco detections used `DICT_4X4_50`

These counts describe this one **seen** simulator trace only. They must not be interpreted as a general detection rate or safety rate.

### Image localization

For the 25 paired visible/detected frames:

- pixel-center MAE: **40.99 px**
- pixel-center median error: **16.00 px**
- pixel-center p95 error: **113.80 px**
- maximum pixel-center error: **462.92 px**
- normalized pixel-center MAE: **0.0256**
- footprint-normalized center MAE: **0.1225**

### PnP geometry

The geometric estimates are the most important negative finding in this result.

- lateral MAE: **0.998 m**
- lateral p95 absolute error: **5.087 m**
- maximum lateral absolute error: **7.344 m**
- altitude MAE: **1.520 m**
- altitude p95 absolute error: **6.597 m**
- maximum altitude absolute error: **10.294 m**
- median `|lateral residual| / sigma`: **8.11**
- median `|altitude residual| / sigma`: **5.89**

The uncertainty proxies are therefore not well calibrated to these geometric residuals on this trace. Strong detection availability should **not** be confused with accurate pose/geometry estimation.

### Temporal/descriptive diagnostics

- mean analyzed frame interval: **0.330 s**
- frame-interval standard deviation: **0.002 s**
- p95 frame interval: **0.332 s**
- maximum missed-detection burst while truth-visible: **0 frames**
- lag-1 lateral-error correlation: **0.060**
- confidence vs. absolute lateral-error Pearson correlation: **-0.851**
- absolute lateral error vs. altitude Pearson correlation: **-0.270**
- pixel error vs. projected target area Pearson correlation: **0.956**

These correlations are descriptive diagnostics from 25 paired samples, not calibrated guarantees.

## Phase 7 comparison

A direct Phase 7 KS/Wasserstein comparison is intentionally withheld. Phase 9 lateral error is defined in the external camera optical-horizontal axis, whereas the frozen Phase 7 `image_x_m` series is a state-level lateral coordinate. Computing a distribution distance across those incompatible definitions would create a misleading number.

The scientific result records this as `insufficient_axis_definition` rather than forcing a favorable or unfavorable comparison.

## Interpretation

The valid Phase 9 result demonstrates that the project can preserve genuine Gazebo camera payloads, bind them to explicit simulator provenance, verify them by hash, construct projected truth from corrected moving camera world poses, and run the unchanged descriptive detector/analyzer end to end.

It does **not** demonstrate accurate metric pose recovery. In this trace, target detection availability was strong but the PnP-derived lateral and altitude estimates showed large errors and under-dispersed uncertainty proxies. That distinction is part of the result and must remain visible in later presentations.

No Phase 9 classification threshold or resemblance verdict is declared. `safety_acceptance = false` and `controller_tuning_allowed = false` remain unchanged.

## Remaining limitations

- simulation only; no physical-camera or physical-aircraft evidence;
- one short PX4/Gazebo downward-camera trace;
- first valid genuine-camera trace is **seen**, not held out;
- only 25 paired truth-visible/detected samples drive the geometric metrics;
- fiducial/quad imagery is simpler than broad real-world landing perception;
- the pose association uses the latest received camera pose rather than a fully timestamp-interpolated pose stream;
- image/reprojection-derived sigmas are uncertainty proxies, not calibrated probabilistic guarantees;
- Phase 7 distribution comparison remains withheld because the axes are not directly compatible;
- nothing in this result changes the frozen Phase 8 `diagnostic_mismatch`.

## Claim-safe summary

> The first valid PX4/Gazebo downward-camera trace was recorded as `external_perception_seen`. Raw-frame and provenance integrity checks passed and the unchanged preregistered Phase 9 analysis ran to completion. Detection availability was strong on this seen trace, while PnP geometry errors remained large. No acceptance threshold, safety verdict, controller retuning, or physical-flight claim was applied.
