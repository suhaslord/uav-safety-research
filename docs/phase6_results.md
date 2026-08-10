# Phase 6 Frozen Results — Temporal Image Perception Connected to Aegis

## Status

Phase 6 is frozen and evaluated.

The algorithm was frozen before confirmatory evaluation at:

`9cddd41b76302ecc04492ef89fa56de0ea70bc21`

The held-out landing evaluation used:

- evaluation seed: `747474`
- calibration seed: `616161`
- 100 paired episodes per image condition / architecture cell
- 5 image conditions
- 2 architectures
- **1,000 simulated landing episodes total**

The frozen result validator passed all row-count, seed-pairing, metadata, outcome-consistency, and configuration-snapshot checks.

These are synthetic-image, planar-simulation results, not physical-UAV safety claims.

---

## Main held-out result

| Condition | Architecture | Success | Unsafe touchdown | Safe abort | Timeout |
|---|---|---:|---:|---:|---:|
| clean | image temporal | 100% | 0% | 0% | 0% |
| clean | image + Aegis | **100%** | **0%** | 0% | 0% |
| blur | image temporal | 100% | 0% | 0% | 0% |
| blur | image + Aegis | **100%** | **0%** | 0% | 0% |
| low light | image temporal | 100% | 0% | 0% | 0% |
| low light | image + Aegis | **100%** | **0%** | 0% | 0% |
| occlusion | image temporal | 89% | 11% | 0% | 0% |
| occlusion | image + Aegis | **96%** | **4%** | 0% | 0% |
| mixed | image temporal | 63% | 37% | 0% | 0% |
| mixed | image + Aegis | **92%** | **7%** | **1%** | 0% |

### 95% Wilson intervals

For `mixed` image+Aegis:

- success: **85.00%–95.89%**
- unsafe touchdown: **3.43%–13.75%**
- safe abort: **0.18%–5.45%**

For `occlusion` image+Aegis:

- success: **90.16%–98.43%**
- unsafe touchdown: **1.57%–9.84%**

The result is strong but not perfect, which is useful: Phase 6 does not claim that synthetic image uncertainty has been eliminated.

---

## Paired episode effects

The two architectures used the same episode seeds inside each image condition.

### Mixed

Relative to image-only temporal perception:

- Aegis improved success by **29 percentage points**
- Aegis reduced unsafe touchdowns by **30 percentage points**
- **33** image-only unsafe touchdowns became Aegis successes
- **3** image-only successes became Aegis unsafe touchdowns
- **1** image-only success became an Aegis safe abort

This is a net paired improvement, while also showing that redundant intervention is not regression-free.

### Occlusion

- Aegis improved success by **7 percentage points**
- Aegis reduced unsafe touchdowns by **7 percentage points**
- **11** image-only unsafe touchdowns became Aegis successes
- **4** image-only successes became Aegis unsafe touchdowns

Again, the aggregate benefit is real in this held-out simulation, but some individual episodes regress.

---

## Failure decomposition

Unsafe touchdown criteria are not mutually exclusive.

### Mixed

`image_temporal` had 37 unsafe touchdowns:

- 8 violated lateral-position tolerance
- 32 violated horizontal touchdown-speed tolerance
- 2 violated vertical touchdown-speed tolerance

`image_aegis_v3` had 7 unsafe touchdowns:

- 3 violated lateral-position tolerance
- 4 violated horizontal touchdown-speed tolerance
- 0 violated vertical touchdown-speed tolerance

The most important remaining mixed failure mode is therefore still lateral dynamics near touchdown rather than vertical descent speed.

### Occlusion

`image_temporal` had 11 unsafe touchdowns:

- 4 lateral-position failures
- 5 horizontal-speed failures
- 4 vertical-speed failures

`image_aegis_v3` had 4 unsafe touchdowns:

- 0 lateral-position failures
- 1 horizontal-speed failure
- 3 vertical-speed failures

---

## Confidence calibration

A separate audit used a seed derived from the held-out evaluation seed and did not change the frozen algorithm.

Calibration reliability by occupied confidence bin:

| Calibrated-confidence bin | Samples | Mean confidence | Observed good rate | Absolute gap |
|---|---:|---:|---:|---:|
| 0.6–0.8 | 416 | 0.757 | 0.683 | 0.075 |
| 0.8–1.0 | 184 | 0.869 | 0.880 | 0.011 |

Overall expected calibration error (ECE): **0.0551**.

The confidence signal is useful but still somewhat overconfident in the lower occupied bin.

---

# Held-out selective-perception benchmark

The abstention mechanism was also evaluated separately using a predeclared unused sequence seed:

- sequence seed: `757575`
- calibration seed: `616161`
- 20 sequences per condition
- 100 frames per sequence
- **10,000 synthetic image frames total**

This test deliberately asks a different question from landing success: does the image front end itself reject frame-level estimates outside the calibration error tolerances?

| Condition | Raw bad-frame rate | Abstention rate | Bad-frame abstention recall | Good-frame false abstention |
|---|---:|---:|---:|---:|
| blur | 44.2% | 0.0% | 0.0% | 0.0% |
| clean | 48.5% | 0.0% | 0.0% | 0.0% |
| low light | 5.45% | 0.0% | 0.0% | 0.0% |
| occlusion | 0.35% | 1.45% | 14.29% | 1.40% |
| mixed | 70.35% | 1.20% | 1.56% | 0.34% |

## Important negative result

**Standalone abstention is not selective enough.**

Under held-out `mixed` sequences, 70.35% of raw frame estimates fell outside the calibration target, yet only 1.20% of frames were abstained and only about 1.56% of those bad raw frames were explicitly rejected.

This is not hidden by the strong landing result.

It means the Phase 6 system-level improvement should **not** be described as “the confidence/abstention system detects almost every bad frame.” It does not.

Instead, the held-out evidence supports a narrower mechanism:

> Temporal state estimation, robust lateral-velocity estimation, independent redundant evidence, near-ground cross-estimator integrity checking, and frozen V3 safety logic can together mitigate many failures caused by degraded synthetic image perception even when the frame-level abstention classifier remains weak.

The unexpectedly high raw bad-frame rate in some easy conditions also shows that the frame-level calibration target (especially its altitude-error threshold) is not perfectly aligned with system-level landing performance. Improving that alignment is a separate research problem.

---

## Development-to-freeze progression

Phase 6 preserved its development failures instead of replacing them silently.

### Development iteration 1

After initial calibrated temporal image integration:

- mixed image+Aegis success: **36.7%**
- occlusion image+Aegis success: **80.0%**

Failure decomposition showed that most mixed failures violated horizontal touchdown-speed tolerance even though accepted lateral-position error was much smaller.

### Development iteration 2

Adding robust lateral velocity estimation raised:

- mixed image+Aegis success to **73.3%**
- occlusion image+Aegis success to **86.7%**

The remaining mixed failures were still dominated by horizontal speed.

### Development iteration 3

An exact failed episode showed a smoothly wrong image track near touchdown: true lateral velocity and image-derived lateral velocity had opposite signs while the image sequence remained internally consistent.

That motivated the near-ground cross-estimator integrity gate. The final development sample reached:

- mixed image+Aegis: **30/30 successes**
- occlusion image+Aegis: **29/30 successes**

Those values were development results only. The algorithm was then frozen and tested on new seed `747474`, producing the confirmatory values reported above.

---

## What Phase 6 establishes

Within this simulator, the project has now moved from directly corrupted state variables to a complete pixel-sequence perception loop:

```text
synthetic image sequence
        ↓
pixel measurement
        ↓
confidence calibration
        ↓
temporal tracking / abstention / reacquisition
        ↓
robust image-derived lateral velocity
        ↓
redundant cross-estimator integrity checking
        ↓
frozen V3 safety supervisor
        ↓
simulated landing controller
```

On the held-out landing experiment, the redundant image+Aegis architecture substantially outperformed the same temporal image-perception system without Aegis under `mixed` and `occlusion` degradation.

The result does **not** establish real-camera robustness, physical-flight safety, or strong frame-level selective prediction.

---

## Next research questions

The next version should be treated as a new phase rather than a retuned Phase 6 result. Strong candidates are:

1. **Selective perception / abstention redesign**
   - train or calibrate abstention against downstream risk rather than a fixed frame-level geometric error target;
   - compare risk-coverage curves, not only a single abstention threshold.

2. **Correlated failure stress**
   - bias both image perception and the reference estimator;
   - introduce common-mode errors where redundancy is less informative.

3. **Time-varying visual bias**
   - move beyond persistent fixed offsets to drifting or switching bias.

4. **More realistic synthetic imagery**
   - shadows, clutter, partial marker visibility, contrast inversion, structured occluders, perspective/rotation changes, and camera motion.

5. **Higher-fidelity simulation**
   - retain the same research questions while moving beyond planar dynamics.

Any such change should receive a new development seed, new freeze, and new held-out evaluation.
