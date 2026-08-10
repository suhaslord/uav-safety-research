# Phase 1 Milestone Roadmap

## Milestone A — Verify the research harness

- [ ] CI passes on Python 3.11.
- [ ] Unit tests cover dynamics, supervisor decisions, and episode outcomes.
- [ ] A demo run completes and produces a trace.
- [ ] A small Monte Carlo smoke test completes.
- [ ] Output files regenerate without manual editing.

## Milestone B — Freeze the primary experiment

- [x] Research question written.
- [x] Primary endpoint defined.
- [x] Fixed supervisor thresholds recorded.
- [x] Trial budget recorded.
- [x] Exclusion and stopping rules written.
- [x] Null-result policy written.
- [ ] Confirm whether paired episode seeds should be used before the main run.

## Milestone C — Run preregistered v1

- [ ] Record commit SHA.
- [ ] Run 500 episodes per profile/controller cell.
- [ ] Save all 5,000 episode rows.
- [ ] Generate summary tables and plots.
- [ ] Calculate pooled degraded-condition primary endpoint.
- [ ] Write an interpretation without changing the experiment.

## Milestone D — Stress the conclusion

- [ ] Repeat with additional top-level seeds.
- [ ] Run supervisor threshold sweep.
- [ ] Add confidence-only ablation.
- [ ] Add uncertainty-only ablation.
- [ ] Analyze failure cases.
- [ ] Create calibration/reliability analysis.

## Milestone E — External review

- [ ] Ask a controls/autonomy researcher to critique the baseline.
- [ ] Ask a perception researcher to critique the stress model.
- [ ] Ask a statistics/research-methods reviewer to critique the analysis.
- [ ] Log criticism and decisions.

## Milestone F — Phase 2

Only after the Phase 1 result is understood:

- [ ] Build a synthetic landing-pad image generator.
- [ ] Define reproducible visual corruptions.
- [ ] Estimate position from images.
- [ ] Evaluate confidence calibration.
- [ ] Connect image-based uncertainty to Aegis supervisor.

The project should move forward by **evidence**, not by feature count.