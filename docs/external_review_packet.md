# AegisLand — external review packet

## What I am asking you to review

I am looking for a **methodology and research-integrity sanity check**, not an endorsement of a UAV safety claim.

AegisLand is a simulation-only research project about persistent perception error in an autonomous landing task. The central idea is to combine component-wise confidence with an independent reference estimate so that a primary perception stream can be selectively rejected when it is confidently wrong.

The project now has three distinct evidence layers:

1. a frozen synthetic-image result (Phase 6B),
2. a higher-fidelity external-model comparison against PX4/Gazebo (Phase 8), and
3. an in-progress raw-camera external-perception path (Phase 9).

The detailed audit trail is in [`research_checkpoint_2026-08-10.md`](research_checkpoint_2026-08-10.md).

## Thirty-second summary

### Frozen synthetic result

Phase 6B was frozen at commit `b4e9838555e935a5ec42690495315473629b58f6` before held-out evaluation. In 1,500 paired synthetic landing episodes, the component-selective architecture performed strongly in the hardest mixed condition, while the project retained measurable weaknesses such as low-light timeouts and imperfect lateral selectivity.

These are synthetic-simulation results only.

### External-validity stress

Phase 7 stopped optimizing the frozen percentage and attacked the assumptions around it: sensing rates, latency, dropout, bias drift, common-mode faults, and a stronger plant. Its audited 200-episode factorial is explicitly labeled development/failure-discovery evidence because each cell has only five episodes.

### Independent PX4/Gazebo comparison

Phase 8 froze a simulator-agnostic trace-resemblance method before applying it to genuine PX4/Gazebo evidence. The frozen method classified the external trace as `diagnostic_mismatch` (`1 close / 2 watch / 9 mismatch / 14 insufficient`). The mismatch was preserved; no controller or threshold was changed to erase it.

This is the most important current external result: several internal surrogate distributions did not closely reproduce the PX4/Gazebo trace.

### Raw-camera evidence path

Phase 9 adds raw-frame preservation, per-frame SHA-256, timestamps, camera-pose association, explicit observation-missing semantics, and a descriptive external-perception trace format.

The current genuine Gazebo-camera run captured 56 raw 1280×960 frames, with 55 matched camera poses. However, the run **did not pass its predeclared evidence-completeness gate**: the relevant ground-truth ULog stream spans about 19.248 seconds while the gate requires at least 20.0 seconds.

The gate has not been weakened after seeing the result. Therefore Phase 9 currently has **no completed scientific external-perception result**. The failed attempt is retained as diagnostic evidence.

## Evidence status

| Evidence | Current status | Appropriate claim |
|---|---|---|
| Phase 6B held-out synthetic landing | frozen | result for the defined synthetic benchmark |
| Phase 7 factorial | audited development/seen | failure discovery, not safety-rate estimation |
| Phase 8 deterministic fixture | pipeline validation only | software/provenance machinery works |
| Phase 8 PX4/Gazebo trace | external simulator seen | frozen model-resemblance diagnostic = mismatch |
| Phase 9 deterministic camera fixture | pipeline validation only | raw-frame schema/hash machinery works |
| Phase 9 genuine Gazebo camera attempt | incomplete seen evidence | raw capture worked; completeness gate failed |
| Physical flight | not performed | no claim |

## What I would most value feedback on

Please be critical. In particular:

1. Is the frozen/development-seen/external-seen/fixture separation clear enough to prevent accidental overclaiming?
2. Are the Phase 8 empirical distribution and temporal diagnostics a reasonable first resemblance test?
3. Is it scientifically appropriate to preserve the Phase 8 mismatch and treat it as evidence against parts of the internal surrogate?
4. For Phase 9, is raw frame + timestamp + camera pose + per-frame hash a sufficient minimum provenance set?
5. Is the current decision **not** to relax the 20-second gate after observing 19.248 seconds the right research-integrity choice?
6. What would you preregister before collecting a later unseen external-perception evaluation?
7. Is there any wording in the project that sounds stronger than the evidence supports?

## Useful entry points

- Repository README: project motivation, frozen historical results, reproducibility, and limitations
- [`research_checkpoint_2026-08-10.md`](research_checkpoint_2026-08-10.md): current phase-by-phase audit
- PR #13: current Phase 9 implementation and CI history
- `docs/phase8_trace_validation.md`: frozen external-trace comparison protocol
- `docs/phase9_external_perception_protocol.md`: Phase 9 evidence roles and raw-frame protocol

## Scope boundary

AegisLand is **simulation-only**. No physical aircraft, hardware test, or real-flight safety claim is part of this review packet. Passing a CI job, a deterministic fixture, or even a simulator resemblance test should not be interpreted as safety acceptance for a real UAV.
