# Professor Reply Packet

If a professor or researcher replies to the outreach email and asks what the project is, send them this repository plus the shortest relevant context below.

## 30-second description

AegisLand is a simulation-first study of **confidence-aware safety supervision for autonomous UAV landing**. The current experiment asks whether a lightweight supervisory layer can reduce unsafe simulated touchdowns when perception becomes noisy, biased, stale, or uncertain, while measuring the cost in holds and aborts.

The project deliberately begins with an interpretable surrogate perception model so the safety decision layer can be studied before adding a computer-vision front end.

## What already exists

- reproducible planar simulation
- baseline landing controller
- controlled perception-stress profiles
- interpretable risk estimator
- `PROCEED / HOLD / ABORT` supervisor
- Monte Carlo experiment runner
- episode-level data export
- confidence intervals
- threshold sweep
- automated tests and CI
- preregistered Phase 1 protocol

## What I would most value from a researcher

I am not asking someone to design the project for me. The highest-value feedback would be one of:

1. **Baseline fairness:** Is the baseline comparison defensible?
2. **Perception model:** What failure mode is missing from the surrogate stress model?
3. **Controls:** Is the supervisory intervention structure reasonable for the question being asked?
4. **Statistics:** Should the architecture comparison use paired identical episode seeds?
5. **Phase 2:** What is the simplest defensible image-based perception task to add next?

## Suggested links to send

- Main overview: [`README.md`](../README.md)
- Research plan: [`research_plan.md`](research_plan.md)
- Frozen Phase 1 protocol: [`preregistration_v1.md`](preregistration_v1.md)
- Reviewer questions: [`reviewer_guide.md`](reviewer_guide.md)
- Methodology: [`methodology.md`](methodology.md)

## Short reply template

```text
Thank you for getting back to me. I’ve started the project and put the current simulation, methodology, and experiment plan here:

https://github.com/suhaslord/uav-safety-research

I’m currently freezing the Phase 1 experiment before running the full dataset. The question I’d most value your opinion on is: [ONE QUESTION SPECIFIC TO THEIR FIELD].

Even a quick criticism of the methodology would help a lot. I’m trying to make the project rigorous rather than just make the result look good.

Thank you again,
Suhas
```

Use **one** technical question per reply. Do not send every question at once.