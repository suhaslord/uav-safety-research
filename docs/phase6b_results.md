# Phase 6B — Frozen Held-Out Results

## Summary

Phase 6B is the component-selective confidence revision that followed the frozen Phase 6 image experiment. It separates lateral-position confidence from altitude confidence, adds a simulation-specific pixel-scale observability cap for altitude, and allows the redundant reference estimate to carry only the component that the image system rejects.

The Phase 6B algorithm and fixed `0.80 / 0.80` component gates were locked before the held-out evaluation. The frozen executable snapshot was:

`b4e9838555e935a5ec42690495315473629b58f6`

The final workflow passed **53 automated tests** before exposing the held-out seeds.

## Frozen evaluation design

Landing evaluation:

- held-out landing seed: `868686`
- calibration seed: `616161`
- 100 paired episodes per condition and architecture
- 5 image conditions
- 3 architectures
- **1,500 simulated landing episodes total**

Architectures:

1. `image_temporal` — temporal image perception without Aegis redundant fusion;
2. `image_aegis_v3` — established Phase 6 image/Aegis integration;
3. `image_aegis_phase6b` — component-selective Phase 6B integration.

Selective-perception evaluation:

- held-out selective seed: `878787`
- 20 sequences × 100 frames per condition
- 5 image conditions
- **10,000 synthetic image frames total**
- frozen operating point: lateral confidence `>= 0.80`, altitude confidence `>= 0.80`.

No Phase 6B threshold or algorithm parameter was changed after these held-out runs.

## Held-out landing results

| Condition | Image-only success | Image-only unsafe | Phase 6 success | Phase 6 unsafe | **Phase 6B success** | **Phase 6B unsafe** | **Phase 6B timeout** |
|---|---:|---:|---:|---:|---:|---:|---:|
| clean | 100% | 0% | 100% | 0% | **100%** | **0%** | 0% |
| blur | 100% | 0% | 100% | 0% | **100%** | **0%** | 0% |
| low light | 100% | 0% | 100% | 0% | **97%** | **0%** | **3%** |
| occlusion | 86% | 14% | 93% | 7% | **96%** | **4%** | 0% |
| **mixed** | **57%** | **43%** | **94%** | **6%** | **99%** | **1%** | **0%** |

All Phase 6B abort rates were 0% in this held-out run.

### Main held-out confidence intervals

Using 95% Wilson intervals:

- Phase 6B mixed success: **94.55%–99.82%**
- Phase 6B mixed unsafe touchdown: **0.18%–5.45%**
- Phase 6B occlusion success: **90.16%–98.43%**
- Phase 6B occlusion unsafe touchdown: **1.57%–9.84%**
- Phase 6B low-light success: **91.55%–98.97%**
- Phase 6B low-light timeout: **1.03%–8.45%**

The intervals are deliberately reported because 100 episodes per cell is still a finite sample and point estimates should not be treated as exact probabilities.

## Paired effects

Because all architectures used identical episode seeds within a condition, the comparison can be made episode-by-episode.

### Mixed degradation

Relative to image-only temporal perception, Phase 6B:

- increased success by **42 percentage points**;
- reduced unsafe touchdowns by **42 percentage points**;
- converted **43** image-only unsafe touchdowns into Phase 6B successes;
- converted **1** image-only success into a Phase 6B unsafe touchdown.

Relative to the established Phase 6 Aegis path on the same held-out seed, Phase 6B:

- increased success by **5 percentage points**;
- reduced unsafe touchdowns by **5 percentage points**;
- converted **6** Phase 6 unsafe touchdowns into Phase 6B successes;
- converted **1** Phase 6 success into a Phase 6B unsafe touchdown.

### Occlusion

Relative to image-only temporal perception, Phase 6B:

- increased success by **10 percentage points**;
- reduced unsafe touchdowns by **10 percentage points**;
- converted **13** image-only unsafe touchdowns into successes;
- converted **3** image-only successes into unsafe touchdowns.

Relative to the established Phase 6 Aegis path:

- increased success by **3 percentage points**;
- reduced unsafe touchdowns by **3 percentage points**;
- converted **6** Phase 6 unsafe touchdowns into successes;
- converted **3** Phase 6 successes into unsafe touchdowns.

### Low light

Phase 6B introduced an availability cost under low light:

- success changed from 100% to **97%**;
- unsafe touchdowns remained **0%**;
- **3 episodes timed out** rather than touching down within the 45 s horizon.

Those three timeouts had frequent altitude-component reference takeover and no Aegis HOLD/ABORT interventions. This is consistent with a completion/availability cost from conservative component substitution rather than a safety abort, but the study does not claim a unique causal explanation from these three episodes alone.

## Failure decomposition

The remaining Phase 6B unsafe touchdowns were narrow:

- mixed: **1 unsafe touchdown**, caused by a vertical touchdown-speed violation; lateral position and horizontal speed were within limits;
- occlusion: **4 unsafe touchdowns**, all caused by vertical touchdown-speed violations;
- clean, blur, and low light: **0 unsafe touchdowns**.

This differs from earlier image-only mixed failures, which were dominated by horizontal touchdown-speed errors.

## Component-selective behavior

The component confidence layer was actively used rather than acting as a decorative score.

Mean Phase 6B component abstention rates during landing were approximately:

| Condition | Lateral abstention | Altitude abstention | Lateral reference takeover | Altitude reference takeover |
|---|---:|---:|---:|---:|
| clean | 14.6% | 7.1% | 14.4% | 7.5% |
| blur | 5.4% | 57.3% | 5.3% | 57.7% |
| low light | 7.6% | 48.9% | 7.1% | 49.3% |
| occlusion | 22.4% | 7.7% | 22.3% | 8.1% |
| mixed | 11.5% | 71.8% | 11.2% | 72.0% |

This is the intended Phase 6B behavior: a frame does not have to be classified globally as “good” or “bad.” The image system may retain a reliable lateral estimate while rejecting an unreliable altitude estimate, or vice versa.

## Held-out selective-perception audit

The separate 10,000-frame held-out audit confirms that altitude confidence became meaningfully selective.

At the frozen `0.80` altitude-confidence gate:

| Condition | Altitude coverage | Selected bad-altitude rate | Bad-altitude rejection recall |
|---|---:|---:|---:|
| clean | 100% | 0% | 0%* |
| blur | 20.95% | 0% | **100%** |
| low light | 30.55% | **0.16%** | **99.35%** |
| mixed | 0.85% | 0% | **100%** |
| occlusion | 100% | 0% | 0%* |

`*` There were no bad altitude estimates in the held-out clean/occlusion sets to reject, so rejection recall is not an informative statistic for those cells.

The component audit also exposes an important remaining limitation. Under mixed degradation, lateral estimates were usually accurate (`95.7%` within the lateral target), but the lateral gate still accepted some bad estimates:

- lateral coverage: **96.6%**;
- selected bad-lateral rate: **3.99%**;
- bad-lateral rejection recall: only **10.47%**.

So Phase 6B should not be described as a perfect bad-frame detector. Its strongest held-out selective behavior is currently in altitude/scale reliability.

## Interpretation

The held-out result supports three narrower conclusions inside this simulator:

1. **Component-wise confidence can be more useful than one global image-confidence score.** Blur and mixed degradation often preserve usable lateral information while making scale/altitude unreliable.
2. **A pixel-scale observability limit prevents the confidence model from claiming altitude precision that the rendered geometry cannot support.**
3. **Selective redundant substitution improved the hardest system-level landing conditions in the held-out comparison**, especially mixed degradation, while introducing a measurable low-light completion cost.

The result does not show that Phase 6B is uniformly superior. It trades some availability under low light for improved mixed/occlusion safety and success, and paired regressions still occur.

## Important limitations

- The camera images are synthetic rather than real camera data.
- Vehicle dynamics are planar, not full 6-DOF flight dynamics.
- The independent reference estimate is a **surrogate simulated secondary sensor** generated from simulator state with independent noise, dropout, lower update rate, stale propagation, and uncertainty growth. It is not a fully modeled inertial/navigation estimator.
- The altitude observability cap is derived from this synthetic renderer's pixel geometry and is not a real-camera uncertainty equation.
- Common-mode or correlated sensor failures are not yet modeled.
- Mixed lateral confidence still has weak bad-estimate rejection recall.
- No physical aircraft or hardware is validated by this work.

## Provenance and archived evidence

Frozen GitHub Actions run: `31355377934`

Landing artifact:

- artifact ID: `9051147608`
- artifact SHA-256: `ca175ae7906e84fdf2dffe95d2e56ebc6fb5e2334ed94d8c7bbc479276d321bf`
- committed archive: [`results/phase6b_frozen_landing/`](../results/phase6b_frozen_landing/)

Selective-perception artifact:

- artifact ID: `9050458293`
- artifact SHA-256: `679a75e0d139c8cdb462d61c3bd8cf936d8234a45e10aa690ba301ae414e852c`
- committed archive: [`results/phase6b_frozen_selective/`](../results/phase6b_frozen_selective/)

The large raw `episodes.csv` and `frames.csv` files are stored as `.csv.gz` in the repository. Compression was performed after downloading the frozen artifacts; the rows were not modified.

## Safety scope

AegisLand remains a simulation-only research project. These results are evidence about a synthetic experimental architecture, not validation for a real UAV, camera, autopilot, or flight-safety system.
