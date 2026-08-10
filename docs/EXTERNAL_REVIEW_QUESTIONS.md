# External Review Questions

Use these questions selectively when a professor or researcher replies. Ask **one question at a time**, chosen to match their expertise.

## Controls / autonomy

- Is `PROCEED / HOLD / ABORT` a defensible supervisory abstraction for the research question, or should the safety layer act through a different mechanism?
- Is the baseline unfair because the supervised controller can delay descent while the baseline cannot?
- Would paired identical initial conditions/seeds materially strengthen the comparison?
- Which state variable or failure mode would you add first to make the simplified dynamics more informative without making the project unmanageably complex?

## Perception / computer vision

- Which synthetic degradation is most important to add before claiming the stress model covers meaningful perception failure modes?
- What would be a defensible confidence signal for a simple image-based landing-pad estimator?
- Would calibration error or selective-risk curves be a better way to evaluate whether confidence is trustworthy?

## Fluid dynamics / aerospace

- Which simplified environmental disturbance is most defensible for an initial simulation study?
- Which assumptions in the planar model most limit aerospace interpretation?
- If moving to a higher-fidelity simulator later, which modeling upgrade should come first?

## AI safety / uncertainty

- Is the current hand-designed risk score useful as an interpretable baseline, or does it entangle the evaluation too strongly with the stress model?
- Which ablation would best test whether uncertainty itself adds value beyond ordinary state thresholds?
- What is the clearest way to measure the cost of over-conservative intervention?

## Experimental design / statistics

- Should the main architecture comparison be paired at the episode level using identical random seeds?
- Is absolute risk reduction the most interpretable primary effect size here?
- Is 500 episodes per cell a reasonable first preregistered trial budget for estimating event-rate differences?
- What sensitivity analysis would most improve confidence in the result?

## Rule

Do not ask a professor ten questions at once. Choose the **single question most directly connected to their research** and show that you have already done the work needed to make the question concrete.