# Phase 10R live-archive status

The public research cockpit should present Phase 10R as a **mixed trajectory-held-out validation result**:

- difficult miss rate: `25.70% → 8.72%` (`66.0%` relative reduction)
- lateral MAE / p95 improvement: `30.1% / 15.2%` — below preregistered gates
- altitude MAE / p95 improvement: `53.0% / 44.9%` — passed
- 95% empirical coverage: `94.1%` lateral / `94.1%` altitude
- mean absolute coverage error: `0.84 pp`
- no post-validation retuning
- new protected Phase 10R frozen holdout not exposed
- `safety_acceptance = false`

`phase10r-frontier.js` surfaces this status on the cockpit home page. `phase-hero-fix.js` repairs the responsive Phase 7 and Phase 10 hero containers without changing the phase evidence data.
