const PHASES = {
  phase1: {
    label: "Phase 1 · Aegis V1",
    era: "Foundation",
    title: "Can a simple safety layer stop a bad landing?",
    lede: "The first experiment compared a normal landing controller with a supervisor that could HOLD or ABORT when perception looked risky. We tested it across clean, blurred, dark, occluded, and mixed conditions.",
    status: "Frozen original experiment",
    role: "simulation-only · 5,000 episodes",
    change: [
      "Added confidence-aware HOLD / ABORT decisions",
      "Locked the unsafe-touchdown endpoint before testing",
      "Reported safety and availability separately"
    ],
    before: "The controller acted directly on the perception estimate.",
    after: "A separate supervisor could pause or abort when risk crossed frozen thresholds.",
    metrics: [["Mixed unsafe", "82.8% → 0%"], ["Mixed abort", "0% → 100%"], ["Main lesson", "Safety ≠ availability"]],
    finding: "V1 stopped the unsafe touchdowns in the hardest mixed condition, but it did so by aborting every time. That made the tradeoff obvious: a system can look safe simply because it refuses to finish the task.",
    source: "Phase 1 preregistration + V1 findings",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/blob/phase10-temporal-metric-perception/docs/v1_findings_and_v2_plan.md"
  },

  phase2: {
    label: "Phase 2 · Aegis V2",
    era: "Foundation",
    title: "Stop overreacting to one bad frame.",
    lede: "V2 made the supervisor less jumpy. Instead of treating one ugly measurement as a crisis, it filtered risk over time and required the problem to persist before escalating.",
    status: "Fixed V2 result",
    role: "simulation-only · 7,500 episodes",
    change: [
      "Filtered risk across time",
      "Required persistence before escalation",
      "Added hysteresis and recovery-aware HOLD behavior"
    ],
    before: "One severe observation could trigger a long hold or an abort.",
    after: "Risk had to stay high long enough to justify escalation.",
    metrics: [["Mixed abort", "100% → 0%"], ["Occlusion abort", "94.6% → 0%"], ["Mixed unsafe", "84.8%"]],
    finding: "V2 fixed the availability disaster from V1, but it revealed a harder problem: a sensor can be consistently wrong. Temporal smoothing helps with spikes; it does not automatically expose a steady bias.",
    source: "V2 frozen results",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/blob/phase10-temporal-metric-perception/docs/v2_results.md"
  },

  phase3: {
    label: "Phase 3 · Aegis V3",
    era: "Foundation",
    title: "Give vision a second opinion.",
    lede: "V3 added an independent reference estimate. When vision and the reference disagreed for long enough, the system could treat that disagreement as evidence of bias instead of trusting one internally consistent stream.",
    status: "Frozen held-out result",
    role: "simulation-only · 10,000 episodes",
    change: [
      "Added an independent reference estimator",
      "Tracked cross-estimator disagreement",
      "Corrected only when confidence supported the correction"
    ],
    before: "The system had only one corrupted observation stream to reason about.",
    after: "A second error pattern made persistent visual bias observable.",
    metrics: [["Mixed success", "97.6%"], ["Mixed unsafe", "2.4%"], ["Occlusion unsafe", "1.4%"]],
    finding: "V3 was the first big architecture win. The important part was not another filter; it was independent evidence. A second estimator exposed errors the first one could not diagnose by looking only at itself.",
    source: "V3 frozen results",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/blob/phase10-temporal-metric-perception/docs/v3_results.md"
  },

  phase4: {
    label: "Phase 4 · Naming gap",
    era: "Foundation",
    title: "There is no standalone Phase 4 result.",
    lede: "The early work was named V1, V2, and V3. The repository then resumes explicit phase numbering at Phase 5. The archive keeps that gap instead of inventing a milestone that never happened.",
    status: "No standalone phase",
    role: "historical lineage · no invented result",
    change: [
      "Keep the original naming history",
      "Do not invent a result for visual neatness",
      "Treat the gap as part of provenance"
    ],
    before: "The early experiments were versioned as V1, V2, and V3.",
    after: "The next explicit numbered milestone is Phase 5.",
    metrics: [["Standalone result", "None"], ["Invented metrics", "0"], ["Archive policy", "Gap preserved"]],
    finding: "A clean-looking timeline is not more important than an accurate one. There was no separate Phase 4 experiment, so the archive says that plainly.",
    source: "Repository research checkpoint",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/blob/phase10-temporal-metric-perception/docs/research_checkpoint_2026-08-10.md"
  },

  phase5: {
    label: "Phase 5 · Robustness",
    era: "Perception + robustness",
    title: "Push V3 harder, then move from abstract errors to pixels.",
    lede: "Phase 5 swept new seeds, stronger degradation, reference quality, dropout, and persistent bias. It also introduced a 96×96 synthetic landing-pad image benchmark so perception could finally fail for image-level reasons.",
    status: "Completed robustness study",
    role: "simulation-only · stress + synthetic images",
    change: [
      "Added five unseen seed families and broad stress sweeps",
      "Tested reference quality and dropout sensitivity",
      "Added the first synthetic landing-pad renderer and pixel estimator"
    ],
    before: "V3 had strong frozen results, but perception was still represented as abstract corrupted measurements.",
    after: "The controller was stress-tested more broadly and the project gained its first real image-derived measurements.",
    metrics: [["Mixed V3 success", "97.6% mean"], ["Mixed V3 unsafe", "2.4% mean"], ["Image valid outputs", "100% — too willing"]],
    finding: "V3 held up well under the broader simulation sweeps. The new image estimator exposed a different failure: it almost never admitted uncertainty. It kept returning a valid answer even when the answer was bad.",
    source: "Phase 5 results",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/blob/phase10-temporal-metric-perception/docs/phase5_results.md"
  },

  phase6: {
    label: "Phase 6 · Image perception",
    era: "Perception + robustness",
    title: "Run the landing loop from image-derived measurements.",
    lede: "Phase 6 connected synthetic image sequences to confidence calibration, tracking, reacquisition, velocity estimation, redundant checks, and the frozen Aegis supervisor.",
    status: "Frozen held-out result",
    role: "synthetic-image simulation",
    change: [
      "Built a pixel-to-observation pipeline",
      "Added abstention, track loss, and reacquisition",
      "Added image-derived velocity and redundant near-ground checks"
    ],
    before: "The best controller result still depended on abstract state estimates.",
    after: "Landing decisions came from a complete synthetic image-sequence pipeline.",
    metrics: [["Mixed success", "92%"], ["Mixed unsafe", "7%"], ["Bad-frame rejection", "Still weak"]],
    finding: "The full system became safer even though the frame-level confidence still missed many bad images. In other words, the architecture could absorb some perception mistakes without actually recognizing every mistake when it happened.",
    source: "Phase 6 frozen results",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/blob/phase10-temporal-metric-perception/docs/phase6_results.md"
  },

  phase6b: {
    label: "Phase 6B · Selective confidence",
    era: "Perception + robustness",
    title: "Stop judging the whole image with one confidence score.",
    lede: "Phase 6B split lateral-position confidence from altitude/scale confidence. If vision was useful for one component but not the other, the system could keep the good part and substitute only the weak part.",
    status: "Frozen held-out result",
    role: "synthetic-image simulation · component selective",
    change: [
      "Separated lateral and altitude confidence",
      "Added a pixel-scale altitude observability cap",
      "Allowed component-specific abstention and reference takeover"
    ],
    before: "One global confidence score could throw away useful lateral information just because altitude looked weak, or the other way around.",
    after: "Each geometry component could be accepted or rejected on its own evidence.",
    metrics: [["Mixed success", "99%"], ["Mixed unsafe", "1%"], ["Occlusion unsafe", "4%"]],
    finding: "The split confidence design worked better than one all-or-nothing score. It became the strongest frozen synthetic-image landing result, while still leaving clear weaknesses in low light and mixed lateral rejection.",
    source: "Phase 6B frozen results",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/blob/phase10-temporal-metric-perception/docs/phase6b_results.md"
  },

  phase7: {
    label: "Phase 7 · External validity stress",
    era: "External validation",
    title: "Make the simulator less forgiving.",
    lede: "Phase 7 stopped chasing another easy percentage point and attacked the assumptions underneath the earlier results: sensor timing, stale state, common-mode faults, actuator lag, rate limits, drag, and colored disturbances.",
    status: "Audited development milestone",
    role: "simulation-only · development evidence",
    change: [
      "Added GNSS-like lateral and barometer/range-like vertical sensing",
      "Added latency, stale state, queues, and common-mode faults",
      "Added actuator lag, rate limits, nonlinear drag, and colored disturbances"
    ],
    before: "Earlier experiments still used relatively clean timing and simplified dynamics.",
    after: "Sensors arrived at different rates, could become stale or jointly wrong, and drove a harder plant model.",
    metrics: [["Factorial", "200 episodes"], ["New stresses", "Bias / dropout / latency"], ["Outcome", "Weak cells preserved"]],
    finding: "Phase 7 did what a robustness phase should do: it found weak cells and kept them. The value was not a prettier score; it was a harder environment that made brittle assumptions easier to see.",
    source: "Phase 7 PR #10",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/pull/10"
  },

  phase8: {
    label: "Phase 8 · Higher-fidelity validation",
    era: "External validation",
    title: "Compare the internal simulator with PX4 and Gazebo.",
    lede: "Phase 8 built a common trace format so AegisLand output could be compared with a real PX4 SITL + Gazebo run using frozen comparison thresholds.",
    status: "Merged external-simulator evidence",
    role: "simulation-only · PX4/Gazebo",
    change: [
      "Added a shared external-trace schema and provenance",
      "Added KS, Wasserstein, correlation, and latency diagnostics",
      "Pinned a PX4 SITL + Gazebo evidence harness"
    ],
    before: "The important conclusions still came from AegisLand's own simulator family.",
    after: "Internal traces could be compared directly with an outside simulator trace.",
    metrics: [["Close", "1"], ["Mismatch", "9"], ["Overall", "diagnostic_mismatch"]],
    finding: "The answer was mostly mismatch. That was useful. Instead of retuning until the two simulators looked similar, the project kept the disagreement and treated it as evidence that the internal model was not yet externally representative.",
    source: "Phase 8 PX4/Gazebo PR #12",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/pull/12"
  },

  phase9: {
    label: "Phase 9 · External perception",
    era: "External validation",
    title: "Use actual Gazebo camera frames.",
    lede: "Phase 9 preserved raw Gazebo camera bytes and hashes, fixed camera-pose provenance, and ran ArUco/quad detection plus PnP geometry on the first valid external-camera trace.",
    status: "Audited seen-camera evidence",
    role: "simulation-only · external_perception_seen",
    change: [
      "Preserved raw Gazebo camera payloads and SHA-256 hashes",
      "Used ArUco with a fixed quad fallback",
      "Linked metric geometry to camera pose and explicit uncertainty"
    ],
    before: "PX4/Gazebo had tested navigation behavior, but not the AegisLand camera model itself.",
    after: "The project had traceable measurements from genuine simulator-camera frames.",
    metrics: [["Visible observations", "25 / 25"], ["Lateral MAE", "0.998 m"], ["Altitude MAE", "1.520 m"]],
    finding: "Detection worked on the seen trace, but metric geometry was not good enough. The biggest errors came from the seven quad-fallback measurements, which made the next target clear: protect the estimator from ambiguous fallback geometry.",
    source: "Phase 9 PR #13",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/pull/13"
  },

  phase10: {
    label: "Phase 10 · AegisT10",
    era: "Current frontier",
    title: "Make metric perception temporal, then freeze it before the new trajectory.",
    lede: "AegisT10 kept the Phase 9 camera front end, added causal state over time, and calibrated uncertainty on development data before running once on a new 11-segment PX4/Gazebo holdout.",
    status: "Frozen holdout complete",
    role: "simulation-only · phase10_holdout_unseen",
    change: [
      "Added causal lateral/altitude and velocity state",
      "Added explicit reject/predict behavior for ambiguous fallback geometry",
      "Froze source-aware uncertainty calibration on development evidence"
    ],
    before: "Phase 9 solved each camera observation independently and its reprojection-based uncertainty was far too confident.",
    after: "AegisT10 could protect an existing track from ambiguous fallback geometry and report better-calibrated uncertainty.",
    metrics: [["Holdout lateral MAE", "0.0277 m"], ["Holdout altitude MAE", "0.0157 m"], ["Substantial-win gate", "Not passed"]],
    finding: "The holdout did not reproduce the big development point-error gain because all 15 usable measurements were already high-quality ArUco detections. The useful result was uncertainty: normalized residual medians were 0.65 lateral and 0.52 altitude. The unchanged front end still missed five of 20 truth-visible frames.",
    source: "Phase 10 frozen holdout result",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/blob/phase10-temporal-metric-perception/docs/phase10_frozen_holdout_result.md"
  }
};
