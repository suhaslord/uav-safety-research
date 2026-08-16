# Phase 10R trajectory-held-out development/validation result

## Status

**Mixed result — preregistered validation gates did not all pass.**

This result is preserved without post-validation retuning. It is controlled simulation development/validation evidence, not the new protected `phase10r_frozen_holdout` and not a physical-flight safety acceptance.

- candidate freeze commit: `e1d566f8baa47bf10f9bdf39dd5988724208be80`
- GitHub Actions run: `31919732007`
- artifact: `phase10r-development-validation`
- artifact ID: `9256050160`
- artifact ZIP SHA-256: `a9f6836799a4c9eadc16bdaee90ed0ccf517bd2d88be2c22bf132883352262f3`
- development seed: `12345`
- trajectory-held-out validation seed: `271828`
- validation truth-visible frames: `1,200`
- selected partial-view visible-fraction gate: `0.66`
- historical Phase 10 holdout used for selection: **false**

## H1 — detector availability

| Metric | Phase 9 baseline | Phase 10R | Gate | Result |
|---|---:|---:|---:|:---:|
| Difficult truth-visible miss rate | `25.70%` | `8.72%` | ≥40% relative reduction | **PASS — 66.0% reduction** |
| False-positive rate when truth-not-visible | — | `0.0%` | ≤1% | **PASS** |
| Detected-center p95 | `0.4387 px` | `0.4942 px` | ≤1.10× baseline | **FAIL — 1.1265×** |

Phase 10R recovered many edge/partial/stressed observations, but the recovered observations slightly exceeded the preregistered center-error tolerance.

## H2 — ambiguous / partial-view pose

| Metric | Improvement / regression | Gate | Result |
|---|---:|---:|:---:|
| Lateral MAE | **30.1% improvement** | ≥40% improvement | **FAIL** |
| Lateral p95 absolute error | **15.2% improvement** | ≥30% improvement | **FAIL** |
| Altitude MAE | **53.0% improvement** | ≥40% improvement | **PASS** |
| Altitude p95 absolute error | **44.9% improvement** | ≥30% improvement | **PASS** |
| Clean-ArUco lateral MAE regression | `-35.5%` | ≤10% regression | **PASS** |
| Clean-ArUco altitude MAE regression | `-50.0%` | ≤10% regression | **PASS** |
| Visible metric availability drop | `-15.0 pp` | ≤2 pp drop | **PASS** |

Negative availability drop means Phase 10R produced more visible-frame observations than the baseline. The altitude side generalized strongly; the lateral partial-view pose hypothesis did not meet the preregistered magnitude-of-improvement gates.

## H3 — uncertainty calibration

| Metric | Validation result | Gate | Result |
|---|---:|---:|:---:|
| Mean absolute coverage error across 50/68/80/90/95% | **0.84 pp** | ≤5 pp | **PASS** |
| 95% lateral empirical coverage | **94.1%** | 90–98% | **PASS** |
| 95% altitude empirical coverage | **94.1%** | 90–98% | **PASS** |
| Paired 95% lateral interval-width ratio | **0.561×** | ≤1.20× | **PASS** |
| Paired 95% altitude interval-width ratio | **0.498×** | ≤1.20× | **PASS** |

The source-conditional empirical conformal calibration generalized well to the held-out trajectories while remaining narrower than the paired source-only baseline at the 95% target.

## Interpretation

Phase 10R solved a meaningful part of the Phase 10 failure pattern: difficult-frame availability improved sharply and altitude geometry plus uncertainty generalized strongly. It did **not** solve lateral edge/partial-view geometry strongly enough to satisfy the preregistered H1/H2 tolerances.

This is therefore a useful mixed result, not a completed safety claim and not a basis for silently changing the `0.66` gate after validation exposure.

## Next gate

The Phase 10R preregistration requires a **second explicit user approval** before any new protected `phase10r_frozen_holdout` is exposed. Until then:

- validation seed `271828` is permanently seen evidence;
- no post-validation retuning is presented as the same candidate;
- the existing Phase 10 frozen result remains unchanged;
- `safety_acceptance = false`;
- `controller_tuning_allowed = false`.
