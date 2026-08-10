# AegisLand V2 Results

## Experiment

Aegis V2 was evaluated against both the original Aegis V1 supervisor and an unsupervised baseline using paired simulation seeds.

Command used:

```bash
python scripts/run_v2_comparison.py --episodes 500 --seed 2027
```

This produced 7,500 simulated landing episodes across five perception profiles and three architectures.

## Main results

| Profile | Architecture | Success | Unsafe touchdown | Abort | Mean interventions |
|---|---:|---:|---:|---:|---:|
| clean | baseline | 1.000 | 0.000 | 0.000 | 0.000 |
| clean | aegis_v1 | 1.000 | 0.000 | 0.000 | 0.000 |
| clean | aegis_v2 | 1.000 | 0.000 | 0.000 | 0.000 |
| blur | baseline | 1.000 | 0.000 | 0.000 | 0.000 |
| blur | aegis_v1 | 0.998 | 0.000 | 0.002 | 0.282 |
| blur | aegis_v2 | 1.000 | 0.000 | 0.000 | 0.006 |
| low_light | baseline | 0.996 | 0.004 | 0.000 | 0.000 |
| low_light | aegis_v1 | 0.814 | 0.004 | 0.182 | 4.150 |
| low_light | aegis_v2 | 0.996 | 0.004 | 0.000 | 0.046 |
| occlusion | baseline | 0.662 | 0.338 | 0.000 | 0.000 |
| occlusion | aegis_v1 | 0.016 | 0.038 | 0.946 | 92.528 |
| occlusion | aegis_v2 | 0.694 | 0.306 | 0.000 | 9.438 |
| mixed | baseline | 0.158 | 0.842 | 0.000 | 0.000 |
| mixed | aegis_v1 | 0.000 | 0.000 | 1.000 | 124.462 |
| mixed | aegis_v2 | 0.152 | 0.848 | 0.000 | 55.700 |

## Interpretation

### 1. V2 successfully fixed V1 over-conservatism

V1 frequently converted uncertainty into excessive holds or aborts. V2 removed that failure mode:

- low-light abort rate: 18.2% -> 0%
- occlusion abort rate: 94.6% -> 0%
- mixed abort rate: 100% -> 0%

This is a clear architectural improvement in availability.

### 2. V2 preserved performance in clean and blur conditions

V2 did not introduce a measurable penalty in the easy conditions. Clean and blur both retained 100% successful landing rates in this experiment.

### 3. V2 modestly improved occlusion performance

Under occlusion:

- baseline unsafe touchdown rate: 33.8%
- V2 unsafe touchdown rate: 30.6%

and

- baseline success rate: 66.2%
- V2 success rate: 69.4%

This is a 3.2 percentage-point reduction in unsafe touchdowns and a corresponding 3.2 percentage-point increase in success.

The result suggests that temporal state handling and cautious intervention can recover some degraded observations without the catastrophic availability cost of V1.

### 4. V2 did not improve low-light safety

Low-light V2 matched the baseline almost exactly:

- 99.6% success
- 0.4% unsafe touchdown
- 0% abort

This means V2 fixed unnecessary intervention but did not create additional safety benefit in a condition where the baseline was already strong.

### 5. Mixed degradation remains unresolved

The most important negative result is the mixed profile:

- baseline unsafe touchdown rate: 84.2%
- V2 unsafe touchdown rate: 84.8%

V2 was slightly worse than the baseline within this finite sample.

This indicates that temporal filtering does not solve the dominant failure mode in the mixed condition.

## Why mixed degradation is fundamentally different

The mixed profile contains persistent lateral measurement bias in addition to noise, dropout, and reduced confidence.

A temporal filter can reduce random noise and survive short dropouts, but it cannot reliably distinguish:

> "the vehicle is laterally offset"

from

> "the perception system has a persistent lateral bias"

when both produce internally consistent observations over time.

This is an observability / identifiability problem rather than only a thresholding problem.

## V2 conclusion

Aegis V2 shows that temporal smoothing, persistence, and hysteresis can solve the excessive-abort behavior of V1 and modestly improve performance under occlusion. However, the architecture cannot correct persistent systematic perception bias using a single corrupted observation stream.

The next research question therefore becomes:

> Can a second independent simulated state estimate allow the safety layer to detect persistent visual bias and reduce unsafe touchdowns under mixed degradation without returning to excessive aborts?

## Scientific status

These results should be treated as the fixed V2 outcome for seed 2027 and 500 episodes per profile/architecture cell. Future architecture changes should be reported as V3 or later rather than replacing these numbers.
