# Ornik neural FDI: recovered PX4/Gazebo evaluation

The frozen detector transfers poorly to the held-out simulator cases. This is a completed negative-result experiment, not a flight-readiness result.

## Evidence and repair

[Original run 31658568350](https://github.com/suhaslord/uav-safety-research/actions/runs/31658568350) generated five development traces and all 24 held-out traces on August 13, 2026. Its evaluation shell check expected 48 arguments, while 24 pairs of `--trace PATH --summary PATH` require 96. The workflow now derives that count from the frozen configuration.

On September 5, the retained artifact was downloaded and all 318 files were checked against its original SHA-256 receipt, with zero mismatches. The original evaluator then ran successfully on the original frozen detector and standardizer. No training, controller, thresholds, cases, or trace summaries were changed. The nine existing benchmark contract tests pass.

## Held-out result

Each row contains four episodes. Degradation is one minus actuator effectiveness.

| Degradation | Thrust scale | Detected | Correct isolation | Terminal failures | Non-recoveries |
|---|---:|---:|---:|---:|---:|
| Nominal | 1.00 | 0 false alarms | — | 0/4 | 0/4 |
| 25% | 1.00 | 0/4 | 0/4 | 0/4 | 0/4 |
| 50% | 1.00 | 0/4 | 0/4 | 4/4 | 0/4 |
| 50%, unseen model mismatch | 1.45 | 0/4 | 0/4 | 0/4 | 0/4 |
| 75% | 1.00 | 2/4 | 0/4 | 4/4 | 1/4 |
| 100% | 1.00 | 1/4 | 1/4 | 4/4 | 4/4 |

Across 20 fault cases, three were detected and one was correctly isolated. No pre-fault or nominal false positives were recorded. Four nominal episodes cannot establish a low false-alarm rate: the 95% Wilson interval for 0/4 is approximately 0–49%.

## Interpretation limits

- These are genuine PX4/Gazebo ULog traces, with the detector evaluated offline. It was not integrated into the control loop. No hardware was used.
- The frozen recovery metric checks re-entry into an envelope. It can label an episode recovered even if the episode has a terminal failure; the 50% degradation row shows this limitation. Finite recovery times must never be interpreted as successful mission recovery.
- The 1.45 thrust-scale case partly offsets the injected effectiveness loss. It is one explicitly frozen mismatch direction, not general robustness to unknown plants.
- Four cases per group and one trained detector are too small for strong generalization claims. The resource-bounded method reproduction does not reproduce the paper's full training scale or its post-fault controller.
- This report preserves the failed outcomes and original definitions. Any next experiment should specify new metrics and hypotheses before accessing new held-out traces.

[Episode results](../results/ornik/recovered-2026-09-05/heldout_episode_results.csv), [grouped estimates and intervals](../results/ornik/recovered-2026-09-05/summary_by_severity.csv), and [recovery provenance](../results/ornik/recovered-2026-09-05/recovery_receipt.json) accompany the report.
