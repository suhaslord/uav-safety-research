# Model VASE evidence map

Model VASE is AegisLand's proposed landing-reliability system. Its design combines target confidence, estimate uncertainty, and disagreement between independent estimates before the landing decision. It is a system architecture, not a newly trained vision network. The camera detector, uncertainty model, and simulator are still separate artifacts; their combined camera-to-control behavior has not been evaluated.

## Main question

Can a landing system recognize unreliable perception before it trusts a bad estimate?

## Proposed Model VASE flow

1. **Perceive:** detect the landing target and retain the detector's location and confidence.
2. **Check:** compare the estimate with uncertainty and disagreement signals from independent estimates.
3. **Decide:** continue, request another view, hold, or abort according to a rule chosen on development evidence and tested on independent evaluation data.

This is the architecture the project is working toward, not an end-to-end result. Phase 12 uncertainty, the V3 simulator supervisor, and the KIOS camera detector have not been run together.

**Current answer:** conditionally yes in the frozen planar simulator. The real-camera detector results do not yet show an integrated reliability response, and no result establishes flight safety.

## Evidence kept separate

| Track | What was tested | Result | Boundary |
| --- | --- | --- | --- |
| Frozen V3 simulator | 10,000 simulated episodes; 500 paired seeds per architecture/profile cell | Under mixed stress, V3 success was 97.6% and unsafe touchdown was 2.4%; baseline unsafe touchdown was 84.2% | Planar simulation with abstract perception stress; no image-based detector in V3 |
| KIOS detector | Two detector configurations on the same 86 protected video frames across six conditions | Phase 24 found a +3.4 pp equal-weight mAP50 average and a −13.3 pp mean for occlusion plus mixed stress | Reanalysis of published aggregates; not a closed-loop landing test |
| Phase 25 Failure Atlas | Original baseline checkpoint on 86 verified frames and 516 reconstructed views | Baseline boxes and frame diagnostics are available; Phase 23 paired frame outcomes remain pending | The exact Phase 23 checkpoint and original inference versions are unavailable |
| Phase 12 uncertainty | Frozen uncertainty candidate across development, transfer, protected validation, and final replication | The preregistered simulation gates passed without retuning | Not connected to the KIOS detector or tested as a camera-to-control stack |

## What would answer the question more fully

Recover and verify the Phase 23 checkpoint and inference runtime, connect the image detector to a reliability rule using development data, then evaluate that frozen connection on genuinely independent imagery. The reused 86-frame set cannot select the rule or serve as new confirmation evidence.

## Reproduction and source records

- [Frozen V3 results](v3_results.md)
- [Phase 12 final report](phase12_iteration3_final_report.md)
- [Phase 23 detector result](../results/phase23_robust_detector/summary.md)
- [Phase 24 audit](../results/phase24_robustness_audit/summary.md)
- [Phase 25 protocol](phase25_protocol.md)
- [Phase 26 protocol](phase26_protocol.md)
