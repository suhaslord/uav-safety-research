# Methodology

## System abstraction

The simulator models a small UAV in a planar landing task with state:

`[horizontal position, altitude, horizontal velocity, vertical velocity]`

A PD landing controller receives a *perceived* state rather than ground truth.

## Perception stress model

The current model applies controlled combinations of:

- position noise
- velocity noise
- lateral bias
- observation dropout/staleness
- imperfect confidence

The named profiles (`blur`, `low_light`, `occlusion`, `mixed`) are shorthand stress-test conditions. They should **not** be interpreted as physically calibrated camera models.

## Safety supervisor

The supervisor computes an interpretable risk score using:

- reported confidence
- estimated positional uncertainty
- lateral landing error
- excessive descent rate
- observation dropout

The supervisor can:

1. `PROCEED` — use the nominal descent command.
2. `HOLD` — reduce descent while the perception estimate is uncertain.
3. `ABORT` — end the simulated landing attempt when risk is too high near the ground or remains high for too long.

This separation is intentional: the research focus is the **decision layer between perception and control**, not a claim that the underlying controller is flight-ready.

## Experimental comparison

Every degradation profile is evaluated with:

- **baseline:** ignores the supervisor and always attempts the landing.
- **supervised:** allows proceed/hold/abort decisions.

Each cell receives repeated randomized episodes with deterministic seeds.

## Primary safety outcome

`unsafe_touchdown_rate`

A touchdown is marked unsafe in the simulator if any of these exceed the predefined envelope:

- horizontal pad error
- horizontal speed
- vertical speed

The thresholds are simulation study parameters, not certification standards.

## Reproducibility

Run:

```bash
python scripts/run_experiments.py --episodes 100 --seed 2026
```

This writes:

- raw episode CSV
- aggregate summary CSV
- run metadata
- success-rate plot
- unsafe-touchdown-rate plot
- Markdown summary
