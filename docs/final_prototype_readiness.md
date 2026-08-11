# AegisLand Final Prototype Readiness

This checklist defines what must be true before the current research branch is described as a final prototype candidate.

It is intentionally stricter than "the code runs." AegisLand is a simulation-only research prototype, and a passing software test or simulator run is not a physical-aircraft safety claim.

## Current refinement snapshot

- camera world-pose provenance correction: `fae622cfa448e4945174e8c03982686c7b1b0e3a`
- one-command prototype smoke test: `33c5c73768757b508f5c613b2fba73f94e3fd5a6`
- heavy evidence-workflow path scoping: `ec79bcb944226450ee0c4ed7b0d6a050e36d4a45`

Documentation commits after these implementation changes do not redefine the scientific experiment.

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
- [x] Per-frame SHA-256 identity is supported.
- [x] Camera image topic is discovered from the live simulator graph rather than silently guessed.
- [x] The camera-pose collector now composes the moving model world pose with the fixed camera-link transform instead of treating a local link transform as a world pose.
- [ ] A fresh genuine-camera artifact demonstrates that the corrected camera world pose changes consistently with the simulated vehicle trajectory.
- [ ] A fresh artifact contains enough valid pose-linked frames for the preregistered analysis.

### 4. Evidence completeness

- [x] The minimum ULog ground-truth duration requirement remains 20.0 s; it has not been weakened after observed shortfalls.
- [ ] A fresh genuine-camera run satisfies the predeclared ULog completeness gate.
- [ ] Required raw evidence, mission metadata, simulator provenance, source SHAs, and hashes are present in one auditable artifact.

### 5. Phase 9 scientific boundary

- [x] First genuine camera evidence is labeled `external_perception_seen`, never held out.
- [x] Detector behavior remains frozen for the current preregistered analysis.
- [x] Target-visibility semantics remain frozen.
- [x] No Phase 9 acceptance threshold has been invented from the seen evidence.
- [x] No physical-flight or safety-acceptance claim is permitted.
- [ ] If the evidence-completeness gates pass, run the unchanged preregistered analysis and preserve its descriptive result whether favorable or unfavorable.
- [ ] Verify the resulting manifest and raw-frame hash chain independently before documenting the result.

### 6. Prototype presentation

- [x] Heavy Gazebo evidence CI is limited to evidence-relevant source changes and remains manually dispatchable.
- [x] README exposes a one-command prototype smoke path and states the camera-pose provenance correction honestly.
- [ ] Synchronize the external-review packet with the final exact evidence status.
- [ ] Add the final exact commit SHA, workflow run ID, artifact ID/digest, and limitations to the release checkpoint.
- [x] PR #13 remains draft and unmerged while the final audit is incomplete.

## Definition of done

The final prototype candidate is reached when:

1. normal CI is green;
2. Phase 9 schema/provenance validation is green;
3. genuine-camera pose provenance is demonstrably correct;
4. the genuine-camera evidence path either reaches the unchanged descriptive Phase 9 analysis or is preserved as an explicit unresolved blocker;
5. all public-facing documentation states exactly which of those two outcomes occurred;
6. no simulator result is represented as physical-aircraft validation.

A negative or incomplete scientific result does **not** prevent the software from being a final research prototype. It only limits the scientific claim that can accompany it.
