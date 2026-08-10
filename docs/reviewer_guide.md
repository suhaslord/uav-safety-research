# Technical Reviewer Guide

AegisLand is an independent student research project. This page is for professors, graduate students, engineers, and other technical reviewers who are willing to spend a few minutes challenging the methodology.

## What I am asking reviewers to evaluate

I am **not** asking whether the project looks impressive. I am asking whether the research design is defensible.

The most useful feedback would address one or more of these questions:

### 1. Is the research question scoped correctly?

The current question is intentionally narrow: whether an uncertainty-aware supervisor can reduce unsafe simulated touchdowns under controlled perception stress.

- Is the question narrow enough to answer rigorously?
- Is there a more useful dependent variable than unsafe-touchdown rate?
- Is the baseline fair?

### 2. Is the uncertainty model meaningful?

The current perception layer is a surrogate stress model rather than a real camera model.

- Are the chosen degradation families useful for an initial study?
- What failure modes should be added before moving to image-based perception?
- Is the current confidence/uncertainty representation too tightly coupled to the supervisor?

### 3. Is the safety supervisor methodologically fair?

The supervisor combines interpretable risk components and maps them to `PROCEED`, `HOLD`, or `ABORT`.

- Does this create an unfair advantage over the baseline?
- What ablation would best show which risk component matters?
- What alternative baseline should be included?

### 4. Are the statistics strong enough?

The project preserves episode-level data and reports repeated Monte Carlo trials with confidence intervals.

- Is the planned 5,000-episode preregistered run sufficient for the intended claim?
- Should results be paired by identical episode seeds across architectures?
- Which effect-size measure would be most informative?

### 5. What would make Phase 2 scientifically stronger?

The next phase is planned around synthetic landing-pad imagery with controlled corruption.

- Which image-estimation task would be most defensible for a student project?
- How should confidence calibration be evaluated?
- What would be the simplest meaningful temporal-consistency test?

## Files to read first

If you have only 5–10 minutes:

1. [`README.md`](../README.md)
2. [`research_plan.md`](research_plan.md)
3. [`preregistration_v1.md`](preregistration_v1.md)
4. [`methodology.md`](methodology.md)

If reviewing code, the highest-value files are:

- [`src/uav_safety/perception.py`](../src/uav_safety/perception.py)
- [`src/uav_safety/supervisor.py`](../src/uav_safety/supervisor.py)
- [`src/uav_safety/simulator.py`](../src/uav_safety/simulator.py)
- [`src/uav_safety/experiment.py`](../src/uav_safety/experiment.py)

## Feedback format

Short feedback is completely fine. Even something like this is useful:

```text
Biggest methodological weakness:

One thing I would change before collecting the main result:

One paper/method I should read:
```

Issues or pull requests are welcome, and feedback can also be sent privately.

## What I will do with criticism

Substantive feedback will be documented in the research log. If it arrives before the preregistered main run, I may amend the protocol transparently. If it arrives after data collection begins, it will be treated as a recommendation for the next version rather than retroactively changing the experiment.

That distinction is intentional: the goal is to learn how to do research correctly, not just make the hypothesis win.