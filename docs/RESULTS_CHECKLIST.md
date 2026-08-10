# Results Publication Checklist

Before any AegisLand result is described publicly as a project finding, verify all boxes below.

## Reproducibility

- [ ] Record the exact Git commit SHA used for the run.
- [ ] Record the exact command used.
- [ ] Preserve the top-level random seed.
- [ ] Preserve episode-level seeds in `episodes.csv`.
- [ ] Keep raw episode data unchanged after generation.
- [ ] Regenerate all tables and figures from the saved raw data.

## Preregistration

- [ ] Confirm whether the run is **preregistered** or **exploratory**.
- [ ] If preregistered, confirm the parameters match `preregistration_v1.md`.
- [ ] Document any amendment made before data collection.
- [ ] Do not silently replace the primary metric after viewing results.

## Results

- [ ] Report event counts, not only percentages.
- [ ] Report the baseline and supervised result together.
- [ ] Report unsafe-touchdown rate.
- [ ] Report successful-landing rate.
- [ ] Report abort rate.
- [ ] Report intervention burden.
- [ ] Include uncertainty intervals where supported.
- [ ] Include negative or null findings.

## Interpretation

- [ ] Say **simulated** when describing the result.
- [ ] Do not claim real-aircraft safety improvement.
- [ ] State that the perception profiles are surrogate stress models.
- [ ] Separate measured findings from explanations/speculation.
- [ ] List at least three important limitations.
- [ ] Identify at least one plausible alternative explanation.

## Figures

- [ ] Axes are labeled.
- [ ] Rates use a 0–1 or clearly marked percentage scale.
- [ ] Figure titles do not claim causality beyond the experiment.
- [ ] No condition is hidden because it weakens the story.
- [ ] Exploratory threshold sweeps are labeled exploratory.

## External review

- [ ] Ask at least one technically knowledgeable reviewer what they think the biggest methodological weakness is.
- [ ] Log meaningful feedback in `research_log.md`.
- [ ] If feedback changes the next experiment, version the new protocol rather than rewriting history.

A result is more credible when someone else can reproduce it, criticize it, and still understand exactly what was done.