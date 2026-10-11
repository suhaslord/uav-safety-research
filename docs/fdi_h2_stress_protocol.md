# FDI-H2 — preregistered out-of-distribution motor-fault challenge

**Protocol freeze: 2026-10-11, before generating or inspecting any H2 results.**  
**Evidence status:** no H2 measurements at protocol freeze.  
**Relationship:** a separate follow-up to [FDI-H1](fdi_h1_heldout_result.md). This experiment does **not** revise the H1 result, its frozen rule, or its previously inspected command seeds.

## Question

Does H1's **unchanged** early gyroscope threshold-and-quadrant rule still isolate a faulty motor when loss is partial, failure occurs at a different time in flight, or the logged gyroscope readings are noisy?

A negative result is the default hypothesis to challenge H1's apparently perfect success on the narrow full-loss simulator task. This remains one within-simulator engineering sensitivity study, not a field validation or flight-safety evaluation.

## Source and frozen detector

- Plant/world: Bitcraze `crazyflie-simulation` commit `7e93752dbc803af2488c1db46bb79b3da55f5d8c` under Webots `R2025a`. Preserve the Docker digest and Git commit in run artifacts.
- H1's rule is **not retuned**: first three consecutive 32-ms samples satisfying `|gyro_p| >= 2.0 rad/s` and `|gyro_q| >= 0.75 rad/s`; signs (p,q) map (++,+−,−−,−+) to motor (1,2,3,4).
- Use gyroscope signals only. The scripted failure label and true onset are for *evaluation*, not features available to the detector.
- Score a single first alert from the start of each trajectory until **0.70 seconds after the scenario's fault onset** (or before post-onset altitude drops below 0.50 m). Do not change those limits after seeing outcomes.
- An alert **before actual failure onset is a premature false alert**, not successful fault isolation, even when its motor sign happens to match the future failure. Healthy controls count any alert as a false positive.
- For healthy controls, use the matching hypothetical onset as the endpoint reference. The detector does not know onset.

## Independent H2 scenarios

- **Fresh command seeds, not in the H1 pilot or H1 holdout:** `97, 101, 103, 107, 109, 113` (six independent command-seed clusters).
- **Fault onsets:** `8.0` and `12.0` seconds.
- **Loss severity:** `1.0` (complete single-motor loss) or `0.5` (50% reduction in *applied* motor command). The stock controller still requests its usual motor command. No changes to the quadrotor plant parameters.
- **Observed gyro noise:** clean (`σ=0.0 rad/s`) or deterministic additive independent Gaussian noise (`σ=0.5 rad/s`) applied to logged gyro p/q values during *offline detection*, not to flight dynamics or the PID's control signal. Noise RNG seed derived from the immutable scenario identifiers; evaluate both observation conditions on the **same** physical simulator trajectory.
- **Healthy negative control:** one no-fault trajectory per seed × onset; reused transparently across both severity comparisons, never counted as a distinct simulator replication.
- **Expected 108 raw simulated trajectories:** six seeds × two onsets × [one healthy + four motor classes × two severities].
- Each is simulated only to `onset + 1.5 s`; the experiment explicitly excludes the late physically unrealistic blow-up seen in the earlier pilot.
- **Expected 240 grouped classification outcomes:** six seeds × two onsets × two severities × two gyro-noise conditions × five label classes. These are **not 240 independent flight experiments**.

## Outcomes fixed before results

**Primary outcome:** five-class trajectory-level balanced accuracy for **50% motor-power loss, noisy gyro (σ=0.5 rad/s)**, pooling both fault-onset times with equal weights. Report the 5×6 confusion matrix (healthy/motors 1–4 as predicted classes plus premature alert) and number of missed/misidentified faults.

**Secondary:** full eight-cell factorial table (onset × severity × noise) with balanced accuracy, healthy false-positive fraction, correct motor-isolation fraction, premature-alert fraction and median latency among correctly isolated faults.

Each factor cell has one healthy control and four fault cases for each seed (six seeds). Across onsets the same seed is repeated, so uncertainty must resample **the entire seed cluster**, not individual samples, trajectories, or seed-onset pairs. Use a fixed 2,000-resample, seed-cluster percentile bootstrap with seed `20261013`; describe any degenerate interval honestly. Always-healthy five-class balanced accuracy is `0.2`. No p-value or significance claim from overlapping recordings.

**No stopping, tuning, or cherry-picking rule:** If the primary condition performs poorly, keep that negative result as the main finding. No rethresholding, alternative onset cutoff, sensor filtering, cherry-picked seeds, or altered severity based on observed H2 outcomes.

## Verification and limitations

- Require exactly 108 distinct CSVs, strictly increasing time, sufficient ending time, fixed seed/failure labels, correct fault activation, finite p/q/height values through scoring; fail closed if data missing. Archive CSV files, evaluator output, source and environment SHA-256 manifests.
- The **same pinned plant, controller, telemetry path and command distribution** remain. New random seeds do not establish cross-domain independence. Gaussian noise is an artificial observation-side perturbation; actuator partial loss is simulated, not a hardware test.
- Only two fault timings, two loss fractions and two noise levels. Six command seeds are a small cluster sample. No independent drone, real sensors, different physics model, automatic recovery, flight safety or real-world reliability claim.

## Reproduction

Workflow `.github/workflows/fdi-h2-stress.yml` runs a 108-trajectory Webots dataset and scores `experiments/ornik_fdi_webots/evaluate_fdi_h2.py`. Results and raw evidence will be attached to the Actions run. Do not merge a result claim until the raw artifact has been inspected and checksums verified.
