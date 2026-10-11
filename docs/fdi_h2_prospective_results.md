# AegisLand FDI-H2 — prospective within-simulator stress results

**Evidence:** 2026-10-11 UTC. **Outcome:** completed and independently replayed. This is **not** aircraft testing, control recovery, a neural-network evaluation or a flight-safety result.

[Pre-registered protocol](fdi_h2_prospective_protocol.md) · [GitHub Actions run #38115058084](https://github.com/suhaslord/uav-safety-research/actions/runs/38115058084) · [Raw artifact #11693248745](https://github.com/suhaslord/uav-safety-research/actions/runs/38115058084/artifacts/11693248745) · [Original H1 result](fdi_h1_heldout_result.md)

## The question

Would the *unchanged*, causal sign-and-magnitude gyroscope rule from FDI-H1 still identify a single motor loss when the **commanded motor speed** was partially retained, fault onset was shifted, and the offline gyro signal was perturbed?

The frozen rule required three consecutive samples with |p|≥2.0 rad/s and |q|≥0.75 rad/s, then classified the motor by the p/q sign quadrant. Alerts before the injected onset are incorrect. The simulated evaluation stops 0.70 seconds after onset or at the predeclared post-onset altitude censor (<0.50 m). No tuning was performed using H2 outcomes.

## Verified result

**Primary endpoint (50% motor-command-speed retention, no added gyro noise): 100% five-class, temporally valid balanced accuracy**, across 80 cases (16 healthy controls + 64 affected-motor cases), consisting of 8 independent command seeds paired over 2 onset times and 5 true classes. All 64 motor cases isolated correctly; 16/16 healthy controls did not alert. Median correct detection delay: **0.280 s**.

| Offline additive gyro noise σ (rad/s) | Full commanded-speed loss (retention 0) | Partial speed loss (retention 0.5) |
|---|---:|---:|
| 0.0 | **100.00%** | **100.00%** |
| 0.2 | **100.00%** | **100.00%** |
| 1.0 | **93.75%** | **96.25%** |

These are **balanced accuracies**, not probabilities of safe flight. Every group has 80 scored cases, but there are only **eight** independently generated command histories; cases sharing a command seed are paired. The online simulator itself did *not* receive noisy gyro measurements: noise was added **offline** when scoring the saved traces. Each noise variant is a reused trace, not a new trajectory.

### High-noise errors, retained without filtering

At **σ = 1.0 rad/s**, full-loss condition:

- Balanced accuracy **93.75%**, eight-cluster bootstrap percentile interval **[90.0%, 97.5%]**.
- **59/64** faulty cases isolated correctly. There were five motor-*identification* mistakes: one true motor 1 predicted motor 2; three true motor 3 predicted motor 4; one true motor 4 predicted motor 3. **All 64 fault cases alerted**; healthy false alarms **0/16**.
- By onset, five-class balanced accuracy was **97.5% at 9 s** and **90.0% at 13 s**.

At **σ = 1.0 rad/s**, half-retention condition:

- Balanced accuracy **96.25%**, eight-cluster bootstrap percentile interval **[92.5%, 98.78%]** (rounded).
- **61/64** faulty cases isolated correctly. Three identification mistakes: one true motor 1 predicted motor 2, and two true motor 4 predicted motor 3. **All 64 fault cases alerted**; healthy false alarms **0/16**.
- By onset, accuracy was **92.5% at 9 s** and **100% at 13 s**.

No case in these runs had a premature alert. The median correctly classified fault alert delay was **0.280 s** for every tested group. This uniformity is typical of a small deterministic simulation and is not evidence of real-world latency stability.

**Uncertainty:** The clean and low-noise eight-cluster bootstrap intervals collapse to [100%, 100%] because all observed clusters succeeded. That is a property of the finite sample, **not** proof of universally perfect accuracy. Independence is limited to generated command histories; vehicle physics and the deterministic failure signature are shared across all scenarios.

## Evidence and integrity audit

The uploaded workflow artifact contains:

- **144 physical-simulation CSV files**: eight previously unseen command seeds (89, 97, 101, 103, 107, 109, 113, 127), two fault times (9 s and 13 s), one healthy condition and eight motor×retention conditions per seed/time combination.
- **432 per-case decisions**: the same 144 raw traces scored at three fixed offline noise levels.
- **54,072 raw telemetry rows**, the reported metric groups, paired-bootstrap results, a trace SHA-256 manifest, Git checkout SHA, dependency versions and Webots Docker image digest.
- Original artifact ZIP SHA-256: `3c76f9bbcb92254d96521065f0c20e7a363ee7160b482f20cc41f991c27a70d5`.
- Workflow checkout SHA: `5ed639aa107d6534885023af5804584615ce5f9a`.

**Independent check:** Downloaded ZIP and verified all **144/144 CSV SHA-256 hashes**, monotonic time and scenario coverage. Directly replayed **432/432 decisions** from raw gyroscope readings with independently reconstructed seeded offline noise, then recalculated all six aggregate balanced accuracies. No disagreement found. This checks evidence integrity and statistical replay, **not the physical validity of the simulator**.

Reproduce the deeper audit using the **unmodified** archived ZIP:

```bash
python scripts/audit_fdi_h2_artifact.py aegisland-fdi-h2-prospective-evidence.zip \\
  --evaluator-source experiments/ornik_fdi_webots/evaluate_fdi_h2.py \\
  --expected-archive-sha256 3c76f9bbcb92254d96521065f0c20e7a363ee7160b482f20cc41f991c27a70d5
```

The independent auditor also rejects duplicate ZIP member names, malformed/reordered CSV headers, and corrupted pre-onset Boolean markers. Its optional external-ZIP checksum prevents a self-consistent but substituted ZIP from being mistaken for the archived original. The local evaluator file is checked against the SHA-256 embedded in the report; use the historical evaluator bytes, not a later modified analysis script. A different legitimate artifact will have its **own** ZIP fingerprint. These are integrity protections, not new flight results. Raw Actions artifacts have a **90-day retention period**; preserve a verified copy outside GitHub before expiry.

## Independent trace-timing and paired-control integrity

A further **read-only independent check of the original 144-trace ZIP** found **72 trajectories with 313 samples** (9-second onset; recorded through 10.016s) and **72 with 438 samples** (13-second onset; recorded through 14.016s), accounting for all **54,072 samples**. Every recorded timestamp occupies its expected 32ms position; none of the 144 original traces has a missing or shifted sample. The 16 healthy controls match all **128 paired faulty-condition trajectories exactly before the corresponding injected onset**, comparing position, gyroscope and pre-injection motor-command fields. There are 281 pre-onset samples per 9-second case and 406 per 13-second case.

The independent auditor now also enforces these paired-input and sample-grid integrity conditions and rejects altered published rule/noise/bootstrap metadata. The pairing result supports controlled *within-simulator* comparisons. It does **not** mean 128 independent vehicles or flight tests, nor does it measure post-fault applied motor speed.

## Measurement and instrumentation boundaries

The frozen H2 Webots controller applies a motor-command-speed multiplier in its actuator loop, but the archived `cmd_m1`–`cmd_m4` columns record **pre-fault PID requests**, not the resulting `motor.setVelocity()` inputs or independently measured rotor RPM. The analysis therefore verifies the **declared scenario controls and their recorded gyroscope response** under the pinned controller; it does **not** independently measure the realized motor speed or aerodynamic thrust.

The controller's `finite()` routine also substitutes **zero** when an upstream sensor reports a nonfinite number, without a flag in the CSV. Finite archived values cannot demonstrate that no such substitution occurred. A future study must log requested *and applied* actuator signals, raw sensor validity/counters, and any invalid samples before making stronger fault-severity or sensor-robustness claims.

## What this means and what must come next

The frozen simple detector discriminated complete and partial command-speed reductions at two specified fault times in a single simulator. The **high-noise wrong-motor predictions** are a genuine observed weakness. The earlier 15-trace learned MLP pilot scored only 49.1% balanced accuracy and produced physically unrealistic late dynamics; H1/H2 deliberately constrain conclusions to an early pre-impact window rather than using that divergence.

This study still lacks realistic faults and independent validation: the setup has one Crazyflie plant, two fault-onset times, sudden faults, commanded motor-speed retention rather than verified partial thrust loss, no turbulence, no new sensor physics, no alternative vehicle dynamics, and no controller response. The 100% clean condition is not a performance claim for those untested cases.

**Recommended next experiment:** A separate, *preregistered* detection-coverage study on genuinely different dynamics and noise injected during state evolution—not another sweep of offline perturbations of these same traces. Before any new protected evaluation, compare the unchanged detector with simple gyro-magnitude and model-residual baselines; reserve fresh seeds/conditions and report missed faults, false alarms, and incorrect motor IDs. Do not change H2 thresholds using these protected outcomes and then relabel the same data confirmatory.

**Status:** the historical H2 experiment and numerical report are complete. The study remains a **draft PR pending outside review** and is not part of a deployed flight-control system. Phase 26 independent landing-pad dataset admission is a separate open issue; H2 provides no progress on that gate.
