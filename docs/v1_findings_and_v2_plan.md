# V1 Findings and V2 Research Plan

## V1 main experiment

The preregistered Phase 1 experiment used 500 episodes per profile/controller cell (5,000 total simulated landing episodes) with seed 2026.

### Key result

The confidence-aware supervisor reduced unsafe touchdowns in severe degradation, but did so by becoming excessively conservative.

- **Mixed degradation**: baseline unsafe touchdown rate 82.8%; supervised unsafe touchdown rate 0.0%, but supervised abort rate 100.0% and success rate 0.0%.
- **Occlusion**: baseline unsafe touchdown rate 35.8%; supervised unsafe touchdown rate 2.6%, but supervised abort rate 94.6% and success rate 2.8%.
- **Low light**: baseline and supervised unsafe touchdown rates were both 0.4%, while supervised success dropped from 99.6% to 79.6% because of a 20.0% abort rate.
- **Clean / blur**: both systems remained near-perfect, indicating the simulator is not simply forcing failures in every condition.

## Interpretation

V1 supports only part of the original hypothesis.

The supervisor can suppress unsafe touchdowns under severe perception stress, but the current threshold-based design is not useful enough because it sacrifices landing availability. In low-light conditions it can also intervene without producing a measurable safety gain.

The research question should therefore evolve from:

> Can uncertainty-aware supervision reduce unsafe landings?

into:

> Can a safety supervisor reduce unsafe landings while preserving acceptable landing availability?

This safety-availability tradeoff is the primary focus of V2.

## Threshold sweep finding

Threshold sweeps were performed after the fixed V1 experiment.

### Occlusion

Across hold thresholds 0.58–0.76 and abort thresholds 0.82–0.94:

- success remained only 2.0%–5.5%
- unsafe touchdown rate remained 1.5%–3.0%
- abort rate remained 92.5%–95.5%

The least-unsafe tested point was hold=0.76, abort=0.82 with 1.5% unsafe touchdowns, 3.5% success, and 95.0% aborts.

### Mixed

Every tested threshold combination produced:

- 0% success
- 0% unsafe touchdowns
- 100% aborts

Therefore, **simple threshold retuning is not sufficient** to solve the availability problem.

## V2 hypothesis

A supervisor that uses temporal evidence and state-aware persistence, rather than reacting strongly to isolated high-risk observations, will preserve more valid landing attempts while maintaining substantially lower unsafe-touchdown rates than the no-supervisor baseline.

## V2 design

V2 should remain interpretable and should not jump directly to an opaque learned policy.

### 1. Temporal risk filtering

Maintain an exponentially weighted risk estimate:

```text
filtered_risk_t = alpha * instantaneous_risk_t
                + (1 - alpha) * filtered_risk_(t-1)
```

This reduces reactions to one-frame spikes.

### 2. Persistence requirement

Require risk to remain above a threshold for multiple consecutive frames before escalating from PROCEED to HOLD or from HOLD to ABORT.

This directly tests whether temporal consistency improves the safety-availability tradeoff.

### 3. Hysteresis

Use separate entry and exit thresholds so the supervisor does not rapidly switch between states.

Example concept:

```text
PROCEED -> HOLD when filtered risk > H_enter
HOLD -> PROCEED when filtered risk < H_exit
HOLD -> ABORT only after persistent severe risk
```

with H_exit < H_enter.

### 4. Near-ground weighting

Risk should matter more near touchdown, but altitude should not cause premature aborts when there is still enough time to recover.

### 5. Hold budget redesign

V1's hold budget can convert long uncertainty periods into automatic aborts. V2 should track whether confidence is recovering during a hold before deciding to abort.

## V2 ablations

Compare at least four systems using identical episode seeds:

1. baseline: no safety supervisor
2. V1: instantaneous threshold supervisor
3. V2a: temporal filtering only
4. V2b: temporal filtering + persistence + hysteresis

Optional fifth system:

5. V2c: V2b + altitude-aware escalation

## V2 success criteria

Do not define success as zero unsafe touchdowns.

For occlusion, a useful target region would be a configuration that:

- reduces unsafe touchdown rate substantially below the 35.8% baseline
- preserves a meaningful fraction of successful landings
- avoids the ~95% abort behavior seen in V1

The exact operating point should be chosen from a reported safety-availability frontier, not selected after looking only at one favorable metric.

## Scientific rules

- V1 results remain immutable as the original experiment.
- V2 results must be reported separately.
- Do not overwrite V1 with tuned thresholds.
- Preserve raw episode-level outputs.
- Use fixed seed lists for paired comparisons where possible.
- Report failures and negative results, not only the best configuration.
