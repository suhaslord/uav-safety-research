# Research Log

This log records decisions that could affect interpretation of AegisLand results. It is intentionally separate from Git commit messages: code history shows *what changed*; this file explains *why the research design changed*.

## 2026-08-09 — Project foundation

### Decision
Start with a simulation-first study of confidence-aware supervisory control during autonomous landing rather than immediately building a vision model or physical UAV prototype.

### Reason
A simpler model makes it possible to isolate the safety-decision question and produce reproducible experiments before adding perception complexity.

### Current research question
Can an uncertainty-aware supervisor reduce unsafe simulated touchdowns under degraded perception without causing an impractically high abort/intervention rate?

### Current limitations
- planar point-mass dynamics
- synthetic perception stress rather than calibrated camera degradation
- hand-designed interpretable risk score
- no physical-aircraft validation
- current controller/supervisor parameters not derived from a specific aircraft

## 2026-08-09 — Phase 1 preregistration added

### Decision
Freeze a v1 primary experiment before promoting any result as a finding.

### Main run
- 500 episodes per profile/controller cell
- 5 perception profiles
- baseline + supervised architecture
- 5,000 episodes total
- top-level seed `2026`

### Primary endpoint
Pooled unsafe-touchdown rate across `blur`, `low_light`, `occlusion`, and `mixed` conditions.

### Reason
This prevents changing thresholds, seeds, profiles, or primary metrics after seeing which configuration produces the most favorable result.

See [`preregistration_v1.md`](preregistration_v1.md).

## Open methodological questions

1. Should baseline and supervised runs use **paired identical episode seeds** rather than independently generated episode seeds?
2. What is the best additional baseline: confidence-only thresholding, uncertainty-only thresholding, or a simple state-envelope rule?
3. Should the primary analysis emphasize absolute risk reduction rather than relative risk?
4. How should false/unnecessary interventions be defined rigorously?
5. Before Phase 2, what confidence-calibration metric should be primary?

## Rule for future entries

Every major experiment should add:

- date
- Git commit SHA
- hypothesis
- exact command/configuration
- what changed from the previous run
- whether the run is exploratory or preregistered
- result summary
- interpretation
- limitations discovered
- next decision

Negative and null results stay in the log.