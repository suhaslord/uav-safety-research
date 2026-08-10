# AegisLand V3 Design

## Why V3 exists

V2 solved the excessive-abort behavior of V1 but did not solve the `mixed` profile. In the 500-episode paired V2 evaluation, the mixed unsafe-touchdown rate was 84.2% for the baseline and 84.8% for V2.

The dominant unresolved failure is persistent lateral perception bias. A single observation stream can be internally consistent while still being consistently wrong, so temporal smoothing alone cannot identify the offset.

V3 tests whether an independent, imperfect state estimate adds enough information to detect and compensate persistent bias.

## Architecture

```text
corrupted vision ----> temporal filter -----------+
                                                   |
independent lower-rate reference -----------------+--> bias/disagreement model
                                                   |
                                                   v
                                            redundant fusion
                                                   |
                                                   v
                                            V3 supervisor
                                                   |
                                         PROCEED / HOLD / ABORT
```

## Independent reference estimator

The reference estimator is intentionally imperfect:

- lower update rate than vision
- independent zero-mean position and velocity noise
- occasional missed updates
- uncertainty growth between updates
- no access to controller decisions
- no perfect-state output

It is an abstract simulation instrument, not a model of one specific physical sensor.

## RNG isolation

V3's reference estimator uses a dedicated random-number stream derived from the episode seed. The legacy environment stream remains responsible for initial state, vision corruption, and simulated disturbances.

This matters because adding a new estimator should not silently change the random vision/wind sequence being compared.

## Persistent-bias estimator

On fresh reference updates, V3 records the lateral disagreement between raw vision and the independent reference. A rolling window estimates the mean offset.

Bias correction is gated by three conditions:

1. enough samples have been collected;
2. the estimated offset is large enough to matter;
3. the mean offset is statistically distinguishable from random disagreement.

This prevents ordinary clean-condition noise from being converted into a fake correction.

## State fusion

When the reference estimate is usable, V3:

1. subtracts the confidence-gated bias estimate from filtered vision;
2. blends the corrected lateral estimate with the independent reference;
3. uses much smaller reference weights for altitude and velocity;
4. raises fused confidence modestly when independent information is available;
5. grows caution when the reference becomes stale.

The lateral channel receives the strongest redundant-estimator weight because persistent lateral bias is the measured V2 failure mode.

## Safety logic

V3 keeps V2's temporal principles:

- smoothed risk
- persistent evidence before intervention
- hysteresis before releasing a hold
- abort only under sustained near-ground danger

But V3 distinguishes **explained disagreement** from **unexplained disagreement**.

If vision/reference disagreement is stable enough to produce a confident bias estimate, V3 treats it as a correctable estimation problem rather than automatically escalating risk. If disagreement remains large and unexplained near touchdown, the supervisor can hold or abort.

## Guardrails against misleading results

V3 must not be declared successful because it merely aborts more often.

Primary endpoint:

- unsafe touchdown rate under `mixed`

Required secondary checks:

- success rate under `mixed`
- abort rate under `mixed`
- clean/blur regression
- low-light availability
- occlusion unsafe-touchdown rate
- intervention count
- final bias estimate and bias confidence

The benchmark also reports paired episode effects, including how many baseline/V2 unsafe episodes become V3 successes and how many previously successful episodes become unsafe.

## Current scientific status

V3 is implemented but **not yet validated**. No performance claim should be added to the README or paper until the development run and frozen evaluation are completed.

This repository remains simulation-only and is not flight-control software.
