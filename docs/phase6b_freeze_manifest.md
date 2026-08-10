# Phase 6B Freeze Manifest

## Freeze decision

Phase 6B is frozen for its preregistered held-out evaluation.

No confidence-threshold, controller, fusion, supervisor, renderer, temporal-tracker, velocity-filter, dynamics, or reference-estimator change may be made after this point and still be described as the same Phase 6B held-out evaluation.

If the held-out result reveals a weakness that motivates an algorithm change, that change becomes a new named revision with new held-out seeds.

## Frozen architecture

The evaluated architecture is:

```text
synthetic image sequence
        ↓
Phase 6 structured image estimator
        ↓
temporal tracking + reacquisition
        ↓
robust image-derived lateral velocity
        ↓
Phase 6B component confidence
   ├─ p_x_good
   └─ p_z_good
        ↓
component-wise abstention at 0.80 / 0.80
        ↓
Phase 6B redundant-fusion adapter
        ↓
frozen V3 safety supervisor
        ↓
landing controller + planar dynamics
```

The historical Phase 6 and V3 paths remain available as comparison architectures and are not overwritten.

## Frozen component-confidence definition

Phase 6B uses separate probabilities for lateral position and altitude accuracy:

- `p_x_good = P(|x_hat - x| <= 0.30 m)`
- `p_z_good = P(|z_hat - z| <= 0.85 m)`

The component calibrator is trained offline on condition-balanced, altitude-stratified synthetic frames spanning 0.25–8.0 m.

Runtime confidence features include image-derived raw confidence, geometry, apparent scale, component support, contrast, sharpness, scale-bin width, and deterministic interactions. Runtime landing episodes do not receive ground-truth state or degradation-condition labels through this calibrator.

Final altitude confidence is capped by the known synthetic scale observability:

`delta_z_bin = 35/h - 35/(h+1)`

`p_z_good <= min(1, 0.85 / delta_z_bin)`

This cap is simulation-specific and is not a claim about real-camera uncertainty.

## Frozen operating point

- lateral component threshold: `0.80`
- altitude component threshold: `0.80`
- temporal calibration seed: `616161`
- component calibration seed: `616161`
- temporal calibration samples per condition: `180`
- component calibration samples per condition: `280`
- image severity: `1.0`
- paired episode seeds within each condition: yes
- image/reference/environment RNG streams: isolated as documented
- frozen V3 supervisor: unchanged

The `0.80 / 0.80` gates were selected from the predeclared development risk/coverage grid before Phase 6B landing outcomes were used and were not retuned after development landing results.

## Algorithm source freeze

The last substantive Phase 6B confidence-algorithm change before this manifest was the scale-observability revision in commit:

- `841db55d27055093e727372be8cf6f60ce836396`

Subsequent commits before this manifest add tests, calibration reporting, development workflow/reporting, protocol documentation, and held-out workflow preparation. They do not retune the Phase 6B control or confidence operating thresholds.

The held-out workflow records its exact `GITHUB_SHA` in each result artifact, providing the final executable repository snapshot used for evaluation.

## Pre-freeze validation

All available unit/regression tests pass; the corrected development workflow reported 53 passing tests before the paired landing study.

### Component-confidence development audit

At the fixed 0.80 operating point:

- blur altitude: 18.7% coverage, 0% selected bad rate, 100% bad-altitude rejection recall;
- low-light altitude: 30.25% coverage, about 0.17% selected bad rate, 99.42% bad-altitude rejection recall;
- mixed altitude: 0.9% coverage, 0% selected bad rate, 100% bad-altitude rejection recall;
- clean and occlusion: 100% altitude coverage with 0% selected bad altitude estimates in the normal-sequence development benchmark.

A separate 5.8–8.0 m high-altitude stress audit retains a documented residual limitation: the selected clean/occlusion altitude subset contains roughly 12% bad altitude estimates even after the analytic observability correction.

### Corrected paired landing development audit

Using development seed `626262`, 30 episodes per condition/architecture:

| Condition | Phase 6B success | Phase 6B unsafe | Notes |
|---|---:|---:|---|
| clean | 100.0% | 0.0% | no regression |
| blur | 100.0% | 0.0% | no regression |
| low_light | 96.7% | 0.0% | one timeout |
| mixed | 96.7% | 3.3% | one vertical-speed unsafe touchdown |
| occlusion | 96.7% | 3.3% | matched established Phase 6 outcome rate |

The mixed unsafe touchdown had approximately `0.815 m/s` vertical speed against the unchanged `0.80 m/s` safety limit. It is preserved rather than tuned away.

Phase 6B remains substantially stronger than image-only temporal perception under mixed and occlusion degradation while providing far more meaningful component-wise abstention than the original Phase 6 scalar confidence layer.

## Held-out evaluation — preregistered and unseen at freeze

The following seeds are reserved and have not been used for tuning at the time of this manifest:

- landing: `868686`
- selective-perception audit: `878787`

Frozen landing evaluation:

- 5 image conditions
- 3 paired architectures
- 100 episodes per condition/architecture
- 1,500 landing episodes total

Frozen selective audit:

- 20 sequences × 100 frames per condition
- 10,000 frames total
- primary operating point: 0.80 / 0.80
- full predeclared risk/coverage grid retained as diagnostic reporting

## Interpretation commitment

The held-out result may be positive, neutral, or negative. It will be reported as observed. Phase 6B will not be retuned and rerun under the same held-out label after those seeds are exposed.

## Safety scope

This freeze covers a synthetic planar research simulation only. It does not validate physical UAV flight, real cameras, real-world landing control, or an operational autopilot.
