# Phase 6 Evaluation Protocol

## Status

Phase 6 is currently in **development**, not frozen evaluation.

The image-perception architecture has been changed in response to development smoke results. Therefore the current development seed family must not be treated as held-out evidence.

## Data roles

### Offline calibration development

- seed: `616161`
- purpose: fit the empirical raw-confidence → probability-of-good-estimate mapping
- synthetic ground truth is permitted only during this offline calibration step
- this seed must not be reused as a Phase 6 held-out landing-evaluation seed

### Landing-system development

- seed: `626262`
- purpose: architecture debugging, smoke tests, abstention/reacquisition development, and Phase 6 fusion-adapter development
- results from this seed may guide code changes
- because it has guided code changes, it is **not** confirmatory evidence

## Development changes already motivated by observed failures

The development process has already identified and corrected several interface failures:

1. uniform blank frames could pass a zero threshold and masquerade as one giant component;
2. the historical Phase 5 marker-size clipping made altitude partly unobservable near touchdown;
3. a one-frame innovation rejection could lock the tracker onto a stale state and cause a long abstention cascade;
4. direct historical V3 reference blending could add noisy control error even when the calibrated image track was already good.

These failures motivated, respectively:

- low-information frame rejection,
- a separate Phase 6 perspective renderer,
- multi-frame track reacquisition and short-window velocity estimation,
- a Phase-6-only confidence-aware redundant-fusion adapter around frozen V3 logic.

## Current development comparison

The Phase 6 runner compares paired episode seeds for:

- `image_temporal`
- `image_aegis_v3`

across:

- clean
- blur
- low light
- occlusion
- mixed

It records image abstention, calibration, position-estimation, intervention, and landing-outcome metrics. Unsafe touchdowns are also decomposed by lateral-position, horizontal-speed, and vertical-speed criteria.

## Freeze rule

Before a confirmatory Phase 6 result is generated:

1. finish the development study on seed `626262`;
2. resolve only clearly identified development failures;
3. ensure tests and CI pass;
4. record the exact Phase 6 algorithm commit and all relevant default configs;
5. choose a new held-out evaluation seed that has not been used for tuning;
6. run the frozen evaluation once;
7. validate row counts, paired seeds, metadata, and outcome consistency;
8. do not change Phase 6 parameters based on the held-out result and rerun it as though it were still held out.

If the frozen result exposes a new weakness, that weakness is reported and any later improvement becomes a new version/evaluation rather than silently replacing the frozen result.

## Claims boundary

All Phase 6 results remain synthetic-image, planar-simulation results. Neither development nor held-out results constitute evidence of safety on a physical UAV.
