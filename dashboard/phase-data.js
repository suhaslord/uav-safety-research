const PHASES = {
  phase1: {
    label: "Phase 1 · Aegis V1",
    era: "Foundation",
    title: "Could a separate safety check stop a bad landing?",
    lede: "A supervisor could stop a risky landing. Could it also finish one?",
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
    finding: "Mixed unsafe touchdowns fell from 82.8% to 0%, but every mixed run aborted.",
    source: "Phase 1 preregistration + V1 findings",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/blob/main/docs/v1_findings_and_v2_plan.md"
  },

  phase2: {
    label: "Phase 2 · Aegis V2",
    era: "Foundation",
    title: "What if one ugly frame does not get the final say?",
    lede: "V2 waited for risk to persist instead of reacting to one bad frame.",
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
    finding: "Mixed aborts fell to 0%. Steady sensor bias still escaped the smoother.",
    source: "V2 frozen results",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/blob/main/docs/v2_results.md"
  },

  phase3: {
    label: "Phase 3 · Aegis V3",
    era: "Foundation",
    title: "Give the vision estimate an independent check.",
    lede: "A second estimate checked the vision stream for persistent bias.",
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
    finding: "Mixed unsafe touchdowns fell to 2.4%, with 97.6% landing success in simulation.",
    source: "V3 frozen results",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/blob/main/docs/v3_results.md"
  },

  phase4: {
    label: "Phase 4 · Naming gap",
    era: "Foundation",
    title: "Phase 4 was never a standalone experiment.",
    lede: "There is no standalone Phase 4. The numbering resumes at Phase 5.",
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
    finding: "The archive keeps the gap. No result was invented.",
    source: "Repository research checkpoint",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/blob/main/docs/research_checkpoint_2026-08-10.md"
  },

  phase5: {
    label: "Phase 5 · Robustness",
    era: "Perception + robustness",
    title: "Stress V3, then make perception work from pixels.",
    lede: "V3 faced stronger stress. A first image estimator entered the loop.",
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
    finding: "V3 held up in wider simulation sweeps. The image estimator answered bad frames too confidently.",
    source: "Phase 5 results",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/blob/main/docs/phase5_results.md"
  },

  phase6: {
    label: "Phase 6 · Image perception",
    era: "Perception + robustness",
    title: "Run the landing loop on measurements taken from images.",
    lede: "A simulated landing loop ran from synthetic image sequences.",
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
    finding: "Mixed success reached 92%, but frame confidence still missed many bad images.",
    source: "Phase 6 frozen results",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/blob/main/docs/phase6_results.md"
  },

  phase6b: {
    label: "Phase 6B · Selective confidence",
    era: "Perception + robustness",
    title: "Do not force one confidence score to judge every part of the image.",
    lede: "Lateral and altitude confidence were judged separately.",
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
    finding: "Mixed success reached 99%. Low light and lateral rejection remained weak.",
    source: "Phase 6B frozen results",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/blob/main/docs/phase6b_results.md"
  },

  phase7: {
    label: "Phase 7 · External validity stress",
    era: "External validation",
    title: "Make the simulator less convenient.",
    lede: "The simulator gained stale sensors, shared faults, actuator lag, and rougher dynamics.",
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
    finding: "Weak cells exposed assumptions the earlier clean simulator had hidden.",
    source: "Phase 7 PR #10",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/pull/10"
  },

  phase8: {
    label: "Phase 8 · Higher-fidelity validation",
    era: "External validation",
    title: "Put the internal simulator next to PX4 and Gazebo.",
    lede: "A common trace format put AegisLand beside PX4 SITL and Gazebo.",
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
    finding: "Nine comparisons disagreed; one was close. The mismatches stayed in the record.",
    source: "Phase 8 PX4/Gazebo PR #12",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/pull/12"
  },

  phase9: {
    label: "Phase 9 · External perception",
    era: "External validation",
    title: "Run perception on the Gazebo camera frames themselves.",
    lede: "Gazebo camera frames replaced abstract perception inputs.",
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
    finding: "Detection worked on the seen trace. Seven ambiguous quad fallbacks drove the largest errors.",
    source: "Phase 9 PR #13",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/pull/13"
  },

  phase10: {
    label: "Phase 10 · AegisT10",
    era: "Current frontier",
    title: "Use recent history to protect the metric estimate, then freeze it.",
    lede: "Causal tracking and frozen calibration faced a new PX4/Gazebo holdout.",
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
    finding: "Point-error gains did not repeat. Calibration improved, but five of 20 visible frames were missed.",
    source: "Phase 10 frozen holdout result",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/blob/main/docs/phase10_frozen_holdout_result.md"
  }
};