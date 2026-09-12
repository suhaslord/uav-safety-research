# Browser experiments

Open any phase and choose **Run an experiment**, or use the Experiment link on the research home. Each run exposes its scope before execution and labels its output as exploratory.

## What runs

- Phases 1, 2, 3 and 5: original Python V1/V2/V3 landing simulators, paired with the baseline under custom initial state, perception noise, bias, dropout and seed. Phase 5 uses V3 for an exploratory robustness batch.
- Phases 6 and 6B: original image renderer and geometric/observability components on new synthetic frames. These are component tests, not full closed-loop evaluations.
- Phase 7: original nonlinear, lagged plant compared with the original point-mass dynamics.
- Phase 8: original KS and quantile-distance functions on generated error traces.
- Phase 9: synthetic camera-error sensitivity metrics. ArUco/PnP, camera capture, and actual Gazebo validation are not available in the browser.
- Phases 10 and 10R: original AegisT10 estimator on generated measurement sequences; 10R adds an adjustable synthetic shift.
- Phases 11–13C: calibration/coverage exercises, with original source-aware calibration, finite-sample quantile and staleness components as applicable. The normalized-score exercise does not load the frozen learned Phase 12 scale models. 13B shows paired coverage change; 13C isolates the coverage loss from staleness.
- Phases 14–19: synthetic scalar residual and recoverability exercises using the original staleness/quantile helpers and published residual equation. They do not execute protected/final evaluations or load frozen coefficient candidates.
- Phases 20–22: original Shapley, Walsh and additive prediction functions on a user-defined 32-cell surface. A fixed model derived from that construction is compared with fresh noisy observations. Neither the coefficients nor the response surface are the published frozen artifacts.
- Phase 4: no test, matching its recorded provenance gap.

The browser runner never modifies the research archive, frozen candidates, verdicts or scientific gates. Running a small interactive experiment is not a reproduction of a full research phase or evidence of flight safety.

## Runtime and reproducibility

Python and NumPy run in a dedicated Web Worker using pinned Pyodide 0.29.2. The first run downloads that runtime from jsDelivr; later runs reuse the worker. Inputs and results stay on the device. Cancel terminates the worker, and a three-minute deadline handles stalled loads or runs.

Numeric bounds are enforced in both HTML controls and Python. The maximum batch is 10 paired landing episodes, 128 rendered camera frames, or 1,024 scalar samples. JSON exports include inputs, seed, scope, metrics and rows; CSV exports contain the result rows. Results are marked stale when inputs change.

`deploy/vercel/lab/python-bundle.json` contains the Python modules served to the browser. `scripts/build_browser_lab.py` packages the local core modules and copies selected pure functions verbatim from scientific source commit `668d065f4312e33e2d21ca7a7ee76d4d6d5617b3`. Function hashes and source paths are included. This actual source commit is distinct from the scientific-head string already recorded in the historical presentation; this feature does not rewrite that record.

To rebuild, ensure that commit is available locally, then run:

```sh
git fetch origin phase22/frozen-additive-context-transfer
python scripts/build_browser_lab.py
python -m pytest tests/test_browser_experiments.py -q
node --check deploy/vercel/lab/lab.js
node --check deploy/vercel/lab/worker.js
```

Commit the generated bundle with adapter changes. The existing Vercel release workflow includes everything under `deploy/vercel/` and the shared dashboard taxonomy; no server credentials are shipped to the browser.


## Guided controls and comparisons

The interface adds plain-language questions for all phases, a site-wide introduction and glossary, sliders with numeric input, and three starting scenarios. Presets are synthetic examples, not validated flight conditions. Sample count and seed are under repeatability settings. The browser keeps one completed run in memory for a same-phase metric comparison; percentages are compared in percentage points. This is a paired settings comparison, not a statistical significance test. Reloading the tab clears the kept run.

Series can be hidden independently, and a chart-position slider reports exact values and context names. Context positions are discrete combinations, not time. Phase 20/21 structural measures operate on the constructed surface; observation noise affects the fresh observations only. No camera measurements produces an unavailable RMSE, never a zero-error claim.
