# AegisLand Final Prototype Readiness

This checklist defines what must be true before the current research branch is described as a final research-prototype candidate.

It is intentionally stricter than “the code runs.” AegisLand is a simulation-only research prototype, and a passing software test or simulator run is not a physical-aircraft safety claim.

## Final refinement snapshot

- camera world-pose provenance correction: `fae622cfa448e4945174e8c03982686c7b1b0e3a`
- one-command prototype smoke test: `33c5c73768757b508f5c613b2fba73f94e3fd5a6`
- heavy evidence-workflow path scoping: `ec79bcb944226450ee0c4ed7b0d6a050e36d4a45`
- first valid corrected Phase 9 camera evidence head: `33c5c73768757b508f5c613b2fba73f94e3fd5a6`
- successful genuine-camera workflow run: `31523496671`
- artifact ID: `9114281248`
- artifact digest: `sha256:bd2387f9518c7feb0bb5b8d7d02ccc7cbf416a73cd13e150ebeab06551b041a6`
- synchronized public README head: `8799b396fd784556d3077c433d0343a9a9a71917`
- CI on synchronized README head: run `31546010695` — **success**
- Phase 9 fixture/provenance validation on synchronized README head: run `31546010704` — **success**
- exact result record: [`phase9_gazebo_camera_seen_result.md`](phase9_gazebo_camera_seen_result.md)

Documentation commits after the evidence head do not redefine the scientific experiment.

## Release-candidate gates

### 1. Historical research boundaries remain frozen

- [x] Phase 6B frozen evidence remains unchanged.
- [x] Phase 7 audited development evidence remains unchanged.
- [x] Phase 8 frozen comparison remains unchanged.
- [x] The genuine Phase 8 PX4/Gazebo `diagnostic_mismatch` remains preserved.
- [x] No Phase 9 result is used to retune Phase 6B or Phase 8.

### 2. Core software verification

- [x] Full Python regression suite runs in CI.
- [x] Phase 9 fixture/schema validation runs in CI.
- [x] Raw fixture frame hashes are verified.
- [x] A one-command local smoke entrypoint exists at `scripts/final_prototype_smoke.sh`.
- [x] The smoke test explicitly preserves `simulation_only`, `pipeline_validation_only`, and `safety_acceptance=false` semantics for fixture evidence.

### 3. Genuine camera provenance

- [x] Raw Gazebo camera bytes are preserved rather than screenshots or reconstructed frames.
- [x] Per-frame SHA-256 identity is supported and independently rechecked for all 67 analyzed frames.
- [x] Camera image topic is discovered from the live simulator graph rather than silently guessed.
- [x] The collector composes the moving model world pose with the camera-link transform instead of treating a local link transform as a world pose.
- [x] The valid artifact demonstrates a changing camera world pose across the simulated trajectory.
- [x] The valid artifact contains 67 pose-linked frames for the preregistered analysis; the single initially pose-unavailable selected frame is excluded rather than guessed.

### 4. Evidence completeness

- [x] The minimum ULog ground-truth duration requirement remains 20.0 s; it was not weakened after earlier shortfalls.
- [x] The valid run contains 1,237 ground-truth samples spanning 24.684 s.
- [x] Raw camera evidence, mission metadata, simulator provenance, source SHAs, hashes, trace, result, and manifest are present in one auditable artifact.
- [x] Artifact/result/trace/ULog/metadata hash chains were independently rechecked after the run.

### 5. Phase 9 scientific boundary

- [x] Genuine camera evidence is labeled `external_perception_seen`, never held out.
- [x] Detector behavior remained frozen for the preregistered analysis.
- [x] The analyzer blob is byte-identical at implementation head `353bf45bc8dcad5c7875570b91011d062014ab59` and evidence head `33c5c73768757b508f5c613b2fba73f94e3fd5a6`.
- [x] Target-visibility semantics remained frozen.
- [x] No Phase 9 acceptance threshold was invented from the seen evidence.
- [x] No physical-flight or safety-acceptance claim is permitted.
- [x] The unchanged analysis completed and its descriptive result was preserved, including unfavorable geometry errors.
- [x] The resulting manifest and raw-frame hash chain were independently verified before documentation.

### 6. Prototype presentation

- [x] Heavy Gazebo evidence CI is limited to evidence-relevant source changes and remains manually dispatchable.
- [x] Documentation-only presentation changes no longer trigger the expensive genuine-camera workflow.
- [x] README exposes a one-command prototype smoke path and states the camera-pose provenance history honestly.
- [x] README and external-review packet are synchronized with the valid Phase 9 result.
- [x] The exact evidence head, workflow run ID, artifact ID/digest, hashes, and limitations are preserved in the Phase 9 result record.
- [x] PR #13 description is synchronized with the result and remains draft/unmerged.

## Scientific interpretation of the valid Phase 9 result

The valid 67-frame seen trace produced 25 truth-visible/detected frames, zero misses while truth-visible, and zero detections while truth-not-visible. Those counts are descriptive for this trace only.

The same result exposed weak metric geometry: lateral MAE was approximately **0.998 m** and altitude MAE approximately **1.520 m**, with much larger p95 errors. The uncertainty proxies were under-dispersed relative to the observed residuals. Strong detection availability must therefore not be presented as accurate pose estimation or end-to-end safety.

A direct Phase 7 KS/Wasserstein comparison remains withheld because the lateral-coordinate definitions are not directly compatible.

## Branch policy

PR #13 remains draft and unmerged. Reaching a research-prototype candidate does not automatically mean the branch should be merged, and external technical review can still motivate a later revision.

## Definition of done

The **research-prototype candidate** requires:

1. normal CI green;
2. Phase 9 schema/provenance validation green;
3. demonstrably correct genuine-camera pose provenance;
4. the genuine-camera evidence path reaching the unchanged descriptive Phase 9 analysis;
5. independent verification of the evidence/hash chain;
6. public documentation that states both favorable and unfavorable findings accurately;
7. no simulator result represented as physical-aircraft validation.

All seven gates are satisfied for the current prototype checkpoint. This means the software and research evidence package are ready to be treated as a **final research-prototype candidate for external review**. It does **not** mean AegisLand is validated flight-control software or safe for physical aircraft.
