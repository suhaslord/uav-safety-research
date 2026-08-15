# AegisLand — external review packet

## What I am asking you to review

I am looking for a **methodology and research-integrity sanity check**, not an endorsement of a UAV safety claim.

AegisLand is a simulation-only research project about persistent perception error in an autonomous landing task. The central idea is to combine component-wise confidence with an independent reference estimate so that a primary perception stream can be selectively rejected when it is confidently wrong.

The project now has three distinct evidence layers:

1. a frozen synthetic-image result (Phase 6B),
2. a higher-fidelity external-model comparison against PX4/Gazebo (Phase 8), and
3. a raw-camera external-perception result from PX4/Gazebo (Phase 9).

The full current Phase 9 evidence record is in [`phase9_gazebo_camera_seen_result.md`](phase9_gazebo_camera_seen_result.md).

## Thirty-second summary

### Frozen synthetic result

Phase 6B was frozen at commit `b4e9838555e935a5ec42690495315473629b58f6` before held-out evaluation. In 1,500 paired synthetic landing episodes, the component-selective architecture performed strongly in the hardest mixed condition, while the project retained measurable weaknesses such as low-light timeouts and imperfect lateral selectivity.

These are synthetic-simulation results only.

### External-validity stress

Phase 7 stopped optimizing the frozen percentage and attacked the assumptions around it: sensing rates, latency, dropout, bias drift, common-mode faults, and a stronger plant. Its audited 200-episode factorial is explicitly labeled development/failure-discovery evidence because each cell has only five episodes.

### Independent PX4/Gazebo comparison

Phase 8 froze a simulator-agnostic trace-resemblance method before applying it to genuine PX4/Gazebo evidence. The frozen method classified the external trace as `diagnostic_mismatch` (`1 close / 2 watch / 9 mismatch / 14 insufficient`). The mismatch was preserved; no controller or threshold was changed to erase it.

This remains an important negative external result: several internal surrogate distributions did not closely reproduce the PX4/Gazebo trace.

### Raw-camera evidence

Phase 9 adds raw-frame preservation, per-frame SHA-256, timestamps, corrected camera world-pose provenance, explicit observation-missing semantics, and a descriptive external-perception trace format.

Earlier genuine-camera attempts were rejected before scientific interpretation. One failed the unchanged 20.0-second ULog ground-truth completeness gate. A separate audit then found that the collector was recording a fixed local camera-link transform as though it were the moving camera world pose. That provenance defect was fixed without changing the detector, visibility definition, or descriptive analysis.

A fresh run at evidence head `33c5c73768757b508f5c613b2fba73f94e3fd5a6` passed the frozen gates and completed the unchanged analysis:

- workflow run: `31523496671`
- artifact ID: `9114281248`
- artifact digest: `sha256:bd2387f9518c7feb0bb5b8d7d02ccc7cbf416a73cd13e150ebeab06551b041a6`
- selected raw frames: 68
- analyzed pose-linked frames: 67
- independently reverified raw-frame hashes: 67/67
- ULog ground-truth stream: 1,237 samples / 24.684 s
- evidence role: `external_perception_seen`
- safety acceptance: false
- controller tuning allowed: false
- Phase 9 resemblance verdict: none declared

On this one seen trace, the detector had 25 true positives, 0 false negatives, 0 false positives, and 42 true negatives under the preregistered truth-visibility definition. However, the metric geometry was much weaker: lateral MAE was about **0.998 m** and altitude MAE about **1.520 m**, with large p95 errors. The uncertainty proxies were also too small relative to observed residuals.

That distinction is central: **strong target detection on this trace did not imply accurate geometry estimation or end-to-end safety.**

## Evidence status

| Evidence | Current status | Appropriate claim |
|---|---|---|
| Phase 6B held-out synthetic landing | frozen | result for the defined synthetic benchmark |
| Phase 7 factorial | audited development/seen | failure discovery, not safety-rate estimation |
| Phase 8 deterministic fixture | pipeline validation only | software/provenance machinery works |
| Phase 8 PX4/Gazebo trace | external simulator seen | frozen model-resemblance diagnostic = mismatch |
| Phase 9 deterministic camera fixture | pipeline validation only | raw-frame schema/hash machinery works |
| Phase 9 valid Gazebo camera trace | external perception seen | descriptive detection/localization/geometry evidence for one seen simulator trace |
| Physical flight | not performed | no claim |

## What I would most value feedback on

Please be critical. In particular:

1. Is the frozen/development-seen/external-seen/fixture separation clear enough to prevent accidental overclaiming?
2. Is preserving the Phase 8 `diagnostic_mismatch` the right interpretation rather than retuning against it?
3. Is raw frame + image timestamp + corrected camera world pose + per-frame hash a sufficient minimum provenance set for this Phase 9 stage?
4. Is using the latest received pose with a measured ~63 ms median association offset acceptable for this descriptive first trace, or should a later protocol require timestamp interpolation before unseen evaluation?
5. Does the Phase 9 result correctly separate target detection from metric geometry accuracy?
6. Are the large PnP residuals and under-dispersed uncertainty proxies being interpreted conservatively enough?
7. Is withholding Phase 7 KS/Wasserstein comparison because the coordinate definitions differ the right decision?
8. What should be preregistered before collecting any future unseen external-perception evaluation?
9. Is there any wording in the project that sounds stronger than the evidence supports?

## Useful entry points

- Repository README: project motivation, current evidence status, reproducibility, and limitations
- [`phase9_gazebo_camera_seen_result.md`](phase9_gazebo_camera_seen_result.md): exact valid Phase 9 result and provenance
- [`final_prototype_readiness.md`](final_prototype_readiness.md): release-candidate audit checklist
- [`research_checkpoint_2026-08-10.md`](research_checkpoint_2026-08-10.md): phase-by-phase history before the valid camera rerun
- PR #13: current Phase 9 implementation and CI history
- `phase8_trace_validation.md`: frozen external-trace comparison protocol
- `phase9_external_perception_protocol.md`: Phase 9 evidence roles and raw-frame protocol

## Scope boundary

AegisLand is **simulation-only**. No physical aircraft, hardware-camera test, or real-flight safety claim is part of this review packet. Passing CI or obtaining a valid simulator trace is not safety acceptance for a real UAV.
