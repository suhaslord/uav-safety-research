# Aegis V2 Design

## Why V2 exists

The preregistered V1 experiment and threshold sweeps exposed a structural limitation:

- under **occlusion**, threshold changes still produced very high abort rates;
- under **mixed degradation**, every tested V1 threshold pair aborted every episode;
- under **low light**, V1 could suppress unsafe touchdowns but still discarded a meaningful fraction of otherwise successful landings.

This means the main V1 failure is not simply a poorly chosen scalar threshold. V1 reacts too directly to instantaneous confidence/uncertainty and has weak temporal reasoning.

## V2 hypothesis

> A temporal supervisor that requires persistent evidence, uses hysteresis, propagates state through short dropouts, and continues a cautious descent during temporary uncertainty will preserve more successful landings than V1 while retaining a substantial safety benefit under degraded perception.

This is a new hypothesis. V1 results remain frozen and must not be rewritten after V2 is evaluated.

## Architectural changes

### 1. Temporal risk filtering

V1 applies a risk score almost frame-by-frame. V2 keeps an exponentially smoothed risk estimate.

A short spike therefore matters less than sustained evidence.

### 2. Persistence gates

V2 does not enter HOLD or ABORT from a single bad frame.

- HOLD requires several consecutive high-risk observations or a dropout streak.
- ABORT requires sustained severe risk near the ground, a prolonged near-ground dropout, or failure to recover after a long hold.

### 3. Hysteresis

The threshold for leaving HOLD is lower than the threshold for entering HOLD.

This prevents rapid `PROCEED → HOLD → PROCEED → HOLD` oscillation around one cutoff.

### 4. Temporal consistency feature

V2 compares observed frame-to-frame lateral motion with the reported lateral velocity. Large disagreement adds risk.

This gives the supervisor information about whether measurements are dynamically self-consistent, not only whether a single confidence value is low.

### 5. Dropout propagation

V1 feeds repeated stale observations to the controller during dropouts.

V2 keeps a small temporal observation filter. During a short dropout, it propagates the previous filtered state using velocity instead of freezing the state estimate.

### 6. Confidence-dependent smoothing

When a fresh observation returns, V2 blends it with the filtered state. Higher-confidence measurements are trusted faster; lower-confidence measurements are smoothed more strongly.

### 7. Cautious descent instead of near-stop

V1 HOLD uses a very small descent rate and can remain stuck long enough to cascade into aborts.

V2 HOLD uses a cautious descent rate while the temporal state estimate attempts to recover. This is still only a simulation behavior and must not be interpreted as a recommendation for a physical aircraft.

## What is held constant

To make the comparison meaningful, V2 keeps the same:

- planar dynamics model;
- initial-state distribution;
- wind/gust process;
- touchdown safety envelope;
- perception profiles;
- landing controller gains;
- maximum simulation time.

The comparison script uses **paired random seeds** so Baseline, V1, and V2 encounter the same episode-level randomness within a profile.

## Evaluation command

Smoke test:

```powershell
python scripts/run_v2_comparison.py --episodes 30 --seed 2027
```

Main comparison after tests pass:

```powershell
python scripts/run_v2_comparison.py --episodes 500 --seed 2027
```

This evaluates 5 profiles × 3 architectures × 500 paired episodes = **7,500 simulated episodes**.

## Primary evaluation criteria

V2 should not be called an improvement merely because unsafe touchdowns decrease.

For each profile report all three:

1. successful landing rate;
2. unsafe touchdown rate;
3. abort rate.

A useful V2 should move the safety-availability tradeoff, not simply replace unsafe landings with universal aborts.

## Important limitation: systematic bias

The `mixed` profile contains a persistent lateral measurement bias. A vision-only downstream supervisor may not be able to identify a constant absolute bias from the observation stream alone.

If V2 still struggles on `mixed`, that is scientifically useful evidence rather than a reason to silently change the stress profile. A later experiment can explicitly study **redundant sensing or bias observability** as a separate architectural intervention.

## Integrity rule

Do not tune V2 on the final evaluation seed and then report that same seed as an unbiased test.

If V2 parameters are tuned later:

- use separate development seeds;
- freeze parameters;
- evaluate once on new holdout seeds;
- preserve all raw outputs.
