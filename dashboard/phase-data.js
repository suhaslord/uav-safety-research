const PHASES = {
  phase1: {
    label: "Phase 1 · Aegis V1",
    era: "Foundation",
    title: "Could a separate safety check stop a bad landing?",
    lede: "We started with a simple comparison. One simulated controller trusted the perception estimate directly; the other had a supervisor that could HOLD or ABORT when the estimate looked risky. Both were tested in clean, blurred, dark, occluded, and mixed conditions.",
    status: "Frozen original experiment",
    role: "simulation-only · 5,000 episodes",
    change: [
      "Let the supervisor HOLD or ABORT when confidence dropped",
      "Defined unsafe touchdown before the test started",
      "Kept safety and availability as separate outcomes"
    ],
    before: "The landing controller acted on the perception estimate by itself.",
    after: "A separate supervisor could stop or pause the landing when the frozen risk threshold was crossed.",
    metrics: [["Mixed unsafe", "82.8% → 0%"], ["Mixed abort", "0% → 100%"], ["Main lesson", "Safety ≠ availability"]],
    finding: "The supervisor removed unsafe touchdowns in the hardest mixed condition, but there was a catch: it aborted every single run. Phase 1 made the tradeoff hard to miss. Refusing to finish can make a system look safe without making it useful.",
    source: "Phase 1 preregistration + V1 findings",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/blob/phase10-temporal-metric-perception/docs/v1_findings_and_v2_plan.md"
  },

  phase2: {
    label: "Phase 2 · Aegis V2",
    era: "Foundation",
    title: "What if one ugly frame does not get the final say?",
    lede: "V2 stopped reacting to every bad-looking measurement immediately. The supervisor tracked risk across time and waited for the problem to persist before escalating.",
    status: "Fixed V2 result",
    role: "simulation-only · 7,500 episodes",
    change: [
      "Smoothed risk across recent observations",
      "Waited for repeated evidence before escalating",
      "Allowed HOLD behavior to recover instead of staying latched"
    ],
    before: "A single severe observation could cause a long hold or an abort.",
    after: "The system needed sustained risk before it escalated.",
    metrics: [["Mixed abort", "100% → 0%"], ["Occlusion abort", "94.6% → 0%"], ["Mixed unsafe", "84.8%"]],
    finding: "V2 fixed the all-abort behavior from V1. It also exposed the next problem. A sensor can be wrong in a steady, believable way, and smoothing does not automatically reveal that kind of bias.",
    source: "V2 frozen results",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/blob/phase10-temporal-metric-perception/docs/v2_results.md"
  },

  phase3: {
    label: "Phase 3 · Aegis V3",
    era: "Foundation",
    title: "Give the vision estimate an independent check.",
    lede: "V3 added a second reference estimate. When vision and that reference disagreed for long enough, the disagreement itself became useful evidence instead of letting one self-consistent sensor stream judge its own answer.",
    status: "Frozen held-out result",
    role: "simulation-only · 10,000 episodes",
    change: [
      "Added an independent reference estimator",
      "Measured disagreement between the two estimates",
      "Used a correction only when the confidence evidence supported it"
    ],
    before: "The system had one corrupted observation stream and no independent comparison.",
    after: "Persistent visual bias could show up as disagreement with a second estimate.",
    metrics: [["Mixed success", "97.6%"], ["Mixed unsafe", "2.4%"], ["Occlusion unsafe", "1.4%"]],
    finding: "This was the first large architecture gain. The useful change was not another smoother; it was the second source of evidence. Some errors that looked perfectly consistent from inside the vision stream became obvious once another estimate disagreed with them.",
    source: "V3 frozen results",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/blob/phase10-temporal-metric-perception/docs/v3_results.md"
  },

  phase4: {
    label: "Phase 4 · Naming gap",
    era: "Foundation",
    title: "Phase 4 was never a standalone experiment.",
    lede: "The early work was named V1, V2, and V3. Numbered phases pick up again at Phase 5. Rather than fill the blank with a made-up milestone, the archive leaves the gap where it actually occurred.",
    status: "No standalone phase",
    role: "historical lineage · no invented result",
    change: [
      "Keep the original V1/V2/V3 naming",
      "Leave the missing phase missing",
      "Show the gap as part of the project history"
    ],
    before: "The early experiments used version names: V1, V2, and V3.",
    after: "The next recorded numbered experiment is Phase 5.",
    metrics: [["Standalone result", "None"], ["Invented metrics", "0"], ["Archive policy", "Gap preserved"]],
    finding: "There is no result to rescue here. Phase 4 did not exist as a separate experiment, so the timeline keeps that fact visible instead of smoothing it over.",
    source: "Repository research checkpoint",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/blob/phase10-temporal-metric-perception/docs/research_checkpoint_2026-08-10.md"
  },

  phase5: {
    label: "Phase 5 · Robustness",
    era: "Perception + robustness",
    title: "Stress V3, then make perception work from pixels.",
    lede: "Phase 5 widened the stress test with new seeds, stronger degradation, reference-quality changes, dropout, and persistent bias. It also introduced a 96×96 synthetic landing-pad image benchmark. For the first time, the perception stack could fail because of what was in an image rather than only because an abstract state value had been corrupted.",
    status: "Completed robustness study",
    role: "simulation-only · stress + synthetic images",
    change: [
      "Ran five unseen seed families across broader stress settings",
      "Varied reference quality and dropout",
      "Added a synthetic landing-pad renderer and pixel estimator"
    ],
    before: "V3 had a strong frozen result, but its perception input was still an abstract corrupted measurement.",
    after: "The controller faced a wider stress test and received its first measurements derived from rendered images.",
    metrics: [["Mixed V3 success", "97.6% mean"], ["Mixed V3 unsafe", "2.4% mean"], ["Image valid outputs", "100% — too willing"]],
    finding: "V3 stayed strong in the wider simulation sweeps. The image estimator revealed a different weakness: it almost always returned an answer, even when the answer was poor. Its confidence was too willing.",
    source: "Phase 5 results",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/blob/phase10-temporal-metric-perception/docs/phase5_results.md"
  },

  phase6: {
    label: "Phase 6 · Image perception",
    era: "Perception + robustness",
    title: "Run the landing loop on measurements taken from images.",
    lede: "Phase 6 joined the pieces into one simulated image pipeline: calibration, tracking, reacquisition, velocity estimation, redundant checks, and the frozen Aegis supervisor all ran from synthetic image sequences.",
    status: "Frozen held-out result",
    role: "synthetic-image simulation",
    change: [
      "Converted pixels into controller observations",
      "Handled track loss, abstention, and reacquisition",
      "Estimated velocity from images and added a near-ground cross-check"
    ],
    before: "The strongest controller result still depended on abstract state estimates.",
    after: "The simulated landing decision came from a complete image-sequence pipeline.",
    metrics: [["Mixed success", "92%"], ["Mixed unsafe", "7%"], ["Bad-frame rejection", "Still weak"]],
    finding: "The overall system improved even though frame-level confidence still failed to catch many bad images. That distinction mattered: the architecture could survive some perception mistakes without actually knowing, frame by frame, which readings were wrong.",
    source: "Phase 6 frozen results",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/blob/phase10-temporal-metric-perception/docs/phase6_results.md"
  },

  phase6b: {
    label: "Phase 6B · Selective confidence",
    era: "Perception + robustness",
    title: "Do not force one confidence score to judge every part of the image.",
    lede: "Phase 6B split confidence for lateral position from confidence for altitude and scale. If the image was useful for one quantity but weak for the other, the system could keep the useful measurement and replace only the unreliable one.",
    status: "Frozen held-out result",
    role: "synthetic-image simulation · component selective",
    change: [
      "Separated lateral confidence from altitude confidence",
      "Capped altitude observability when the pixel scale became weak",
      "Allowed one geometry component to abstain without discarding the other"
    ],
    before: "A single global score could reject good lateral information because altitude was weak, or vice versa.",
    after: "Each geometry component was judged on its own evidence.",
    metrics: [["Mixed success", "99%"], ["Mixed unsafe", "1%"], ["Occlusion unsafe", "4%"]],
    finding: "Splitting the confidence decision worked better than treating the image as all good or all bad. It produced the strongest frozen synthetic-image landing result in this part of the project, while low light and mixed lateral rejection still showed clear weaknesses.",
    source: "Phase 6B frozen results",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/blob/phase10-temporal-metric-perception/docs/phase6b_results.md"
  },

  phase7: {
    label: "Phase 7 · External validity stress",
    era: "External validation",
    title: "Make the simulator less convenient.",
    lede: "Phase 7 stopped trying to squeeze out another clean headline score. Instead, it attacked assumptions that had made the earlier simulator easier: synchronized sensors, fresh state, independent faults, quick actuators, simple drag, and tidy disturbances.",
    status: "Audited development milestone",
    role: "simulation-only · development evidence",
    change: [
      "Added GNSS-like lateral sensing and barometer/range-like vertical sensing",
      "Introduced delays, stale state, queues, and shared faults",
      "Added actuator lag, rate limits, nonlinear drag, and colored disturbances"
    ],
    before: "Earlier experiments still had relatively clean timing and simplified dynamics.",
    after: "Sensors arrived on different schedules, readings could age or fail together, and the plant model became harder.",
    metrics: [["Factorial", "200 episodes"], ["New stresses", "Bias / dropout / latency"], ["Outcome", "Weak cells preserved"]],
    finding: "The point of Phase 7 was to find brittle cases, and it did. Those weak cells stayed in the record. A lower-looking result was more useful here than another polished score because it showed which assumptions had been doing hidden work.",
    source: "Phase 7 PR #10",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/pull/10"
  },

  phase8: {
    label: "Phase 8 · Higher-fidelity validation",
    era: "External validation",
    title: "Put the internal simulator next to PX4 and Gazebo.",
    lede: "Phase 8 defined a common trace format so an AegisLand run and a PX4 SITL + Gazebo run could be compared under thresholds that were fixed in advance.",
    status: "Merged external-simulator evidence",
    role: "simulation-only · PX4/Gazebo",
    change: [
      "Standardized the trace format and recorded provenance",
      "Compared distributions, correlations, and latency behavior",
      "Pinned the PX4 SITL + Gazebo evidence harness"
    ],
    before: "The main conclusions still came from AegisLand's own simulator family.",
    after: "Internal traces could be checked directly against a trace from a different simulator stack.",
    metrics: [["Close", "1"], ["Mismatch", "9"], ["Overall", "diagnostic_mismatch"]],
    finding: "Nine comparisons disagreed and only one was close. We kept that mismatch instead of tuning it away. The result said the internal model was not yet externally representative, which was exactly the kind of information this phase was meant to surface.",
    source: "Phase 8 PX4/Gazebo PR #12",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/pull/12"
  },

  phase9: {
    label: "Phase 9 · External perception",
    era: "External validation",
    title: "Run perception on the Gazebo camera frames themselves.",
    lede: "Phase 9 kept the raw Gazebo camera bytes and hashes, fixed the camera-pose provenance, and ran ArUco/quad detection with PnP geometry on the first valid external-camera trace.",
    status: "Audited seen-camera evidence",
    role: "simulation-only · external_perception_seen",
    change: [
      "Saved raw camera payloads with SHA-256 hashes",
      "Used ArUco detection with a fixed quad fallback",
      "Tied metric geometry to camera pose and an explicit uncertainty value"
    ],
    before: "PX4/Gazebo had exercised navigation behavior, but not the AegisLand camera estimator itself.",
    after: "The project had traceable measurements produced from simulator-camera frames.",
    metrics: [["Visible observations", "25 / 25"], ["Lateral MAE", "0.998 m"], ["Altitude MAE", "1.520 m"]],
    finding: "Detection succeeded on the seen trace, but the metric geometry was not accurate enough. The seven quad-fallback measurements produced the largest errors. That pointed to a concrete next job: stop ambiguous fallback geometry from damaging an otherwise good track.",
    source: "Phase 9 PR #13",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/pull/13"
  },

  phase10: {
    label: "Phase 10 · AegisT10",
    era: "Current frontier",
    title: "Use recent history to protect the metric estimate, then freeze it.",
    lede: "AegisT10 kept the Phase 9 camera front end but added causal state over time. Its uncertainty calibration was fit on development data and frozen before a single run on a new 11-segment PX4/Gazebo holdout.",
    status: "Frozen holdout complete",
    role: "simulation-only · phase10_holdout_unseen",
    change: [
      "Tracked lateral position, altitude, and velocity through time",
      "Rejected or predicted through ambiguous fallback geometry",
      "Calibrated source-aware uncertainty on development evidence before the holdout"
    ],
    before: "Phase 9 solved each camera observation on its own, and the reprojection uncertainty was much too confident.",
    after: "AegisT10 could protect an existing track from ambiguous geometry and report uncertainty that was better calibrated.",
    metrics: [["Holdout lateral MAE", "0.0277 m"], ["Holdout altitude MAE", "0.0157 m"], ["Substantial-win gate", "Not passed"]],
    finding: "The big point-error gain from development did not repeat on the holdout because all 15 usable measurements were already high-quality ArUco detections. The more useful result was calibration: normalized residual medians were 0.65 laterally and 0.52 in altitude. The unchanged front end still missed five of 20 truth-visible frames.",
    source: "Phase 10 frozen holdout result",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/blob/phase10-temporal-metric-perception/docs/phase10_frozen_holdout_result.md"
  }
};