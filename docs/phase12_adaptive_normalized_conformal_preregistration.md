# Phase 12 preregistration — adaptive normalized robust conformal uncertainty

## Status

**PREREGISTERED BEFORE PHASE 12 TRANSFER / PROTECTED / FINAL EVIDENCE IS EXPOSED**

Authoritative predecessor: Phase 11 P14R, study closed after a mixed / negative protected result.

Phase 11 remains frozen evidence. This phase does **not** reopen P14R, does not retune against protected seed `858858`, and does not expose or reuse retired P15-v2 seed `869869`.

Development seed `907907` is permanently seen and may be rerun for debugging/model development exactly as declared before its first exposure. The development history is recorded in `docs/phase12_development_log.md`.

## Motivation

Phase 11 P14R preserved high useful availability and approximately nominal 95% uncertainty coverage under protected shift, but failed one locked H4 component:

- protected lateral p95 interval half-width / p95 error: `2.4354x`
- frozen maximum: `2.25x`

The failure was narrow: coverage, calibration, base / continuity honesty, high-severity honesty, rescue honesty, rescue accuracy, and rescue effectiveness all passed. The next question is therefore not whether to widen or loosen the old gate. It is whether uncertainty width can become more *locally proportional to inference-visible difficulty* while keeping the successful Phase 11 point estimator and rescue path unchanged.

## Research question

> Can a frozen, inference-visible difficulty scale plus robust normalized conformal calibration reduce lateral tail interval width under fresh distribution shift without sacrificing the availability and uncertainty-coverage gains established by P14R?

## Only allowed scientific change

The Phase 11 P14R point estimator, bounded continuity policy, independent rescue model, velocity caps, and innovation scales remain unchanged.

Phase 12 changes only the uncertainty model:

1. fit a simple monotone difficulty scale from fresh Phase 12 scale-fit data using the already inference-visible `severity` signal, separately by P14R output group and axis;
2. apply the development-frozen continuity contrast rule defined below;
3. normalize absolute errors by that frozen scale;
4. compute finite-sample conformal quantiles of the normalized scores independently in two disjoint fresh calibration environments;
5. take the pointwise maximum of the two calibration quantiles for robustness;
6. at inference, return `half_width = frozen_scale(severity, group, axis) * robust_normalized_quantile`.

No truth-derived quantity is available to the uncertainty model at inference.

## Frozen scale family

For each P14R output group and axis:

- severity anchors are the 10th and 90th percentiles of fresh scale-fit severity;
- the low-error anchor is the median absolute error in the lowest severity third;
- the high-error anchor is the median absolute error in the highest severity third;
- the high-error anchor is constrained to be no smaller than the low-error anchor;
- raw scale varies linearly between the two severity anchors and is clipped outside them;
- a positive floor prevents division by zero.

### Development amendment 1 — frozen before transfer exposure

Iteration 1 used the raw clipped-linear scale directly. On permanently-seen development seed `907907`, every required gate except lateral H4 tail efficiency passed; lateral p95 half-width / p95 error improved from the closed Phase 11 protected value `2.4354x` to `2.3620x`, but remained above the locked `2.25x` maximum. No transfer, protected, or final Phase 12 seed had been exposed.

Iteration 2 therefore changes only **within-continuity scale contrast**, while retaining all seeds, family IDs, domains, gates, point-estimator behavior, calibration environments, and the robust maximum rule.

For `continuity_h3`, `continuity_h45`, and `continuity_h67`, after computing raw clipped-linear scale `s` from low/high anchors `l,h`, define:

- `c = sqrt(l*h)`;
- `scale = c * (s/c)^0.5` when `h > l`;
- otherwise `scale = s`.

Base-output and independent-rescue scales keep exponent `1.0` and are unchanged from iteration 1.

This geometric-center shrinkage preserves positivity and monotonicity while reducing unstable high-tail contrast inside the smaller continuity cells. It is **not** a post-conformal multiplicative shrinkage of final intervals: the fresh calibration environments still determine all normalized conformal quantiles after this scale transformation.

The exponent `0.5` is now frozen for the candidate that may advance to transfer. Any further scientific change after a failed development rerun must be recorded before transfer; after transfer exposure, the scale formula cannot change.

This intentionally limits model capacity. No splines, neural scale model, post-transfer coefficient tuning, or protected-data feature engineering is allowed in this phase.

## Conformal rule

Coverage targets remain `{0.50, 0.68, 0.80, 0.90, 0.95}`.

For each fresh calibration environment, group, axis, and target `q`:

1. compute `score = absolute_error / frozen_scale`;
2. apply the existing finite-sample `ceil((n+1)q)` order-statistic conformal rule;
3. apply cumulative maxima across increasing `q` so intervals are nested;
4. set the final Phase 12 multiplier to the maximum of calibration A and calibration B.

The robust max is defined before transfer exposure and cannot be replaced by an average, minimum, or post-hoc blend after seeing results.

## Exposure ledger

Phase 11 permanently seen / retired evidence remains unchanged and is not eligible for Phase 12 tuning.

Phase 12 uses new seeds and new family IDs:

| Role | Seed | Family IDs | Exposure rule |
|---|---:|---|---|
| scale fit | `880880` | `957..988` | fit / permanently seen |
| calibration A | `891891` | `989..1020` | calibration / permanently seen |
| calibration B | `902902` | `1021..1052` | calibration / permanently seen |
| development smoke | `907907` | `1125..1148` | permanently seen; debugging only; never a gate |
| seen transfer | `913913` | `1053..1076` | expose only after candidate + code freeze |
| protected validation | `924924` | `1077..1100` | expose only if seen transfer passes all primary gates |
| final holdout | `935935` | `1101..1124` | expose only if protected validation passes all primary gates |

The development-smoke split can be rerun while implementation is changing, but it can never be promoted to transfer, protected, or final evidence.

## Family strata

Each role uses the same four intervention strata used by P14R:

- `bootstrap5`
- `gap3`
- `gap7`
- `gap12`

Scale-fit / calibration roles allocate 8 families per stratum. Transfer / protected / final / development-smoke roles allocate 6 families per stratum.

## Domain policy

Phase 12 keeps the same factor vocabulary used by the predecessor benchmark (`edge`, `small_scale`, `oblique`, `dim`, `blur_noise`, `low_contrast`, `temporal_dropout`) but uses newly frozen stage-specific compound-domain lists and fresh seeds / family identities.

Domain lists are code constants in the Phase 12 runners and are part of the scientific freeze.

## Power minimums

The scale-fit and calibration stages must meet the same group-level minimums used by P14R calibration:

- base: `>= 900`
- continuity horizon 3: `>= 180`
- continuity horizons 4–5: `>= 135`
- continuity horizons 6–7: `>= 90`
- independent rescue: `>= 180`

Transfer / protected evaluation minimums remain:

- base: `>= 360`
- h3: `>= 60`
- h4–5: `>= 45`
- h6–7: `>= 30`
- rescue: `>= 60`

Final minimums remain P14R's final minimums.

If any required minimum fails, the stage fails; cells are not merged after exposure.

## Primary gates

Phase 12 retains the Phase 11 P14R primary gate definitions so the targeted change is judged against the same scientific boundary:

- H1 useful availability `>= 0.92`
- H2 each-axis 95% coverage in `[0.90, 0.98]`
- H3 mean absolute coverage error across all targets / axes `<= 0.06`
- H4 each axis:
  - median 95% half-width / overall p95 error `<= 1.25`
  - p95 95% half-width / overall p95 error `<= 2.25`
- H5 primary-continuity honesty: each-axis 95% coverage in `[0.88, 0.99]`, p95 width / p95 error `<= 2.75`
- H6 base-output honesty: unchanged P14R rule
- H8 high-severity honesty: unchanged P14R rule
- H9 rescue-output honesty: unchanged P14R rule
- H10 rescue accuracy floor: unchanged P14R rule
- H11 rescue effectiveness: unchanged P14R rule

H7 shift AUROC remains diagnostic only.

**All required gates must pass.** No weighted score can compensate for a failed required gate.

## Stage progression

1. Implementation may iterate only on scale-fit, calibration, unit tests, and the permanently-seen development-smoke split.
2. Freeze the scientific code + candidate hash.
3. Expose seen-transfer seed `913913` once.
4. If and only if all required transfer gates pass, authorize protected seed `924924`.
5. If and only if all required protected gates pass, authorize final seed `935935`.
6. Any failure closes that candidate lineage. A new attempt requires a new preregistered lineage and fresh downstream evidence.

## Stop rules

The following are forbidden after transfer exposure:

- changing the severity anchors, continuity shrinkage exponent, or scale formula;
- changing the robust max rule;
- changing a gate threshold;
- changing transfer / protected / final domains, seeds, or family IDs;
- using Phase 11 protected result rows as model-fit data;
- opening Phase 11 retired P15-v2 holdout seed `869869`;
- rerunning an exposed transfer / protected / final seed after a scientific failure to search for a passing code path.

Software-only reruns that provably do not change scientific data or candidate behavior must be documented as such.

## Claim boundary

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no claim that the synthetic rescue observation matches a real sensor
- no final unseen-replication claim unless the complete Phase 12 progression reaches and passes the frozen final holdout

A Phase 12 pass would support only the narrower simulation claim that adaptive normalized conformal uncertainty improved transfer of interval efficiency while preserving the benchmark's locked availability / honesty gates.