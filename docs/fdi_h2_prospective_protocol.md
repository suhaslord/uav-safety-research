# AegisLand FDI-H2 — prospective fault-timing and actuator-retention stress test

**Preregistered before any H2 Webots simulation or analysis. Frozen rule; no tuning after test outcomes.**
This follow-on is separate from [FDI-H1](fdi_h1_heldout_result.md). H1 achieved 40/40 on a fixed 10.0-s complete motor shutdown; those H1 command seeds are **not** used here. H2 explores where that narrow success fails.

## Research question and hypotheses
Does the **unchanged H1 gyroscope threshold/quadrant detector** accurately distinguish healthy flight and identify which actuator has failed if (a) the disruption occurs at a different time, (b) the motor retains some commanded speed, and (c) gyroscope measurements are noisy?

The hypotheses are **not** criteria for altering the detector: full loss should be easier than partial loss; more additive gyro noise should increase false or missed alerts. Report contrary results and every failure.

## Fixed plant and faults
- Bitcraze Crazyflie Webots at `7e93752dbc803af2488c1db46bb79b3da55f5d8c`; Webots R2025a-ubuntu22.04 with downloaded image digest recorded. This is **simulation only**.
- Use the stock velocity-command profile generator/PID and an H2-specific copy of AegisLand's telemetry logger, with **only** the configurable fault onset and applied motor-speed retention changes. No recovery controller.
- Motor cases: healthy (no injection), and full commanded motor-speed loss (retention = 0.0) or half commanded motor-speed retention (retention = 0.5) on each of motors 1–4. **Half motor-speed command is NOT equivalent to half thrust**.
- Fault onset: **9.0 or 13.0 seconds**. All other parameters fixed. Stop simulator at onset+1.0 seconds, avoiding unrelated late-stage simulation divergence.
- Freeze eight *new* command seeds: **89, 97, 101, 103, 107, 109, 113, 127**. They have no overlap with the H1 seeds.
- Per seed × onset: one healthy trajectory and eight faulted trajectories. **8 × 2 × 9 = 144 raw Webots trajectories**, including 16 independent healthy trajectories and 128 fault trajectories. Healthy traces must not be duplicated and treated as new independent experiments.

## Frozen detector and outcome evaluation
- Same H1 rule: 3 consecutive samples with **|p|≥2.0 rad/s AND |q|≥0.75 rad/s**; first alert's p/q sign maps to motors: (++):1, (+−):2, (−−):3, (−+):4. Healthy if no alert.
- Inputs: measured gyroscope p/q only. The known injection time is used **only to define the scoring window**; the detector is not told the fault time. Altitude is used as **evaluation-only censor**, not a detector feature.
- Evaluate through **onset +0.70 seconds** or until simulated altitude <0.50m after onset. A pre-onset alert **always counts as an error**, even if it happens to predict the correct eventual motor label. No alert before censor is healthy.
- **Primary outcome:** five-class balanced accuracy **for half-motor-speed retention** in the *noise-free* condition, pooled over both onset values. This includes the 16 healthy traces as the reference negative class and 64 retention=0.5 faulty traces.
- **Secondary outcomes (fixed reporting):** balanced accuracy for full loss with those same healthy controls; both endpoints broken down by onset; fault detection rate, correct isolation rate, false alert rate, confusion matrix, and median delay on correct *post-onset* alarms. Report case-level decisions for all 144 raw trajectories.
- **Sensor-noise sensitivity only:** offline additive zero-mean independent Gaussian perturbations on gyro p and q at σ = **0, 0.2, 1.0 rad/s**, using a fixed SHA256-derived seed per trace/noise condition. This is *not* noise in the physical simulation or a study of actual sensor hardware. Perturbed reuses of one trajectory are **not** new independent samples. The **primary** analysis uses σ=0, even if it fails.
- Benchmark against the always-healthy trivial rule: five-class balanced accuracy 0.2 in any fully present five-class stratum.
- **Sampling unit:** command seed; 2,000 paired cluster-bootstrap replicates (RNG seed 20261013), sampling all conditions and onset times for each selected seed together. A degenerate interval must not be described as proof of certainty.

## Evidence/integrity gate
- The GitHub runner must generate **exactly 144 non-empty CSV traces**, each with consistent seed, motor, onset, retention, and monotone timestamps. All numeric measurement and command fields must be finite **in the scored prefix**; data after scoring cutoff must not be used to improve the result.
- Save the raw CSV files, trace SHA-256 manifest, full scenario predictions per noise condition, confusion matrices, bootstrap intervals, environment (Python packages), pinned source commit and Docker image digest, exact workflow SHA and IDs as one immutable workflow artifact.
- Workflows must fail on incomplete scenarios; the predeclared detector parameters are not modified in response to failed test outcomes.
- If the Webots plant becomes physically nonsensical before scoring cutoff, *flag it as an invalid scenario and disclose it* instead of quietly excluding it.

## Interpretation limits
This tests command-seed variation, simulated motor-speed retention and *offline* gyro noise **within a single Crazyflie Webots model**. It does not validate real flight, controller recovery, independent vehicle physics, robustness to true turbulence, or a controller-safe response. The H1-onset and original-pilot results influenced the research question; the H2 test scenario list and primary outcome are frozen before H2 test outcomes.

If a methodology bug is found after H2 results are observed, disclose, mark that analysis exploratory, and use new untouched data for any corrected confirmatory test. Do **not** claim H2 results were independent of H1.
