# AegisLand V3 Frozen Evaluation Protocol

## Status

Aegis V3 is frozen after the development experiment using seed `3031` and 30 paired episodes per profile/architecture cell.

The V3 algorithm, default configuration, perception profiles, dynamics, touchdown criteria, and reference-estimator configuration must not be changed before the frozen evaluation.

## Frozen code baseline

The V3 implementation evaluated here is the version merged to `main` in commit:

`7a8b7bf02b7852bebfe78988fe9803aa40949a13`

Any later documentation or result-validation utilities that do not change the simulator or controller are acceptable, but changes to the following files invalidate the freeze and require a new evaluation version:

- `src/uav_safety/simulator_v3.py`
- `src/uav_safety/supervisor_v3.py`
- `src/uav_safety/reference_estimator.py`
- `src/uav_safety/perception.py`
- `src/uav_safety/dynamics.py`
- `src/uav_safety/controller.py`
- `src/uav_safety/config.py`

## Development result

The development run used:

```bash
python scripts/run_v3_comparison.py --episodes 30 --seed 3031 --out results/v3_development
```

This run is for development only. It must not be presented as the primary V3 evaluation.

## Frozen primary evaluation

Use a seed not used for V1, V2, or V3 development:

```bash
python scripts/run_v3_comparison.py --episodes 500 --seed 424242 --out results/v3_frozen
```

Expected design:

- 5 perception profiles
- 4 architectures
- 500 paired episode seeds per profile
- 10,000 total simulation rows

Architectures:

1. baseline
2. Aegis V1
3. Aegis V2
4. Aegis V3

## Primary endpoint

`mixed` unsafe touchdown rate: Aegis V3 versus Aegis V2 and baseline.

## Secondary endpoints

- mixed success rate
- occlusion unsafe touchdown rate
- occlusion success rate
- clean/blur false-intervention behavior
- low-light regression
- abort rate
- mean intervention count
- final lateral error
- paired rescue/regression counts

## Interpretation rules

Aegis V3 is not considered successful merely for producing a low unsafe-touchdown rate. A result that achieves safety by returning to V1-style near-universal abort behavior is a failure of availability.

The frozen result should be interpreted using both aggregate rates and paired episode outcomes.

Do not alter parameters after seeing seed `424242` results and rerun the same seed as if it were still a held-out evaluation. Any algorithmic change after the frozen run becomes V4 or V3.1 and requires a new held-out seed.

## Important limitation

The V3 reference estimator is an abstract simulated independent state source. It samples the simulated state with independent noise, lower update frequency, dropouts, and growing uncertainty. It is not a validated model of any particular real-world sensor.

Therefore, the primary scientific claim is about the value of **independent error structure and redundant estimation in this simulation**, not about verified physical-aircraft performance.
