# AegisLand V3 Research Plan

## Motivation

V1 showed that a static confidence/risk threshold can dramatically reduce unsafe touchdowns only by becoming unusably conservative.

V2 showed that temporal smoothing, persistence, and hysteresis recover availability and modestly improve occlusion performance, but do not solve persistent systematic bias in the mixed profile.

The next experiment should therefore test whether the limitation is **missing information**, not poor threshold tuning.

## Research question

**Can disagreement between two independent simulated state estimates detect persistent visual bias and reduce unsafe simulated UAV touchdowns under mixed perception degradation without causing the excessive abort behavior seen in V1?**

## Hypothesis

A supervisor that compares a corrupted vision estimate against an independent lower-bandwidth reference estimate will identify systematic lateral disagreement that a single-stream temporal filter cannot observe.

Expected outcome:

- clean / blur: no meaningful performance loss
- low-light: preserve V2 availability
- occlusion: retain or improve V2 safety
- mixed: reduce unsafe touchdown rate relative to baseline and V2
- avoid V1-style near-universal aborts

## Important design rule

V3 must not be given access to ground-truth state.

The second estimator should also be noisy and imperfect. The scientific question is whether **independent error structure** adds useful information, not whether perfect information solves the task.

## Proposed architecture

```text
             corrupted vision estimate
                       |
                       v
                temporal filter
                       |
                       +------------------+
                                          |
independent reference estimate ----------+--> disagreement model
                                          |
                                          v
                                  confidence fusion
                                          |
                                          v
                                  Aegis V3 supervisor
                                          |
                            +-------------+-------------+
                            |             |             |
                         PROCEED        HOLD          ABORT
```

## Reference-estimator model

For the first simulation-only V3 experiment, implement a deliberately simple independent reference estimate with:

- lower update rate than vision
- independent zero-mean position / velocity noise
- no shared lateral bias with the visual stream
- occasional missing updates
- uncertainty that grows between updates

This is not intended to represent one specific physical sensor. It is an abstract redundant-estimation model used to test the information-theoretic value of independent state evidence.

## Disagreement features

Candidate inputs to the V3 supervisor:

1. absolute lateral disagreement
2. altitude disagreement
3. velocity disagreement
4. normalized disagreement by combined uncertainty
5. persistence of disagreement over time
6. visual confidence
7. visual dropout history
8. altitude / proximity to touchdown

## State machine

V3 should preserve V2's temporal behavior:

- smoothed risk
- persistence before HOLD
- persistence before ABORT
- hysteresis for recovery

But add a new concept:

**persistent cross-estimator disagreement**

A single disagreement should not cause an abort. Persistent disagreement, especially near touchdown, should increase the system's caution.

## Ablation study

Compare at least:

1. baseline
2. Aegis V1
3. Aegis V2
4. V3 with redundant estimate but no disagreement persistence
5. V3 full system

Optional later ablations:

- no confidence input
- no temporal smoothing
- no altitude weighting
- perfect reference estimate as an upper-bound diagnostic only

The perfect-reference case must never be reported as the primary V3 result.

## Primary endpoint

Unsafe touchdown rate under `mixed` degradation.

## Secondary endpoints

- success rate
- abort rate
- intervention count
- unsafe touchdown rate under occlusion
- false intervention rate under clean / blur
- disagreement-detection precision and recall, if bias events are labeled in simulation

## Experimental protocol

Development run:

- 30 paired episodes per condition
- new development seed

Frozen V3 evaluation:

- 500 paired episodes per architecture/profile cell
- new seed not used during tuning

Do not use seed 2026 or seed 2027 for the final V3 evaluation.

## Success criteria

V3 should not be considered successful merely because it reduces unsafe touchdowns by aborting everything.

A useful V3 result should satisfy all of the following qualitatively:

1. materially lower unsafe touchdown rate than V2 under mixed degradation
2. substantially higher success / availability than V1 under mixed degradation
3. no meaningful regression in clean and blur conditions
4. retain the availability improvements V2 achieved in low-light
5. make its tradeoff explicit rather than hiding failures behind a single score

## Research integrity

V1 and V2 results are fixed historical experiments.

Any new architecture or tuned parameters belong to V3. Results that fail the hypothesis should remain documented rather than being overwritten.

The goal is not to manufacture better numbers. The goal is to identify what information and decision structure are actually required for safer simulated autonomous landing under corrupted perception.
