# Phase 6D method and freeze criteria

> **Integrity correction:** the original planned held-out seeds `868686` and `878787` were subsequently found to have already been executed by the historical Phase 6B frozen workflow. They are permanently seen and are not valid held-out seeds for Phase 6D or later revisions. This document is corrected by `docs/research_integrity_recovery.md`.

## Scope

Phase 6D is a simulation-only development revision of the Phase 6 image-to-Aegis experiment. It does not alter or overwrite historical Phase 6, Phase 6B, or Phase 6C results.

Replacement held-out seed families reserved after the integrity audit are:

- landing evaluation: `918271`
- selective-perception evaluation: `928271`

They must remain unused during development.

Historical seen seeds that must not be reused as held-out are:

- Phase 6B landing: `868686`
- Phase 6B selective perception: `878787`

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

The hard-contradiction rule is fixed at 3 sigma with a 0.20 m minimum combined-altitude uncertainty floor. These values were declared before the full Phase 6D development matrix and were not selected from Phase 6D landing outcomes.

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

## Phase 6D development decision

Phase 6D is **not frozen**. Although its development landing outcomes were strong, the hard-altitude-alias detector activated widely in nominal clean and blur episodes, triggering the preregistered audit criterion. The next revision must be based on an altitude-specific estimator-consistency benchmark rather than changing the 3-sigma number to improve landing outcomes.

## Replacement held-out rule

Only after a later final architecture passes its development and detector-audit criteria may held-out evaluation occur. That architecture must be frozen in writing before execution, and the replacement seeds must be used exactly once:

- landing: `918271`
- selective perception: `928271`

Both outcomes must be reported regardless of whether they improve or worsen the development result.
