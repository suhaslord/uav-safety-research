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
