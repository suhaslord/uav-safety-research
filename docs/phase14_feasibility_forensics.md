# Phase 14 feasibility forensics — why the uncertainty gate is empty

## Scope

This analysis uses only already-seen Phase 14 identification and development artifacts. It does not expose any new Phase 14 evidence role and does not authorize retuning inside the closed Phase 14 lineage.

## Frozen caps

From the fit candidate:

- lateral Phase 12 half-width cap: `0.0613350659 m`
- altitude Phase 12 half-width cap: `0.1811164977 m`

These caps were not selected manually. They follow the preregistered relation

`h_cap = 0.90 * ((1 - |a|) * r) / gamma`.

## Identification evidence already showed the cap would be empty

Among fit transitions beginning inside the fixed recoverable box:

- rows: `12,013`
- minimum lateral Phase 12 95% half-width: `0.1915865539 m`
- minimum altitude Phase 12 95% half-width: `0.4045110001 m`
- joint fraction below both frozen caps: `0.0`

The smallest fit half-widths were already:

- lateral: **`3.1236×`** the frozen lateral cap
- altitude: **`2.2334×`** the frozen altitude cap

The fit workflow intentionally did not use nonvacuous admission as a candidate-selection criterion; the preregistration made that a fresh development gate. Development therefore provided the first pass/fail statement on this issue.

## Fresh development half-width distribution

### Natural development cohort

Eligible transitions beginning inside the fixed box: `8,873`.

Lateral Phase 12 95% half-width:

- min: `0.1915865539 m`
- 1st percentile: `0.1915865539 m`
- 5th percentile: `0.1943646365 m`
- 10th percentile: `0.1971380188 m`
- median: `0.3122047279 m`
- 90th percentile: `0.7962174289 m`
- 95th percentile: `1.0396611838 m`
- max: `1.9445090663 m`
- frozen cap: `0.0613350659 m`
- fraction at or below cap: `0.0`

Altitude Phase 12 95% half-width:

- min / 1st / 5th / 10th percentile: `0.4045110001 m`
- median: `0.7498230710 m`
- 90th percentile: `1.8321885589 m`
- 95th percentile: `1.8727134835 m`
- max: `2.0626875490 m`
- frozen cap: `0.1811164977 m`
- fraction at or below cap: `0.0`

### Fixed-two-frame latency challenge

Eligible transitions beginning inside the fixed box: `1,375`.

Lateral half-width:

- min: `0.1915865539 m`
- 5th percentile: `0.1963657143 m`
- median: `0.2550656843 m`
- 95th percentile: `0.8536765817 m`
- max: `1.3707210871 m`
- fraction at or below frozen cap: `0.0`

Altitude half-width:

- min: `0.4045110001 m`
- 10th percentile: `0.6220468189 m`
- median: `0.6220468189 m`
- 95th percentile: `1.7884042590 m`
- max: `1.9435611991 m`
- fraction at or below frozen cap: `0.0`

## The 10% reserve is not the cause

Removing the 10% reserve would not make the bridge feasible.

For the fitted surrogate, the full contraction budgets are:

- lateral: `(1-|a|)r = 0.1169196684 m`
- altitude: `(1-|a|)r = 0.3206714718 m`

Using the **smallest** Phase 12 half-width observed even in identification evidence, the preregistered normalized-residual envelope would imply minimum disturbance bounds of:

- lateral: `gamma * h_min = 0.3286898354 m`
- altitude: `gamma * h_min = 0.6445775259 m`

Those are:

- lateral: **`2.8112×`** the entire available contraction budget
- altitude: **`2.0101×`** the entire available contraction budget

So even a hypothetical reserve fraction of `1.0` cannot make any observed fit transition admissible under this direct mapping.

## Scientific interpretation

The Phase 12 95% interval half-width is an uncertainty object for the current estimation error. Phase 14 attempted to reuse that same width as the scale for a **one-step dynamics residual**. The empty admissible set indicates that this direct identification is structurally too conservative for the locked recoverable box.

That distinction matters. A current-state uncertainty interval and a one-step process/disturbance residual are not automatically the same mathematical object.

The next rigorous research question should therefore not be “how do we relax the Phase 14 cap until something passes?” A better follow-up is to preregister a different bridge that keeps these roles separate — for example:

1. use Phase 12 uncertainty to decide whether the current state-confidence set lies inside a recoverable region, and
2. calibrate a separate one-step transition-residual envelope for propagation.

Any such follow-up must be a new lineage with fresh downstream evidence. It cannot reopen or retune Phase 14.

`simulation_only = true`
`safety_acceptance = false`
`controller_tuning_allowed = false`
