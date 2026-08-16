# Next Experiment: Preregistered Phase 1

This is the next experiment that should be run after CI and smoke tests pass.

## Command

```bash
python scripts/run_experiments.py --episodes 500 --seed 2026
```

Expected output directory:

```text
results/latest/
```

Expected total episode rows:

```text
5 profiles × 2 architectures × 500 episodes = 5,000 episodes
```

## Before running

- confirm the Git commit SHA
- confirm `pytest -q` passes
- confirm the parameters in `src/uav_safety/config.py` match `preregistration_v1.md`
- confirm failure-state and recovery-envelope definitions are frozen before the run
- do not tune supervisor thresholds after looking at preliminary main-run results

## After running

1. Preserve `episodes.csv` unchanged.
2. Verify the row count is 5,000.
3. Save the Git commit SHA and command in `research_log.md`.
4. Report the preregistered primary endpoint before exploring threshold sweeps.
5. Report the predeclared secondary metrics across the full uncertainty sweep.
6. Use `RESULTS_CHECKLIST.md` before describing a result publicly.

## Primary analysis

Pool the degraded profiles:

- `blur`
- `low_light`
- `occlusion`
- `mixed`

Compare baseline vs supervised on **unsafe-touchdown rate**.

Do not select only the profile with the strongest improvement as the headline result.

## Secondary analysis

Report, without post-hoc threshold retuning:

- **failure probability:** fraction of episodes ending in an unsafe touchdown or another frozen terminal failure state.
- **recovery time:** elapsed simulated time from the first degraded/unsafe condition until return to the frozen nominal envelope.
- **non-recovery rate:** fraction of episodes that never return to the nominal envelope before termination.

If recovery time is undefined because an episode never recovers, keep it as a non-recovery case rather than substituting an arbitrary finite value.

## Important

If the supervisor performs worse, keep the result. The next research question becomes *why* it failed and which assumption was wrong.
