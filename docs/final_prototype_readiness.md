# AegisLand Final Prototype Readiness

This checklist defines what must be true before the current research branch is described as a final prototype candidate.

It is intentionally stricter than “the code runs.” AegisLand is a simulation-only research prototype, and a passing software test or simulator run is not a physical-aircraft safety claim.

## Current refinement snapshot

- camera world-pose provenance correction: `fae622cfa448e4945174e8c03982686c7b1b0e3a`
- one-command prototype smoke test: `33c5c73768757b508f5c613b2fba73f94e3fd5a6`
- heavy evidence-workflow path scoping: `ec79bcb944226450ee0c4ed7b0d6a050e36d4a45`
- first valid corrected Phase 9 camera evidence head: `33c5c73768757b508f5c613b2fba73f94e3fd5a6`
- successful genuine-camera workflow run: `31523496671`
- artifact ID: `9114281248`
- artifact digest: `sha256:bd2387f9518c7feb0bb5b8d7d02ccc7cbf416a73cd13e150ebeab06551b041a6`
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
- [x] README exposes a one-command prototype smoke path and states the camera-pose provenance history honestly.
- [ ] Synchronize the README and external-review packet with the valid Phase 9 result.
- [x] The exact evidence head, workflow run ID, artifact ID/digest, hashes, and limitations are preserved in the Phase 9 result record.
- [x] PR #13 remains draft and unmerged while final presentation/documentation is being synchronized.

## Scientific interpretation of the valid Phase 9 result

The valid 67-frame seen trace produced 25 truth-visible/detected frames, zero misses while truth-visible, and zero detections while truth-not-visible. Those counts are descriptive for this trace only.

The same result also exposed weak metric geometry: lateral MAE was approximately **0.998 m** and altitude MAE approximately **1.520 m**, with much larger p95 errors. The uncertainty proxies were under-dispersed relative to the observed residuals. Strong detection availability must therefore not be presented as accurate pose estimation or end-to-end safety.

A direct Phase 7 KS/Wasserstein comparison remains withheld because the lateral-coordinate definitions are not directly compatible.

## Branch policy during refinement

Do not merge PR #13 simply because software CI and simulator evidence pass. The branch remains the audit workspace while final public-facing documentation is synchronized and external review is still welcome.

## Definition of done

The **research prototype candidate** is reached when:

1. normal CI is green;
2. Phase 9 schema/provenance validation is green;
3. genuine-camera pose provenance is demonstrably correct;
4. the genuine-camera evidence path reaches the unchanged descriptive Phase 9 analysis;
5. the full evidence/hash chain is independently checked;
6. all public-facing documentation states the favorable and unfavorable findings accurately;
7. no simulator result is represented as physical-aircraft validation.

Gates 1–5 are now satisfied. The remaining work is presentation/documentation synchronization and one final exact-head software audit. A negative scientific metric does not prevent the software from being a final research prototype; it limits the claim that can accompany it.
