# AegisLand / Nakahira Uncertainty-Safety Benchmark — Frozen Preregistration

**Status:** frozen before held-out evaluation  
**Scope:** simulation only  
**Base AegisLand commit:** `51ecc8cb12892714e2ba81c6028b62aea93dd7a7`  
**Safety acceptance:** `false`  
**Controller tuning allowed:** `false`

## Research question

As perception and navigation evidence become less reliable, how do AegisLand's frozen controller/supervisor behave in terms of **failure probability** and **recovery time**, and how often does degradation produce **non-recovery** rather than a finite recovery?

This study follows the methodological feedback that failure probability and recovery time are meaningful safety outcomes. It re-applies the intent of PR #15 on the current Phase-10 research lineage instead of merging the stale PR.

## Evidence boundary

The benchmark reuses the existing Phase-6B/Phase-7 simulation stack:
- frozen controller defaults,
- frozen V3 supervisor thresholds,
- Phase-7 stronger plant,
- historical synthetic calibration seed `616161`,
- existing image renderer, component confidence, reference stack, and fusion.

It does **not** retune controller thresholds, supervisor thresholds, confidence gates, or calibrators for this benchmark.

Development and held-out evidence are separated:
- development seeds: `81001`–`81004`;
- held-out seeds: `92001`–`92016`;
- the same seed set is paired across conditions within an evidence role.

The held-out seed list and all condition levels are recorded in `configs/nakahira_uncertainty_frozen_v1.json` before the held-out workflow runs.

## Frozen uncertainty axes

The first frozen sweep deliberately contains **no multi-axis combinations**. That avoids turning a first result into a large, difficult-to-interpret factorial and prevents post-result selection of whichever combination looks interesting.

1. **Nominal**
   - clean image condition,
   - historical image severity `1.0`,
   - historical sensor update rates.

2. **Pose/perception noise**
   - clean renderer so only its existing sensor-like noise scale changes,
   - image severity `1.50`, `2.25`, `3.00`.

3. **Partial observability**
   - existing occlusion renderer,
   - severity `1.00`, `1.40`, `1.80`.
   - This is an image-availability stress model, not a calibrated physical occlusion model.

4. **Sensor latency**
   - existing Phase-7 scheduled-delivery reference stack,
   - latency-burst extra delays `4`, `8`, `14` simulation steps,
   - fault window begins at 10% of the nominal episode horizon and lasts 20% (4.5–13.5 s under the frozen 45 s horizon), so it occurs during the descent rather than after a typical landing has already ended.

5. **Stale reference**
   - transport latency remains at the historical base value,
   - reference acquisition becomes progressively sparser:
     - level 1: GNSS/baro/range every `8/4/2` steps;
     - level 2: `12/6/3`;
     - level 3: `20/10/5`.
   - The existing reference estimator carries delivered age forward, increases uncertainty with age, and eventually marks data unavailable at its historical age limit.

## Primary outcome definitions

### Failure probability

For a condition/severity cell:

`failure probability = terminal failures / total held-out episodes`

A terminal failure is frozen as:
- `unsafe_touchdown`, or
- `timeout`.

A `safe_abort` is **not** silently reclassified as an unsafe failure. Abort rate is reported separately as a supporting behavior measure.

Wilson 95% intervals are reported with every failure probability.

### Recovery time

At every simulator step, the benchmark records the frozen V3 supervisor decision/risk and the true simulated velocities.

A degraded/unsafe operating envelope is entered when **any** of:
- supervisor decision is not `PROCEED`;
- filtered V3 risk is at least `0.68` (the historical HOLD threshold);
- `|vx| > 1.20 m/s`;
- `|vz| > 1.25 m/s`.

The recovery envelope requires **all** of:
- supervisor decision is `PROCEED`;
- filtered V3 risk is at most `0.52` (the historical release threshold);
- `|vx| <= 0.80 m/s`;
- `|vz| <= 0.80 m/s`;

and it must remain true continuously for **1.0 simulated second**.

Recovery time is simulated elapsed time from first degraded-envelope entry (after the applicable degradation onset) to the first sustained recovery entry.

### Non-recovery

Non-recovery is mandatory and separate:
- if degradation is entered and the sustained recovery envelope is never reached, `non_recovery = true`;
- `recovery_time_s = null`.

No arbitrary large finite recovery time may be substituted.

## Supporting outcomes

Predeclared supporting outcomes:
- HOLD rate;
- component-abstention rate;
- safety-envelope violation rate;
- unsafe-touchdown rate;
- timeout rate;
- safe-abort rate;
- degradation latency;
- terminal lateral-position error;
- terminal descent-rate error;
- control confidence and position uncertainty at terminal failure;
- control confidence and uncertainty at recovery.

Supporting outcomes do not replace the primary result because they look more favorable.

## Safety-envelope violation

A step is counted as a supporting safety-envelope violation if any of:
- V3 risk >= `0.90` (historical abort-risk threshold);
- `|vx| > 2.0 m/s`;
- `|vz| > 2.0 m/s`.

This is a simulation research envelope, not a real-aircraft certification limit.

## Analysis

For each condition/severity cell:
- report sample count;
- failure probability + Wilson 95% CI;
- non-recovery probability + Wilson 95% CI;
- finite recovery-time median, Q25, and Q75;
- supporting behavior means/rates.

Raw episode rows and compressed step traces are preserved. The final artifact also contains plots, the exact frozen config, executable Git SHA, and a SHA-256 result manifest.

## Integrity rules

- `simulation_only = true`
- `safety_acceptance = false`
- simulator outcomes are not physical-UAV safety validation
- preserve negative results
- preserve safe aborts, timeouts, and non-recoveries as their actual outcomes
- no held-out threshold/model/definition tuning
- no post-hoc substitution of a supporting metric for the primary result
- no final-sweep combination conditions beyond the frozen config
