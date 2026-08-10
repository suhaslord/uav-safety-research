# Phase 6E perception confirmation protocol

## Purpose

Phase 6E produced a strong first validation and was also the stronger reference architecture in the failed Phase 6F three-seed replication. This protocol performs a dedicated **Phase 6E-only perception confirmation on new development seeds** before Phase 6E is connected to the landing loop.

This is still simulation-only development evidence, not final held-out evaluation.

## Frozen Phase 6E perception rule

Phase 6E is frozen for this confirmation exactly as implemented in `src/uav_safety/phase6e_perception.py`:

- historical Phase 6 marker renderer;
- p30, median, standard deviation, and p90 image statistics;
- if `median > 0.5 * p90`, use p30 as the background statistic;
- otherwise use the historical median;
- preserve the historical threshold equation, largest-connected-component estimator, x/z geometry inversion, raw-confidence formula, and sharpness statistic;
- fit the existing component-confidence model on Phase 6E measurements across altitude bands `0.08–0.50`, `0.50–2`, `2–4`, `4–6`, and `6–8 m`;
- component selection threshold remains `0.80`;
- altitude observability cap remains unchanged.

No Phase 6E code or constant may be changed after this protocol is committed and before the confirmation finishes.

## Confirmation seeds

The following static-image development seeds were searched in the repository before this protocol was committed and returned no matches:

- `737431`
- `747432`
- `757432`

They become permanently seen development seeds when the confirmation runs.

The final replacement held-out seeds remain untouched:

- landing: `918271`
- selective perception: `928271`

## Frame matrix

For each confirmation seed:

- conditions: clean, blur, low light, occlusion, mixed;
- altitudes (m): `0.08, 0.12, 0.18, 0.25, 0.40, 0.60, 0.80, 1.20, 2, 3, 4, 5, 6, 7, 8`;
- 40 frames per condition/altitude cell;
- x offset uniformly sampled from `[-1.5, 1.5]`;
- calibration seed `616161`;
- no landing controller, supervisor, or reference-fusion logic.

Total: 9,000 unique rendered confirmation frames.

## Fixed definitions

- x-good: `|x_hat - x| <= 0.30 m`;
- z-good: `|z_hat - z| <= 0.85 m`;
- selected component: calibrated component probability `>= 0.80`;
- near-ground: true altitude `<= 0.25 m`;
- high-altitude audit: true altitude `>= 6.0 m`;
- catastrophic altitude error: `|z_hat - z| > 2.0 m`.

## Acceptance criteria

Phase 6E may proceed to landing-development integration only if all criteria pass on the pooled confirmation set.

1. **Selected-risk semantics:** in every condition and for each component x/z, the 95% Wilson upper confidence bound on bad-frame rate among selected frames must be <=0.20.
2. **Nontrivial availability:** selected-frame coverage must be >=0.50 for x and >=0.50 for z in every condition. This prevents passing by abstaining almost everywhere.
3. **Near-ground recovery:** raw z-good rate must be >=0.95 in every condition for true altitude <=0.25 m.
4. **No accepted catastrophic altitude error:** zero z-selected frames may have absolute altitude error >2.0 m.
5. **High-altitude degraded-scale honesty:** for blur and mixed frames at true altitude >=6.0 m whose altitude estimate is bad, at least 95% must be rejected by the 0.80 z gate.
6. **Seed-family consistency:** within each individual confirmation seed and condition, the 95% Wilson upper selected bad-frame rate for x and z must also remain <=0.20.
7. **No final-seed leakage:** `918271` and `928271` must not appear in confirmation inputs or result metadata.
8. **No post-confirmation retuning:** a failed criterion rejects Phase 6E for landing integration as currently defined. Any estimator/calibrator change becomes a new revision and requires new development evidence.

These criteria are committed before any of the three Phase 6E confirmation seeds are executed.
