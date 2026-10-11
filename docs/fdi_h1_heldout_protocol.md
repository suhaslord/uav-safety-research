# AegisLand FDI-H1 — early motor fault isolation before simulated impact

**Status: corrected protocol, numerical outcome pending.** This document replaces the initial long-window comparison in this PR after review of the preceding 15-simulation pilot. Keep that failed methodological idea in the record; do not claim that a late, unstable simulation can prove flight-relevant fault detection.

## Research question

With the **same** pinned Webots/Bitcraze Crazyflie plant and full single-motor shutdown at 10 seconds, can an **interpretable causal gyroscope rule** correctly identify the motor **before the simulation becomes unstable** on previously unseen command seeds?

This is only a narrow *within-simulator* pre-contact feasibility study, not a reproduction of Garg/Ornik, a flight-safety experiment, or a hardware result.

## Why the first attempt was revised

The earlier 15-simulation exploratory pilot (command seeds 11, 23, 47) produced 0.661 window accuracy and 0.491 balanced accuracy on just one held-out command seed. Reviewing its actual CSV logs showed that some full-motor-loss trajectories subsequently exhibit physically absurd altitude and angular-rate values (e.g., hundreds of metres altitude and thousands of rad/s angular rate). The first draft of PR #175 evaluated windows at 14–22 seconds, **after** this divergence. Its MLP results would mainly test simulator failure artifacts. The late-window analysis was withdrawn *before looking at outcomes on the newly reserved seeds*.

The replacement rule was inspired by the **already inspected** pilot seeds 11, 23, 47. Therefore those seeds must **not** be presented as protected independent evaluation.

## Frozen rule and evaluation

- Simulator: Bitcraze `crazyflie-simulation` at commit `7e93752dbc803af2488c1db46bb79b3da55f5d8c`; Webots Docker `cyberbotics/webots:R2025a-ubuntu22.04` with full image digest recorded.
- Same stock quadrotor dynamics/PID and AegisLand logging controller; 24 s of trajectory saved for audit, but **only pre-contact data scored**.
- Fault class: healthy (0) or fully disable one motor (1–4) at exactly t=10.0 s; identical commanded motion for all five scenarios sharing a command seed.
- Each timestep, based exclusively on measured gyro `p` and `q`, mark a candidate if **|p| ≥ 2.0 rad/s and |q| ≥ 0.75 rad/s** for **3 consecutive samples**. The first qualifying alert wins. Healthy = no alert. At the first alert, quadrant `(+,+)→1, (+,-)→2, (-,-)→3, (-,+)→4`; a pre-onset alert is an error.
- Stop scoring at t=10.70 s or when simulated altitude falls below **0.50 m after onset**, whichever comes first. Altitude is **not** fed into the detector: it is used only to censor the outcome, preventing post-contact instabilities from contaminating results. This is not a stand-in for a real contact detector.
- Rule developed from preceding pilot and **frozen before obtaining or interpreting data for independent command seeds 53,59,61,67,71,73,79,83**.

## Data and statistics

Run 14 command seeds × five conditions = **70 complete simulated trajectories**:

- Source/pilot development: 11, 23, 29, 31.
- Descriptive development: 41, 47.
- **Protected test: 53, 59, 61, 67, 71, 73, 79, 83** — 40 trajectories, eight independent command-seed clusters. Seed 47 was seen in the previous pilot and is intentionally excluded.
- **Primary endpoint:** five-class trajectory-level balanced accuracy (healthy and four motor classes).
- Secondary, all reported: healthy false-alarm rate, fault detection fraction, correct motor isolation fraction, per-class recall, confusion matrix, median latency for correctly detected faults.
- **Uncertainty:** 2,000 bootstrap resamples of the eight complete command-seed clusters (all five paired fault conditions sampled together), RNG seed 20261012. Do not treat each timestep as an independent observation.
- Negative baseline: always healthy → 20% balanced accuracy on this balanced evaluation.
- Raw 70 CSVs and SHA-256 input manifest, rule source SHA, exact git commit, results and environment archived. Fail if any file missing, any input malformed, or simulated fault onset mismatches the definition.

## Honest interpretation limits

Even a 100% score here would not imply a robust motor-fault detector: this deterministic scenario is unusually simple, complete loss in a single plant has a strong gyroscope signature, and only a few independent command patterns are sampled. The motor-sign map may be particular to this plant/controller. There is no injected sensor noise, partial loss, different drone, real-world turbulence, recovery policy, or controlled flight experiment. The frozen initial MLP late-time result is **not** part of this study's evidence.

Report failure and success cases as observed, including raw data and the eight-cluster confidence interval. Do not publish a safety or generalization claim beyond this narrow protocol. No independent Phase 26 landing-pad validation is implied.

## Workflow

`.github/workflows/fdi-heldout-seed-validation.yml` generates all 70 trajectories and uses:

```bash
python experiments/ornik_fdi_webots/evaluate_fdi_early.py \
  --input-dir experiments/ornik_fdi_webots/heldout_run/raw \
  --output-dir experiments/ornik_fdi_webots/heldout_run/report
```

If workflows fail, fix infrastructure while preserving the holdout labels and frozen rule. If **analysis** fails, disclose what happened rather than silently changing thresholds or reusing the test as a new development set.
