# Fault-indicator validation reference result

This note records the first validation pass requested after review of the UNM Crazyflie / Webots resilience benchmark. It uses the exact 1,000-sample Webots trajectory from the previously reviewed run and keeps the residual/uncertainty thresholds frozen rather than retuning them by fault severity.

## Frozen detector definition

- Residual indicator: 0.5 s rolling median normalized innovation squared (NIS).
- Residual threshold: **1.591346**, defined as 1.20 × the maximum nominal post-settling rolling-median NIS.
- Dropout indicator: radial position sigma from the Kalman covariance.
- Uncertainty threshold: **0.017617 m**, defined as 1.50 × the maximum nominal post-settling radial sigma.

## Detection results

| Fault | Severity | Result | First-alert latency |
|---|---:|---:|---:|
| Gaussian position noise | 0.04 m sigma | 30/30 detected | 0.024 s after 5 s detector arming |
| Gaussian position noise | 0.08 m sigma | 30/30 detected | 0.024 s after arming |
| Gaussian position noise | 0.16 m sigma | 30/30 detected | 0.024 s after arming |
| Gaussian position noise | 0.32 m sigma | 30/30 detected | 0.024 s after arming |
| Fixed +x bias | 0.05 m | not detected | n/a |
| Fixed +x bias | 0.10 m | not detected | n/a |
| Fixed +x bias | 0.20 m | detected | 0.384 s after 12 s onset |
| Fixed +x bias | 0.40 m | detected | 0.320 s after 12 s onset |
| Position dropout | 0.5 s | detected | 0.128 s |
| Position dropout | 1.0 s | detected | 0.128 s |
| Position dropout | 2.0 s | detected | 0.128 s |
| Position dropout | 4.0 s | detected | 0.128 s |

Noise is present for the entire run in the original experiment, so its latency is measured from the detector's 5 s arming point rather than from a later injection onset.

## Normal-maneuver false-positive audit

The frozen nominal trajectory produced **0/844 post-settling alert samples (0.000%)**. No alert occurred within ±0.75 s of any of the four commanded direction changes.

| Turn time | Alerts | Max rolling NIS | Margin below threshold |
|---:|---:|---:|---:|
| 10.0 s | 0/46 | 1.098 | 0.493 |
| 15.0 s | 0/47 | 1.262 | 0.330 |
| 20.0 s | 0/47 | 1.268 | 0.323 |
| 25.0 s | 0/47 | 0.712 | 0.879 |

## Interpretation boundary

This is still an **in-sample** no-fault check because the thresholds were calibrated using the same nominal trajectory. It should not be presented as a general false-alarm guarantee. The clean next experiment is a second no-fault Webots trajectory with different turn timings/speeds while freezing these thresholds. A mitigation comparison (for example, rejecting or down-weighting suspect measurements) should follow that holdout rather than precede it.

All results are simulation-only and do not claim physical-flight performance.
