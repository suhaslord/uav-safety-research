# Research Plan

## Working title

**AegisLand: Confidence-Aware Safety Supervision for Vision-Based Autonomous UAV Landing**

## Research question

Can a lightweight uncertainty-aware supervisory layer reduce unsafe simulated UAV landings caused by degraded visual perception without producing an impractically high intervention or abort rate?

## Hypothesis

A controller that explicitly uses perception confidence and uncertainty to decide when to proceed, hold, or abort will show a lower unsafe-touchdown rate than a baseline controller that always continues the landing, especially under severe perception degradation.

## Independent variables

1. Perception condition: clean, blur-like, low-light-like, occlusion-like, mixed.
2. Control architecture: baseline vs confidence-aware supervisor.
3. Supervisor thresholds in later ablation experiments.

## Dependent variables

- unsafe touchdown rate
- successful landing rate
- abort rate
- touchdown horizontal error
- touchdown horizontal and vertical speed
- number of interventions
- maximum and mean predicted risk

## Controlled variables

- vehicle dynamics model
- controller gains
- initial-state distribution
- trial budget
- landing safety envelope
- top-level random seed

## Phase 1 — surrogate perception study

The first phase deliberately abstracts image degradation into noisy, biased, stale, and uncertain state estimates. This is useful because it isolates the core research question: **what should the autonomy stack do when perception becomes unreliable?**

The corruption profiles are *not* claimed to be calibrated models of real cameras.

## Phase 2 — image-based perception

Replace the surrogate with a reproducible vision front end using synthetic landing-pad images. Corrupt the images with controlled transformations such as blur, reduced contrast, partial masking, and noise. Measure both pose-estimation error and confidence.

## Phase 3 — calibration + ablations

Study whether the confidence score is actually calibrated. Sweep the hold/abort thresholds and report the safety-vs-availability tradeoff. Compare at least:

- no supervisor
- confidence threshold only
- confidence + uncertainty
- confidence + uncertainty + temporal consistency

## Statistical plan

Use repeated Monte Carlo trials with fixed seeds. Report rates with 95% Wilson confidence intervals. Preserve raw episode-level CSV output so every figure can be regenerated.

## Success criterion

The project is successful if the safety supervisor produces a meaningful reduction in unsafe touchdowns under degraded perception and the result survives threshold sweeps and repeated seeds, while limitations are reported clearly.
