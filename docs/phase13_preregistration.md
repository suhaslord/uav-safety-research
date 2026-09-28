# Phase 13 preregistration — Thirteen-Domain Gauntlet

## Status

**PREREGISTERED BEFORE ANY PHASE 13 DEVELOPMENT, TRANSFER, PROTECTED, OR FINAL EVIDENCE IS EXPOSED.**

Phase 13 is a new external-validity lineage. It is not a continuation of Phase 12 tuning.

Phase 12 is permanently closed. Its protected and final evidence may not be reused for Phase 13 construction, calibration, model selection, threshold selection, or tuning.

## Why Phase 13 exists

Phase 12 answered a narrow but important question:

> Can a frozen innovation-aware uncertainty model pass preregistered simulation gates across development, transfer, protected validation, and final unseen replication under the Phase 12 data-generating family?

The answer was yes.

Phase 13 asks the harder next question:

> Does that exact frozen model remain honest when the data-generating process changes in structured ways that were not used to fit or calibrate it?

This is an external-validity test, not an optimization phase.

The number **13** is used as a scientific constraint rather than decoration: the phase contains exactly **13 preregistered out-of-distribution stress domains**. All 13 are frozen before the first Phase 13 development result is generated.

## Frozen predecessor identity

Phase 13 inherits the exact Phase 12 Iteration 3 candidate without modification.

- frozen Phase 12 scientific Git SHA: `8d0617a83d699cd14eae6194ce3a86a5c034dfbc`
- frozen Phase 12 candidate SHA-256: `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`
- method: `continuity_lateral_innovation_residual_normalized_robust_conformal`

The following remain frozen:

- point estimator
- bounded continuity logic
- independent coarse rescue
- velocity caps
- innovation scales
- output groups
- severity scaling
- lateral reliability scaling
- all normalized conformal radii
- calibration A/B maximum rule
- targets `{0.50, 0.68, 0.80, 0.90, 0.95}`
- H1-H11 definitions and thresholds
- availability and rescue decisions
- claim boundary

Phase 13 performs **no fitting, recalibration, multiplier selection, threshold relaxation, or post-hoc widening** before the zero-shot result.

## Primary hypothesis

The Phase 12 uncertainty architecture should retain useful calibration under structured domain shift when its inference-visible reliability signals continue to respond to the mechanisms that drive estimator error.

The primary hypothesis is:

> The exact frozen Phase 12 Iteration 3 candidate will preserve the preregistered Phase 12 primary gates under the combined 13-domain shifted development distribution, while maintaining at least 88% 95%-interval coverage on both axes in every individual domain and preserving a positive continuity innovation/error relationship.

This is deliberately difficult.

A Phase 13 failure is scientifically acceptable. A failed zero-shot result identifies an external-validity boundary and is not permission to silently adapt the Phase 12 candidate.

## Paired-control design

Each Phase 13 domain is evaluated using a paired design.

For every domain:

1. Generate the ordinary predecessor event using a fresh Phase 13 family partition and seed.
2. Preserve a paired control copy with no Phase 13 stress overlay.
3. Apply the preregistered Phase 13 stress transform to a second copy.
4. Evaluate both with the exact same frozen Phase 12 candidate.

This separates two failure modes:

- **control failure:** the predecessor pipeline itself did not reproduce on the fresh family partition;
- **shift failure:** the paired control is sound but the structured domain shift breaks calibration or other gates.

No Phase 13 result may be interpreted as external-validity failure unless paired-control integrity is also reported.

## The 13 locked domains

The machine-readable source of truth is `docs/phase13_domain_manifest.json`.

### Sensing shifts

1. **camera_scale_miscalibration**
   - base domain: `small_scale+oblique+temporal_dropout`
   - lateral error gain: `1.12`
   - altitude error gain: `1.08`
   - innovation gain: `1.08`
   - severity offset: `0.04`

2. **lateral_sensor_bias**
   - base domain: `edge+low_contrast+temporal_dropout`
   - lateral bias: `+0.06 m`
   - innovation gain: `1.12`
   - severity offset: `0.05`

3. **correlated_measurement_noise**
   - base domain: `blur_noise+low_contrast+temporal_dropout`
   - low-frequency lateral amplitude: `0.055 m`
   - low-frequency altitude amplitude: `0.11 m`
   - innovation gain: `1.18`
   - severity offset: `0.06`

4. **heavy_tail_measurement_noise**
   - base domain: `edge+blur_noise+temporal_dropout`
   - lateral sigma: `0.025 m`
   - altitude sigma: `0.05 m`
   - tail probability: `0.04`
   - tail multiplier: `4.0`
   - innovation gain: `1.22`
   - severity offset: `0.07`

### Timing shifts

5. **fixed_latency_2f**
   - base domain: `small_scale+temporal_dropout`
   - fixed estimate latency: `2 frames`
   - innovation gain: `1.18`
   - severity offset: `0.06`

6. **jittered_latency_0_4f**
   - base domain: `oblique+dim+temporal_dropout`
   - deterministic per-frame latency: `0–4 frames`
   - innovation gain: `1.24`
   - severity offset: `0.08`

7. **burst_staleness_5f**
   - base domain: `edge+small_scale+temporal_dropout`
   - frozen/stale estimate windows: `5 frames`
   - preregistered windows begin at frames `18` and `43`
   - innovation gain: `1.28`
   - severity offset: `0.09`

### Dynamics shifts

8. **lateral_wind_drift**
   - base domain: `edge+oblique+temporal_dropout`
   - sequence-scale lateral drift amplitude: `0.09 m`
   - innovation gain: `1.16`
   - severity offset: `0.06`

9. **vertical_gust**
   - base domain: `small_scale+dim+temporal_dropout`
   - vertical gust amplitude: `0.18 m`
   - innovation gain: `1.10`
   - severity offset: `0.06`

10. **dynamics_gain_mismatch**
    - base domain: `edge+small_scale+oblique+temporal_dropout`
    - lateral error gain: `1.30`
    - altitude error gain: `1.20`
    - innovation gain: `1.20`
    - severity offset: `0.08`

11. **oscillatory_drift**
    - base domain: `oblique+blur_noise+temporal_dropout`
    - lateral oscillation amplitude: `0.07 m`
    - altitude oscillation amplitude: `0.12 m`
    - innovation gain: `1.15`
    - severity offset: `0.06`

### Compound shifts

12. **reacquisition_shock**
    - base domain: `oblique+blur_noise+temporal_dropout`
    - post-dropout lateral shock: `0.10 m`
    - post-dropout altitude shock: `0.20 m`
    - decay schedule: `1.0, 0.5, 0.25`
    - innovation gain: `1.35`
    - severity offset: `0.10`

13. **latency_wind_calibration_compound**
    - base domain: `edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout`
    - fixed latency: `2 frames`
    - lateral bias: `0.04 m`
    - altitude bias: `0.08 m`
    - lateral drift amplitude: `0.07 m`
    - lateral noise sigma: `0.02 m`
    - altitude noise sigma: `0.04 m`
    - innovation gain: `1.35`
    - severity offset: `0.12`

## Stress-layer interpretation

The Phase 13 stress layer is a **simulation stress transform**, not physical flight evidence.

It preserves truth trajectories and predecessor availability decisions, then deterministically perturbs estimator outputs and inference-visible reliability cues according to the frozen domain profile.

This means Phase 13 tests:

- uncertainty calibration under a changed simulated error-generating process;
- robustness to structured staleness, bias, correlated noise, heavy tails, drift, gusts, and model mismatch;
- whether the innovation-aware continuity mechanism remains informative under those changes.

It does **not** claim that these transforms are a high-fidelity model of a particular sensor, aircraft, atmosphere, or real flight stack.

A later phase may replace these synthetic transforms with a genuinely independent simulator or recorded sensor dataset. Phase 13 does not pretend that step has already happened.

## Truth-leakage rule

Truth is permitted only to:

- generate the synthetic stress process;
- recompute evaluation error after the stress transform;
- calculate evaluation metrics.

Truth may not enter the frozen Phase 12 inference-time half-width calculation.

The stress transform may update inference-visible `severity` and `p9_anchor_innovation_lateral_abs` only through fixed preregistered response rules. It may not update them using the observed truth error.

## Evidence partitions

All Phase 13 evidence uses fresh seeds and disjoint family ranges.

### Development

- seed: `946946`
- families: `1201–1224`
- role: permanently seen development-only evidence

### Transfer

- seed: `957957`
- families: `1225–1248`
- remains unexposed until development passes

### Protected validation

- seed: `968968`
- families: `1249–1272`
- remains unexposed until transfer passes

### Final

- seed: `979979`
- families: `1273–1296`
- remains unexposed until protected validation passes

Phase 12 seeds `907907`, `913913`, `924924`, and `935935` are not Phase 13 evaluation evidence.

Phase 11 protected seed `858858` and retired seed `869869` remain forbidden.

## Group power

Each Phase 13 stage uses 24 fresh families split evenly across the existing intervention strata:

- bootstrap5: 6 families
- gap3: 6 families
- gap7: 6 families
- gap12: 6 families

Development, transfer, and protected validation retain the existing Phase 12 evaluation group minimums.

Final retains the existing Phase 12 final group minimums.

No group threshold will be relaxed after seeing a Phase 13 result.

## Frozen Phase 12 primary gates

Both the paired control and shifted aggregate are evaluated using the existing H1-H11 Phase 12/P14R gate implementation.

The Phase 13 shifted aggregate must pass the same required primary gates:

- H1 useful availability
- H2 overall lateral and altitude 95% coverage
- H3 calibration curve MACE
- H4 overall interval efficiency
- H5 primary-continuity honesty
- H6 base-output honesty
- H8 high-severity honesty
- H9 rescue-output honesty
- H10 rescue accuracy floor
- H11 rescue effectiveness
- group minimums

H7 remains diagnostic exactly as in the predecessor.

## Phase 13-specific gates

### G13.1 — Paired-control integrity

The fresh paired control must pass all predecessor primary gates.

This must pass before a shifted failure is treated as a domain-shift finding.

### G13.2 — Zero-shot shifted primary gates

The combined 13-domain shifted distribution must pass all predecessor primary gates with the exact frozen Phase 12 candidate.

### G13.3 — Thirteen-domain honesty

Every one of the 13 individual domains must achieve:

- lateral 95% coverage `>= 0.88`
- altitude 95% coverage `>= 0.88`

Required passing domains: **13 / 13**.

This gate is intentionally all-or-nothing. Phase 13 should reveal a weak domain instead of averaging it away.

### G13.4 — No catastrophic domain

Across all individual domains:

- worst lateral 95% coverage `>= 0.80`
- worst altitude 95% coverage `>= 0.80`

This gate is reported separately from G13.3 so a moderate honesty miss can be distinguished from a severe external-validity collapse.

### G13.5 — Reliability mechanism survives shift

On available primary-continuity rows, Spearman correlation between:

`log1p(p9_anchor_innovation_lateral_abs / frozen_lateral_innovation_scale)`

and lateral absolute error must be:

`>= 0.20`

This tests whether the mechanism that motivated Phase 12 remains directionally informative under the new domains.

### G13.6 — Zero adaptation

Before the zero-shot result:

- candidate changed: `false`
- recalibration performed: `false`
- post-hoc threshold change: `false`

Any violation fails Phase 13 by construction.

## Development decision rule

Phase 13 development passes only if:

- G13.1 passes;
- G13.2 passes;
- G13.3 passes;
- G13.4 passes;
- G13.5 passes;
- G13.6 passes.

If development fails:

1. preserve the result permanently;
2. identify the failing domain(s) and mechanism(s);
3. do not expose Phase 13 transfer;
4. do not modify the Phase 12 candidate within this zero-shot lineage;
5. any adaptive follow-up must be a separately preregistered Phase 13B architecture with a new scientific identity.

If development passes:

1. freeze the exact Phase 13 scientific Git SHA;
2. freeze the exact script/domain-manifest identity;
3. authorize a single transfer exposure on seed `957957`;
4. make no scientific changes before transfer.

## Sequential evidence rule

Transfer may be exposed once only after development passes.

Protected validation may be exposed once only after transfer passes.

Final may be exposed once only after protected validation passes.

A failed downstream stage closes the current Phase 13 lineage at that stage.

No stage can be rerun for a better random outcome.

Infrastructure failure before evidence generation may be retried only if logs show that the protected seed was not generated/exposed and the change is non-scientific.

## No leaderboard rule

Phase 13 development is not a tuning leaderboard.

The following are forbidden after development exposure:

- changing any of the 13 stress magnitudes because a gate was close;
- dropping the worst domain;
- changing the 88% per-domain floor;
- changing the 80% catastrophic floor;
- changing the 0.20 Spearman floor;
- widening Phase 12 intervals;
- recalibrating conformal radii;
- changing the Phase 12 innovation model;
- selecting among multiple unregistered stress formulations.

## Required artifacts

Every Phase 13 evaluation stage must emit:

- paired-control frames
- shifted frames
- machine-readable result JSON
- per-domain metrics
- Phase 13 gate verdicts
- SHA-256 manifest
- exact predecessor candidate digest
- exact scientific Git SHA
- claim-boundary flags

Development should also retain the execution log.

## Interpretation ladder

Possible outcomes are intentionally distinguishable:

1. **control failure** — fresh-family reproduction problem; external-shift attribution is invalid.
2. **control pass + shifted aggregate fail** — broad external-validity failure.
3. **aggregate pass + one-domain fail** — average behavior hides a local weakness.
4. **all 13 domains pass but mechanism gate fails** — empirical transfer without preserved explanatory mechanism.
5. **all Phase 13 gates pass** — strong synthetic external-validity evidence for the frozen Phase 12 uncertainty model.

Only outcome 5 permits transfer.

## Claim boundary

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`

A Phase 13 pass would support only this claim:

> The exact frozen Phase 12 Iteration 3 uncertainty model passed the preregistered Phase 13 zero-shot synthetic external-validity gauntlet across 13 structured domain shifts.

It would **not** establish:

- physical UAV safety;
- flight validation;
- certification relevance;
- production readiness;
- controller improvement;
- real-sensor equivalence;
- operational reliability;
- autonomous landing safety.

## Future direction if Phase 13 succeeds

If all sequential Phase 13 stages eventually pass, the next scientifically stronger step should not be more synthetic tuning.

The preferred next step is an independent evidence source: a different simulator, recorded camera/sensor data, or another externally generated dataset, while preserving the same evidence-role discipline.

Phase 13 is designed to earn that next step rather than skip it.
