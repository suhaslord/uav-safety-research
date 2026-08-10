# Phase 6D method and freeze criteria

## Scope

Phase 6D is a simulation-only development revision of the Phase 6 image-to-Aegis experiment. It does not alter or overwrite historical Phase 6, Phase 6B, or Phase 6C results.

The reserved unseen seeds remain unused during Phase 6D development:

- landing evaluation: `868686`
- selective-perception evaluation: `878787`

## Fixed architecture before the full development result

Phase 6D inherits:

- the Phase 6 synthetic renderer and temporal image tracker;
- the Phase 6 robust lateral velocity filter;
- the independent lower-rate reference estimator;
- the 0.80 lateral and 0.80 altitude component-confidence gates selected before Phase 6B landing development;
- the original controller and frozen V3 supervisor;
- paired episode seeds and isolated RNG streams.

Phase 6D changes only altitude fallback logic:

1. **Soft altitude uncertainty**: if `p_z_good < 0.80` but image and reference altitude remain statistically compatible, blend altitude position `z` toward the reference while preserving the established Phase 6 vertical-rate estimate `vz`.
2. **Hard altitude contradiction**: if the usable image and independent reference altitude differ by more than 3 combined standard deviations, classify the visual altitude track as a hard alias and blend both `z` and `vz` using the already-existing Phase 6B fallback weight.
3. Lateral x/vx fallback remains unchanged.

The hard-contradiction rule is fixed at 3 sigma with a 0.20 m minimum combined-altitude uncertainty floor. These values are declared before the full Phase 6D development matrix and are not selected from Phase 6D landing outcomes.

## Development matrix

The full development run uses:

- episode seed family: `626262`;
- calibration seed: `616161`;
- 30 paired episodes per condition per architecture;
- conditions: clean, blur, low light, mixed, occlusion;
- architectures: image temporal, original Phase 6 Aegis, Phase 6B, Phase 6C, Phase 6D.

All architectures receive the same episode seeds within each condition.

## Freeze criteria declared before reading the full Phase 6D result

Phase 6D may proceed to held-out evaluation only if the paired development evidence satisfies all of the following:

1. **No new paired failure versus original Phase 6.** A development episode that is successful under original Phase 6 must not become an unsafe touchdown, timeout, or abort under Phase 6D.
2. **Clean and blur availability is preserved.** Phase 6D must not reduce success relative to original Phase 6 in clean or blur.
3. **Low-light and mixed availability is preserved.** Phase 6D must be no worse than original Phase 6 in success, unsafe-touchdown, timeout, and abort rates for low light and mixed.
4. **Occlusion safety is no worse than original Phase 6.** Phase 6D must not increase the occlusion unsafe-touchdown rate or reduce occlusion success relative to original Phase 6 on this paired development matrix.
5. **Alias activation is auditable.** Hard-altitude-alias frame counts and condition-level activation rates must be saved. Unexpected widespread activation in nominal clean/blur operation blocks freezing and requires diagnosis rather than threshold tuning from landing outcomes.
6. **No post-result retuning.** If any criterion fails, Phase 6D is preserved as a development result and any subsequent change becomes a new explicitly labeled revision. The 3-sigma rule and 0.80/0.80 component gates are not adjusted using the Phase 6D development outcome table.

## Held-out rule

If all development criteria pass, the exact Phase 6D architecture and constants are frozen before any reserved seed is run. A separate untriggered held-out workflow must then use `868686` for landing and `878787` for selective perception exactly once. The held-out outcome must be reported regardless of whether it improves or worsens the development result.
