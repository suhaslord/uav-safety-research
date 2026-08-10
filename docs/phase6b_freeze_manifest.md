# Phase 6B Freeze Manifest

## Final status

**Frozen and evaluated. No post-held-out retuning was performed.**

Phase 6B was locked before its preregistered held-out seeds were exposed. Any future algorithmic change is a new revision and cannot be described as the same Phase 6B held-out experiment.

Frozen executable commit:

`b4e9838555e935a5ec42690495315473629b58f6`

Frozen GitHub Actions run:

`31355377934`

Full result: [`phase6b_results.md`](phase6b_results.md)

## Frozen architecture

```text
synthetic image sequence
        ↓
structured pixel estimator
        ↓
temporal tracking + reacquisition
        ↓
robust image-derived lateral velocity
        ↓
component confidence
   ├─ p_x_good
   └─ p_z_good + scale observability
        ↓
component-wise abstention at 0.80 / 0.80
        ↓
component-selective redundant fusion
        ↓
frozen V3 safety supervisor
        ↓
landing controller + planar dynamics
```

Historical V3 and Phase 6 paths remain intact as comparison architectures.

## Frozen component confidence

Phase 6B uses separate confidence targets:

- `p_x_good = P(|x_hat - x| <= 0.30 m)`
- `p_z_good = P(|z_hat - z| <= 0.85 m)`

The offline component calibrator uses condition-balanced, altitude-stratified synthetic calibration examples spanning `0.25–8.0 m`. Runtime confidence features are image-derived; the confidence layer is not supplied the ground-truth degradation condition during a landing episode.

The altitude confidence additionally respects a simulation-specific scale-observability ceiling:

`delta_z_bin = 35/h - 35/(h+1)`

`p_z_good <= min(1, 0.85 / delta_z_bin)`

The rule does not change the measured altitude. It only prevents reported confidence from exceeding the resolution implied by the synthetic integer-pixel marker scale.

## Frozen operating point

- lateral confidence gate: `0.80`
- altitude confidence gate: `0.80`
- temporal calibration seed: `616161`
- component calibration seed: `616161`
- temporal calibration samples per condition: `180`
- component calibration samples per condition: `280`
- image severity: `1.0`
- paired episode seeds: yes
- environment/image/reference RNG streams: isolated as documented
- V3 safety supervisor: unchanged

The `0.80 / 0.80` gates were selected during development from the predeclared risk/coverage grid and were not retuned from held-out landing outcomes.

## Source freeze history

The last substantive Phase 6B confidence-algorithm change before the freeze process was the scale-observability revision at:

`841db55d27055093e727372be8cf6f60ce836396`

Subsequent pre-evaluation commits added tests, reporting, documentation, and frozen-run infrastructure. The exact executable snapshot used for the held-out run was `b4e9838555e935a5ec42690495315473629b58f6`.

The workflow recorded that SHA inside each frozen result artifact.

## Pre-freeze validation

The frozen workflow began with the full test suite. **53 tests passed** before the held-out jobs were allowed to execute.

Development evidence at the unchanged operating point showed the component confidence layer behaving selectively, especially for altitude under blur/low-light/mixed degradation. A high-altitude development audit also retained a known residual limitation for clean/occlusion scale estimates rather than tuning it away.

The final corrected development landing run used seed `626262` and remained development-only.

## Held-out evaluation

The seeds had been declared before the corrected development result was observed:

- landing: `868686`
- selective perception: `878787`

They were exposed once in frozen Actions run `31355377934`.

### Landing study

- 5 image conditions
- 3 paired architectures
- 100 episodes per condition/architecture
- **1,500 landing episodes total**

Phase 6B outcomes:

| Condition | Success | Unsafe | Abort | Timeout |
|---|---:|---:|---:|---:|
| clean | 100% | 0% | 0% | 0% |
| blur | 100% | 0% | 0% | 0% |
| low light | 97% | 0% | 0% | 3% |
| mixed | 99% | 1% | 0% | 0% |
| occlusion | 96% | 4% | 0% | 0% |

The low-light timeout cost and the remaining mixed/occlusion unsafe cases are preserved as part of the frozen result.

### Selective-perception audit

- 20 sequences × 100 frames × 5 conditions
- **10,000 frames total**
- primary component gates: `0.80 / 0.80`

The held-out audit showed strong altitude selectivity under blur, low light, and mixed degradation, while mixed lateral confidence retained weak bad-estimate rejection. That limitation is documented rather than retuned.

## Frozen artifact provenance

Landing:

- artifact ID: `9051147608`
- artifact SHA-256: `ca175ae7906e84fdf2dffe95d2e56ebc6fb5e2334ed94d8c7bbc479276d321bf`
- archive: [`../results/phase6b_frozen_landing/`](../results/phase6b_frozen_landing/)

Selective perception:

- artifact ID: `9050458293`
- artifact SHA-256: `679a75e0d139c8cdb462d61c3bd8cf936d8234a45e10aa690ba301ae414e852c`
- archive: [`../results/phase6b_frozen_selective/`](../results/phase6b_frozen_selective/)

Large raw CSVs are committed as gzip-compressed files after artifact download. Compression changed storage representation only, not the frozen rows.

## Post-evaluation rule

Seeds `868686` and `878787` are permanently seen. They cannot be reused as unseen evidence for a later revision.

Future Phase 6C/6D experimental work has been preserved separately on the `phase6-future-experiments` branch and is **not part of this frozen Phase 6B result**.

## Safety scope

This freeze covers a synthetic planar research simulation only. The reference source is a noisy/dropout-prone surrogate simulated secondary sensor. Nothing in this experiment validates physical UAV flight, real cameras, real-world landing control, or an operational autopilot.
