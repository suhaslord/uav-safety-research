# Phase 9 — External Perception Validation Protocol

## Purpose

Phase 9 addresses the major unresolved limitation from Phase 8: the successful PX4/Gazebo `gz_x500` evidence mission contained no populated external visual-odometry stream, so image/perception resemblance could not be evaluated.

Phase 9 is a **simulation-only external-perception study**. It does not revise the Phase 8 mismatch result and it does not authorize controller tuning.

## Frozen ancestry

Phase 9 begins from merged repository state:

- Phase 9 parent main merge: `babd4d9849c4792ff1cc002c51cc5dbbc6ed0221`
- frozen Phase 8 comparison/tooling head: `bd62e3b31431306fd9d897f560be7325d711d21a`
- audited Phase 8 PX4/Gazebo seen-evidence head: `b9df03e111f3a796e50df440becc587c48ee7643`
- audited Phase 7 development head: `7354eeda8b975f45b659ce4f3f86c82501e6321d`
- frozen historical Phase 6B commit: `b4e9838555e935a5ec42690495315473629b58f6`

Phase 9 must not modify the frozen Phase 8 comparison code, Phase 6B result files, or frozen controller/supervisor behavior in response to external camera evidence.

## External simulator target

The initial simulator target is PX4 v1.17 SITL with Gazebo using the documented downward-facing monocular X500 model `gz_x500_mono_cam_down` in the `aruco` world. PX4 documents this combination for precision-landing camera testing.

Camera frames must be captured from the simulator camera transport stream independently of AegisLand. The actual Gazebo transport topic must be discovered from the running model rather than guessed or silently hard-coded from an unrelated model.

The first real capture is development evidence. It must not be called held-out evidence.

## Evidence roles

Phase 9 recognizes the following roles:

- `fixture_non_authoritative`: deterministic CI/interface data only; never external validation evidence.
- `external_perception_seen`: genuine independently generated simulator camera evidence inspected during Phase 9 development.
- `external_perception_unseen`: a future trace that was not inspected during development and is only evaluated after the Phase 9 analysis protocol, metrics, thresholds (if any), and implementation are frozen.

No trace may be relabeled from seen to unseen after inspection.

## Canonical frame evidence

Each row in `aegisland.phase9.perception-trace.v1` represents one captured camera frame and includes:

- monotonic frame timestamp and frame index;
- safe relative raw-frame path;
- SHA-256 of the exact raw frame bytes;
- image width and height;
- simulator truth for target visibility, target pixel center/area when visible, lateral offset, and altitude;
- perception observation availability;
- observed target pixel center, lateral offset, altitude, confidence, and uncertainty only when an observation genuinely exists;
- optional camera transport latency and exposure duration when actually observable.

Ground truth is evaluation-only. It must never be passed into the estimator/controller as an input.

Missing estimator observations remain missing. Numeric zero sentinels are forbidden for an unavailable observation because they can be mistaken for measurements.

## Raw-frame provenance requirements

A genuine Phase 9 evidence bundle must preserve, at minimum:

- every raw camera frame used in analysis;
- SHA-256 for every frame;
- exact frame timestamps/order;
- raw PX4 ULog from the same run when available;
- simulator log;
- PX4 release and exact Git SHA;
- Gazebo model and world;
- discovered camera topic;
- image dimensions and camera calibration/intrinsics when available;
- exact AegisLand Git SHA used for any perception analysis;
- evidence role (`external_perception_seen` or later `external_perception_unseen`);
- workflow/run identifier;
- hashes for produced trace/report/manifest files.

A capture is invalid as authoritative perception evidence if raw frame identity cannot be verified.

## Predeclared descriptive metrics

The first genuine seen trace will be analyzed with raw descriptive discrepancy metrics. The metric set is declared before that trace is inspected:

1. target-visible rate;
2. observation-available rate;
3. missed-detection rate conditional on target visibility;
4. false-positive rate conditional on target non-visibility;
5. horizontal and vertical target-center pixel error;
6. target-center error normalized by image diagonal;
7. target-center error relative to target pixel footprint when observable;
8. lateral-position error for valid observations;
9. altitude error for valid observations when scale is observable;
10. confidence versus absolute error calibration summaries;
11. uncertainty-normalized residual summaries where reported sigma is available;
12. frame interval and timing-jitter distributions;
13. transport-latency distribution when directly observable;
14. missed-detection/dropout burst-length distribution;
15. lag-1 temporal correlation of valid perception errors;
16. error versus altitude and target pixel area;
17. empirical KS distance against the corresponding Phase 7 camera-surrogate series where definitions are compatible;
18. scale-normalized Wasserstein-1 distance against compatible Phase 7 camera-surrogate series.

Dimensions that are not actually observable are reported as `insufficient`/unavailable rather than reconstructed from unrelated signals.

## Threshold policy

**No Phase 9 external-perception resemblance thresholds are declared in this initial protocol.**

The first genuine simulator camera trace therefore produces descriptive discrepancy evidence, not a `close`/`mismatch` acceptance verdict. If classification thresholds are later useful, they must be committed in a protocol revision **before** the first trace to which those thresholds are applied is inspected. Thresholds may not be selected by looking at the trace they classify.

## Development and held-out lifecycle

1. Freeze this schema and raw metric definitions.
2. Validate the pipeline using `fixture_non_authoritative` raw frames.
3. Capture a genuine simulator camera trace and mark it `external_perception_seen`.
4. Preserve raw evidence and compute the predeclared descriptive metrics.
5. Fix only correctness/provenance bugs discovered in the pipeline; do not tune the frozen Phase 8/controller logic from the result.
6. If a future model revision is scientifically justified, create a new explicitly versioned development phase rather than rewriting the Phase 8 result.
7. Only after the Phase 9 analysis implementation/protocol is frozen may a separate, truly unseen simulator trace be declared `external_perception_unseen`.

## Claims allowed after a seen trace

Allowed:

> We independently generated camera evidence in a higher-fidelity simulator and measured how its perception/error behavior differs from the Phase 7 camera surrogate using a predeclared analysis.

Not allowed from Phase 9 alone:

- physical-flight validation;
- proof of safety;
- a real-world failure probability;
- a held-out claim for a trace inspected during development;
- a claim that unavailable perception dimensions matched;
- tuning Phase 6B/Phase 7/Phase 8 thresholds to improve the reported resemblance.

## Initial completion gate

The Phase 9 infrastructure milestone is complete only when:

- the canonical perception trace validator is implemented;
- deterministic raw-frame fixtures are hash-verified end to end;
- negative tests prove missing observations cannot masquerade as zeros;
- path traversal and frame hash tampering are rejected;
- normal repository CI remains green;
- a Phase 9-specific workflow verifies the frozen ancestry and uploads a non-authoritative fixture artifact.

A genuine camera evidence milestone is separate and requires a real simulator camera capture.
