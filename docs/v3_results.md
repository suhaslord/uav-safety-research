# AegisLand V3 Frozen Results

## Status

V3 is a **frozen, held-out simulation result**.

Development used seed `3031`. The V3 architecture was then frozen before the final evaluation. The frozen benchmark used seed `424242`, 500 paired episode seeds per profile/architecture cell, and produced 10,000 total simulated landing episodes.

The dataset passed `scripts/validate_v3_frozen.py`, including checks for row count, architecture/profile coverage, paired seeds, duplicate seeds, outcome consistency, required metadata, and isolated V3 reference-estimator randomness.

## Primary result

The primary V3 endpoint was unsafe touchdown rate under the `mixed` degradation profile.

| Architecture | Success | Unsafe touchdown | Abort |
|---|---:|---:|---:|
| Baseline | 15.8% | 84.2% | 0.0% |
| Aegis V1 | 0.0% | 0.0% | 100.0% |
| Aegis V2 | 16.0% | 84.0% | 0.0% |
| **Aegis V3** | **97.6%** | **2.4%** | **0.0%** |

For V3, the 95% Wilson interval was:

- success: **95.85% to 98.62%**
- unsafe touchdown: **1.38% to 4.15%**

Relative to the baseline, V3 reduced the observed mixed-profile unsafe-touchdown rate by **81.8 percentage points**, or approximately **97.1% relative**.

This result is simulation-only and should not be interpreted as a real-aircraft safety claim.

## Occlusion result

| Architecture | Success | Unsafe touchdown | Abort |
|---|---:|---:|---:|
| Baseline | 65.4% | 34.6% | 0.0% |
| Aegis V1 | 2.6% | 3.4% | 94.0% |
| Aegis V2 | 66.4% | 33.6% | 0.0% |
| **Aegis V3** | **98.6%** | **1.4%** | **0.0%** |

For V3, the 95% Wilson interval was:

- success: **97.14% to 99.32%**
- unsafe touchdown: **0.68% to 2.86%**

Relative to baseline, V3 reduced the observed occlusion unsafe-touchdown rate by **33.2 percentage points**, or approximately **96.0% relative**.

## Easy-condition regression checks

| Profile | V3 success | V3 unsafe | V3 abort | Mean interventions |
|---|---:|---:|---:|---:|
| clean | 100.0% | 0.0% | 0.0% | 0.500 |
| blur | 100.0% | 0.0% | 0.0% | 0.152 |
| low light | 100.0% | 0.0% | 0.0% | 0.058 |

The frozen run therefore showed no outcome-rate regression in the three easier profiles. V3 did introduce some non-terminal interventions, especially under `clean`, which remains a useful efficiency metric for later work.

## Paired episode effects

Because all architectures used paired episode seeds, aggregate rate differences can be checked against episode-level transitions.

### Mixed

- baseline unsafe -> V3 success: **410 episodes**
- baseline success -> V3 unsafe: **1 episode**
- V2 unsafe -> V3 success: **409 episodes**
- V2 success -> V3 unsafe: **1 episode**

### Occlusion

- baseline unsafe -> V3 success: **166 episodes**
- baseline success -> V3 unsafe: **0 episodes**
- V2 unsafe -> V3 success: **161 episodes**
- V2 success -> V3 unsafe: **0 episodes**

These paired transitions are important because the aggregate improvement was not produced by simply swapping one set of failures for another set of equal size.

## What changed from V2

V2 used one corrupted visual stream plus temporal smoothing. That architecture could reduce random noise and tolerate short dropouts, but it could not reliably identify a persistent lateral measurement bias.

V3 added an independent, imperfect, lower-rate reference estimate with its own RNG stream. V3 then used persistent cross-estimator disagreement to estimate visual bias, apply confidence-gated lateral correction, and fuse the two estimates before control and safety assessment.

The frozen result supports the project hypothesis that **independent error structure can provide information that a single-stream temporal filter cannot recover from persistent systematic bias** in this simulation.

## Important limitations

The result does **not** establish real-world UAV safety.

Current limitations include:

1. planar simulated dynamics rather than a full 6-DOF aircraft model;
2. abstract perception stress profiles rather than calibrated camera physics;
3. an abstract independent reference estimator rather than a modeled physical sensor;
4. synthetic wind/disturbance behavior;
5. one frozen evaluation seed family;
6. no real image-based landing-pad detector in V3;
7. no hardware or flight validation.

The strongest next scientific step is therefore not further threshold tuning. It is testing whether the result survives **multi-seed sensitivity analysis and a more realistic perception front end**.

## Reproduction

```bash
python scripts/run_v3_comparison.py --episodes 500 --seed 424242 --out results/v3_frozen
python scripts/validate_v3_frozen.py --out results/v3_frozen --seed 424242 --episodes 500
```

Expected validator result:

```text
V3 frozen result validation: PASS
seed: 424242
episodes per cell: 500
total rows: 10000
```

Raw episode-level data, aggregate summaries, paired effects, figures, and run metadata are committed under `results/v3_frozen/`.
