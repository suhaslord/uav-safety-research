# AegisLand FDI-H1 — reviewed held-out simulation result

**Evidence date:** 2026-10-11 UTC.  
**Status:** Completed **within-simulator** experiment; replication outside this one vehicle/plant and simulation setting **not demonstrated**.  
**GitHub Actions [successful run](https://github.com/suhaslord/uav-safety-research/actions/runs/38110119678)** · [raw CSV and JSON artifact](https://github.com/suhaslord/uav-safety-research/actions/runs/38110119678/artifacts/11691184435) (90-day Actions artifact retention)  
**Provenance:** workflow-generated checkout SHA `08ecd66ecffe6a16739d0618b521b41d580801d9` (pull-request synthetic merge commit); pinned Bitcraze `7e93752dbc803af2488c1db46bb79b3da55f5d8c`; Webots container digest `sha256:f0023e30daf38b172e4e6ad24ed345909bcd9551df34d63d824e121a7cebf099`; Python 3.12 and NumPy 2.2.6.

## Answer to the narrow research question

Can a deterministic, causal 2-axis gyroscope rule distinguish healthy flight from full loss of exactly one of four motors **within 0.70s of an imposed fault**, before simulated contact, on previously unseen command seeds in this same Crazyflie/Webots setup?

**Yes, on the eight held-out command seeds evaluated here.** Every alert in a faulty test trajectory occurred 0.272 seconds after the fixed 10.0-second fault onset, while simulated altitude was approximately 0.9863–0.9883 m. The healthy controls did not alert. The method is a simple pre-specified sign-and-magnitude rule, **not a trained neural detector**.

This is a **narrow positive feasibility result** and **not** evidence of general flight safety, fault recovery, generalization to real systems, or robustness to other fault timings, partial losses, sensor noise, or different vehicle models.

## Frozen comparison and results

- Predefined response rule: 3 successive samples with `|gyro_p| >= 2.0 rad/s` and `|gyro_q| >= 0.75 rad/s`. First valid alert; angle/quadrant signs map to motor labels 1–4. Healthy is no alert.
- Fault injected at 10.0 seconds in four cases; fifth case healthy. Censor scoring by 10.70s or when post-onset altitude <0.5m.
- 14 command seeds, five paired conditions each; **70 simulation trajectories**, each **750 sensor rows** and running beyond 22 seconds (the late data are not used for scoring). **40 protected held-out trajectories** from eight seeds `53, 59, 61, 67, 71, 73, 79, 83`.
- Known pilot-informing seeds `11, 23, 47` excluded from protected evaluation. Others were not used for threshold tuning. Training described in the old MLP pilot is *not* involved in this final fixed-rule test.

| Metric | Verified result |
|---|---:|
| Protected test balanced accuracy, healthy + four fault classes | **1.000 (100%)** |
| Correct whole-trajectory classifications | **40/40** |
| Correct motor isolation on faulty trajectories | **32/32** |
| Healthy controls without false alarm | **8/8** |
| Median correct-fault response delay after onset | **0.272 seconds** |
| Altitude when correctly alerted | **0.9863–0.9883 m** |
| All-always-healthy negative control | **0.200 balanced accuracy** |

Protected confusion matrix, **rows = truth** and **columns = prediction**:

| | Healthy | Motor 1 | Motor 2 | Motor 3 | Motor 4 |
|---|---:|---:|---:|---:|---:|
| Healthy | 8 | 0 | 0 | 0 | 0 |
| Motor 1 | 0 | 8 | 0 | 0 | 0 |
| Motor 2 | 0 | 0 | 8 | 0 | 0 |
| Motor 3 | 0 | 0 | 0 | 8 | 0 |
| Motor 4 | 0 | 0 | 0 | 0 | 8 |

**Uncertainty:** the seed-cluster bootstrap in the workflow reports `[1.0, 1.0]` because every one of the eight seed clusters achieved perfect classification. That **does not** mean future accuracy is known with certainty. A more conservative exact two-sided 95% binomial lower bound for **8 successful seed clusters out of 8**, assuming independent identically distributed generated-command seeds, is only **0.631**. Even that inference is restricted to the same simulation/command distribution and ignores dependence through the shared vehicle physics. Do **not** treat 40 trajectories or overlapping sensor samples as independent real-world experiments.

## Independent artifact audit

In addition to the green GitHub Actions and unit tests, a separate standard-library replay checked the downloaded workflow artifact:

1. Verified SHA-256 bytes for **all 70 raw CSV files** against the saved input manifest.
2. Verified exactly 14 seeds × 5 conditions, all trajectory timestamps increasing, 750 rows/trajectory, onset labels consistent with the simulation controls and no non-finite p/q/altitude values.
3. Recomputed the early rule from each raw gyroscope trace without trusting the saved predictions.
4. Confirmed **all 70 recomputed labels match** the archived CSV predictions and that all **40 protected cases** match ground truth.
5. Confirmed 32 non-healthy alerts all occurred at `t=10.272s` and above the evaluation altitude cutoff. No control alert.
6. Confirmed the pinned simulator revision and captured Webots image digest.

Run an independent audit against a downloaded artifact:

```bash
python scripts/audit_fdi_h1_artifact.py aegisland-fdi-h1-precontact-evidence.zip
```

The workflow also preserves the raw traces, exact Git checkout, `report/trajectory_decisions.csv`, `report/heldout_results.json`, image digest and Python environment. The code and protocol are [in PR #175](https://github.com/suhaslord/uav-safety-research/pull/175).

## Why the result is not a broader safety claim

1. **The first long-window MLP approach was rejected.** Its preceding 15-trace pilot showed 0.661 window accuracy and 0.491 balanced accuracy on only one held-out seed. Some post-failure Webots trajectories diverged into physically absurd rotations/altitudes. This justified changing the *research question* before examining the new protected seeds; the new rule itself was inspired by those pilot results. This selection must be disclosed.
2. **All simulated faults were complete, sudden motor shutdown at the same known t=10.0.** Detection after a strong physical change is much easier than detecting an incipient failure. The tested onset, motor response, and plant are deterministic and fixed.
3. **Only one dynamics implementation, one drone, no sensor noise or disturbance distribution.** Perfect classification here is unsurprising because failed motors produce consistently different p/q signs and high angular rates, while healthy controls have virtually zero gyroscope response.
4. **Command-seed variation is not vehicle/physics independence.** Eight seeds yield only eight scenario clusters. They do not validate performance on real sensor data or multiple aircraft, and some short-period commands may repeat.
5. **No recovery/control outcome was evaluated.** This is a fault-indicator experiment only, not a guarantee that a drone can respond or land safely.
6. **The 90-day raw GitHub artifact must be downloaded/preserved for future review** because it is not part of the repository history.

## Next genuinely new research step

Freeze a **separate** protocol with random fault onset times, partial actuator degradation, sensor noise, altered dynamics and at least one truly independent flight-dynamics environment; reserve new untouched seeds/trajectories. Compare the rule against simple residual and physics-based baselines. Do not tune on these FDI-H1 protected outcomes and then reuse them as a fresh test. State negative outcomes plainly.

**Bottom line:** A reproducible, verified **positive simulation feasibility finding** is complete, with important generalization and safety limitations. It is not a publishable real-world reliability or flight-safety result by itself.
