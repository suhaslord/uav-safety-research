# FDI robustness follow-up — preregistration draft (not executed)

Status: **design only**. This is a new experiment, not a reinterpretation of the completed 70-trace held-out study. Do not report any performance numbers until independently generated traces, logs and checksums are archived.

## Objective
Test whether the frozen causal gyroscope detector from `evaluate_fdi_early.py` maintains pre-contact fault isolation when the simulation departs from its original deterministic, full-shutdown, fixed-onset setting.

## Preserve the completed result
- Do not change the existing evaluator, frozen thresholds (|p| ≥ 2.0 rad/s; |q| ≥ 0.75 rad/s; persistence 3), quadrant mapping, original held-out splits, or archived traces.
- Do not use original protected seeds 53, 59, 61, 67, 71, 73, 79, 83 for choosing perturbations, fixing thresholds, or designing a better detector.
- Use a distinct experiment namespace and output directory, with a new manifest and CI job.
- Define all scenarios and seed assignments before generating results. Record any changes in a dated amendment, not by silently editing the plan.

## Proposed fixed-factor challenge matrix
Each condition needs one healthy control and four motor-specific fault scenarios on paired command seeds.
1. **Sensor perturbation:** deterministic seeded zero-mean gyroscope noise, at 0, 0.05 and 0.15 rad/s standard deviation per axis; independently drawn at each sample, applied to detector inputs only. Preserve unperturbed ground-truth telemetry separately.
2. **Fault severity:** motor effectiveness retained at 0%, 25% and 50% of commanded motor output. Implement in the actuator/plant interface, not by relabeling a complete shutdown.
3. **Fault onset:** 9.5, 10.0 and 10.5 s, provided each onset precedes the predeclared physically meaningful censor boundary. If not, mark the trial unscorable and report its count.
4. **Command variation:** fresh command seeds disjoint from all original 14 seeds. Freeze a new seed list before execution.

These are separate one-factor-at-a-time studies against a common control, **not** a full factorial design. Any interactions require a separately preregistered experiment.

## First executable challenge (phase R1: motor effectiveness)

Freeze **new command seeds 89, 97, 101, 103, 107, 109, 113, 127** before any R1 runs. These eight seeds are disjoint from all 14 seeds used in the historical study. This is a fixed, convenience-generated set of seeded command programs, **not a representative sample of real-world flights**. Do not drop, replace or select seeds after seeing their outcomes.

A deterministic, **unexecuted** scenario generator and its synthetic tests are now committed at `experiments/ornik_fdi_webots/fdi_robustness_plan.py` and `test_fdi_robustness_plan.py`. To write the exact prospective manifest once (refuses overwrite), use:

```bash
python experiments/ornik_fdi_webots/fdi_robustness_plan.py \\
  --output results/fdi_r1/scenario_plan.json
```

Before executing any Webots R1 run, archive that file, its printed SHA-256, the controller and evaluator hashes and a reviewed actuation/validity instrumentation implementation. **The generator creates no flight or simulator data.**

The first self-contained challenge varies **only actuator effectiveness**, with sensor noise fixed at zero and onset at **t=10.0 seconds**. For each new seed, execute one healthy control, four complete shutdowns (0% retained effectiveness), and four 50%-retained-effectiveness cases: **8 seeds × 9 distinct scenarios = 72 complete simulations**. The same command history must be used for all nine scenarios sharing a seed. Score the full-shutdown and partial-loss strata separately against their shared healthy controls; **do not mix them into one 72-trace five-class accuracy** or treat each fault condition as an independent command-seed cluster. The full-shutdown arm is a new baseline on *new* seeds, not a rerun or replacement of protected FDI-H1 test data.

Before running R1, pin and log the new controller source, plant image digest, configuration and exact scenario JSON manifest; implement and test the *applied* motor fraction at the actuator. The manifest generator is a **design artifact only**, not proof that any simulation ran.

## Correcting historical instrumentation gaps for R1

The original controller's `cmd_m1`–`cmd_m4` columns are **pre-injection PID output**, not post-fault motor velocities. The original `finite()` also masks nonfinite upstream sensor readings by replacing them with zero. In the new controller, preserve separate columns for `requested_m1`–`requested_m4` and `applied_m1`–`applied_m4`, explicitly log fault effectiveness, onset and sensor-validity flags/counters, and **fail or classify invalid traces when nonfinite upstream readings occur**. Validate fault actuation from logged applied commands; do not claim observed rotor speed if the simulator does not expose an independent tachometer.

A separately preregistered onset-time study must use a **0.70-second evaluation window relative to each fault onset** (and earlier contact censor when applicable), instead of reusing the fixed 10.70 s stop for different onset times. This prevents changes in observation-window duration from confounding onset effects. Do not modify the historical FDI-H1 scoring rule.

## Measurement and failure handling
- Primary: five-class trajectory-level balanced accuracy by challenge stratum; report confusion matrix, healthy false-alert rate, motor detection/isolation rates and median latency when defined.
- Independent sampling unit: command seed; bootstrap whole paired seed clusters, not telemetry samples.
- Count and report incomplete, censored-before-fault, physically unstable and invalid traces separately. Do not discard difficult trials without disclosure.
- Record physical plausibility checks: altitude, finite rates, time monotonicity, contact/censor event, commanded vs realized motor effectiveness and complete timestamped trace duration.
- Archive controller version, pinned simulator version, environment configuration, perturbation RNG seed, scenario matrix, per-trace SHA-256 manifest and evaluation script hash.
- Distinguish *detected before simulator contact* from *flight-safe*. No real-world safety claim.

## Execution gate
Before running: independent reviewer must confirm the simulator actually applies partial actuator faults, verify noise units and placement, freeze fresh command seeds, and confirm that the onset/censor design gives an observable pre-contact window. If any check fails, stop and record the blocker; do not tune using the completed protected-test results.

## Interpretation
Report negative findings prominently, including false positives and simulator failures. The original perfect result is a narrow deterministic-simulation feasibility result and must not be pooled with the new robustness study.
