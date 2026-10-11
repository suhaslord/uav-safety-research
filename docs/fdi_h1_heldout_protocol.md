# AegisLand FDI-H1: held-out motor-fault generalization

**Protocol frozen in code before outcomes. Status: NOT RUN / NO RESULTS CLAIMED.**

## One question

Can the small, AegisLand-owned Webots motor-fault classifier distinguish a healthy Crazyflie from complete loss of one of four motors **on command trajectories excluded from fitting**?

This is an independent-command-seed *within-simulator* generalization check. It is **not** independent vehicle, domain, real-camera, actual flight, or fault-tolerant landing validation; it is **not** a reproduction of Garg et al. / Ornik et al.

## Plant and immutable choices

- Simulation: pinned Bitcraze crazyflie-simulation source commit `7e93752dbc803af2488c1db46bb79b3da55f5d8c`, Webots Docker image tag `cyberbotics/webots:R2025a-ubuntu22.04`. The workflow records the pulled image digest and git provenance.
- Controller: unmodified AegisLand Webots logger in `webots_fdi_controller.py`; the requested motor command is logged, while the failed actuator receives zero from t = 10 s onward.
- Conditions: healthy or complete failure of exactly one of motors 1, 2, 3, 4. Every command seed is run under all five conditions.
- Command protocol: frozen `seeded_commands()` in the logger; same distribution and times for all splits.
- Window inputs: 100 timesteps of position, angular rate, and requested motor-speed signals (unchanged original pilot feature layout).
- Model: existing NumPy one-hidden-layer MLP, 24 hidden units, 80 epochs, batch size 64, Adam lr 0.001, training RNG seed 20261011. Reuse original code; **no refitting after inspecting test outcomes**.
- Entire trajectories are split by command seed: training = 11,23,29,31; development = 41,43; **protected test = 47,53,59,61,67,71,73,79**. No window from a test seed may enter fitting or normalization. The development set is descriptive only: there is no hyperparameter search or threshold optimization.
- Evaluation: consider predictions from windows ending **14–22 s** (after a full 100-sample post-fault history); majority-vote exactly **one prediction per trajectory**. Ties choose smallest class index (healthy = 0).
- Full model vs command-only **ablation** using the same model class and training procedure; vs an always-healthy negative control.
- **Primary metric:** five-class balanced accuracy across the **40 protected test trajectories** (eight command-seed clusters, each repeated under all five motor conditions). Secondary: macro F1, per-class recall, healthy false-positive rate = 1 - healthy recall, and confusion matrix.
- Sampling unit for uncertainty: **command seed**, not overlapping 100-sample windows. Use fixed 2,000-draw seed-cluster bootstrap with seed 20261012 and 2.5th/97.5th percentiles. Intervals are descriptive and likely wide with eight independent commands.
- Save all raw traces, five-class predictions, model provenance hashes, complete input SHA-256 manifest, environment details, exact Git commit and run ID as downloadable CI artifacts.

## Acceptance criteria

An experiment is *executed* only if the hosted Webots workflow generates all **70 trajectories** (14 seeds × five conditions) and every input trace passes the independent evaluator's completeness, monotonic timestamp and onset-label checks. Missing files or incomplete traces **fail closed**; no partial or invented metrics.

There is **no predetermined success threshold**. Publish the actual held-out result even if it is near chance, worse than command-only, or worse than always-healthy. Do not report window-level p-values as independent evidence.

The comparison has significant remaining limitations: one simulation environment and hardware model, only complete motor shutdown at a fixed time, correlated paired trials across classes, no unseen controller or faults outside the generator, and no physical safety inference. The command-only model helps detect a shortcut but cannot rule out all simulator-specific cues.

## Execution and evidence

The PR-triggered GitHub Actions workflow `FDI held-out seed validation` runs Webots on GitHub-hosted Linux, with no real UAV or hardware required. It records and uploads results; generated raw data are not committed to `main`.

The exact analysis command after capturing trajectories is:

```bash
python experiments/ornik_fdi_webots/validate_trajectory_generalization.py \
  --input-dir experiments/ornik_fdi_webots/heldout_run/raw \
  --output-dir experiments/ornik_fdi_webots/heldout_run/report
```

Read `heldout_metrics.json` and `trajectory_predictions.csv` only **after** all integrity checks succeed. The report includes clear negative and failure cases; no website or model update should be based on these data without a separate development/retest cycle.

Do not conflate this FDI-H1 study with the Phase 25/26 landing-pad detector evidence or claim it advances the independent Phase 26 validation gate.
