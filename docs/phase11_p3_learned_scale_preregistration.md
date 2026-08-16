# Phase 11 P3 preregistration — learned scale without hand risk multiplier

## Status

**PREREGISTERED BEFORE P3 DATA GENERATION**

Branch: `phase11-p3-learned-scale-transfer`

P0 `33033`, duplicate `63333`, P1 `77077`, and P2 transfer seed `101101` are permanently seen. P2 protected validation seed `112112` remains ungenerated and is retired from use rather than recycled.

## Research question

**Can a low-capacity learned error-scale model absorb coactivation and bridge risk directly, avoiding P2's extreme interval tails while retaining two-stage compositional conformal calibration?**

P3 is still simulation-only reliability-layer development. It does not change the frozen Phase 10R image-to-pose candidate or controller behavior.

## Motivation

P2's seen transfer split achieved excellent calibration (`95.12%` on both axes; coverage-curve MACE `0.000784`) and high availability (`97.08%` after its uncertainty budget), but p95 interval tails were inefficient (`5.705x` lateral / `3.332x` altitude relative to p95 error).

The P2 diagnostic is that the P1 ridge scale model already models risk, while the inherited multiplicative rule `1 + 3*coactivation + 6*risk + 2*bridge` expands the same high-risk state again. P3 removes that hand multiplier entirely and adds compact coactivation/top-risk terms to the learned scale basis.

## New P3 splits

- fit seed: `121121`
- single-factor calibration seed: `132132`
- compositional transfer-calibration seed: `143143`
- protected validation seed: `154154`
- frames per sequence: `60`

Trajectory families:

- fit: `42..47`
- calibration: `48..50`
- transfer calibration: `51..53`
- protected validation: `54..56`

Complete sequences are the separation unit.

### Fit / calibration domains

1. `nominal`
2. `edge`
3. `small_scale`
4. `oblique`
5. `dim`
6. `blur_noise`
7. `temporal_dropout`
8. `low_contrast`

### Seen transfer-calibration compositions

1. `edge+blur_noise`
2. `small_scale+dim`
3. `oblique+temporal_dropout`
4. `blur_noise+low_contrast`
5. `edge+small_scale+dim`
6. `small_scale+oblique+temporal_dropout`
7. `edge+dim+low_contrast`
8. `oblique+blur_noise+temporal_dropout`

### Protected validation compositions

1. `edge+small_scale`
2. `oblique+dim`
3. `blur_noise+temporal_dropout`
4. `edge+oblique+low_contrast`
5. `small_scale+blur_noise+low_contrast`
6. `edge+dim+temporal_dropout`
7. `small_scale+oblique+dim+blur_noise`
8. `edge+small_scale+oblique+temporal_dropout+low_contrast`

Validation seed `154154` must not be generated before the candidate-freeze checkpoint.

## Frozen estimator layer

Inherited unchanged from P1:

- factor-identifiable appearance cues;
- non-recursive constant-velocity bridge, maximum horizon `2`;
- eight inference-visible risk components;
- source categories.

No global severity acceptance threshold is used.

## P3 scale model

Separate lateral and altitude ridge models predict log absolute error scale from available fit observations.

Fixed ridge lambda: `2.0`.

The exact feature basis is:

1. intercept;
2. eight P1 risk components: edge, scale, oblique, dim, blur, contrast, temporal, track;
3. scalar risk score;
4. risk score squared;
5. normalized coactivation count `coactivation_count / 7`;
6. normalized coactivation squared;
7. largest primary risk component;
8. second-largest primary risk component;
9. bridge horizon;
10. bridge horizon × risk score;
11. source one-hots: partial-edge, regeometry, known-ArUco-refined, temporal-bridge.

No explicit multiplicative risk inflation is applied after predicted scale.

## Single-factor calibration

On every available truth-visible single-factor calibration row:

`normalized_residual = abs_error / max(predicted_scale, 1e-9)`

For targets `{0.50,0.68,0.80,0.90,0.95}`, compute the finite-sample conformal order statistic `ceil((n+1)*q)`.

## Compositional transfer calibration

On every available truth-visible seen transfer row, form the provisional radius:

`R_single(axis,q) = Q_single(axis,q) * predicted_scale`

Then:

`transfer_ratio = abs_error / max(R_single, 1e-9)`

Freeze `T(axis,q)` as the finite-sample q conformal quantile of transfer ratios.

Final radius:

`R_P3(axis,q) = Q_single(axis,q) * predicted_scale * T(axis,q)`

Final target radii are monotonized by cumulative maximum over increasing q to guarantee nested intervals.

## Last-resort uncertainty budget

On the seen transfer split, freeze per-axis 95% half-width budget:

`budget(axis) = 1.10 * q99(P3 95% half-width)`

An available output is accepted only if both axis 95% half-widths are within budget. No truth error or severity cutoff enters this decision.

## Primary gates

### H1 — full-availability 95% coverage

Before budget abstention, protected-validation 95% coverage must be in `[0.90,0.98]` on both axes.

### H2 — calibration curve

Before abstention, mean absolute coverage error across `{50%,68%,80%,90%,95%}` over both axes must be `<=0.06`.

### H3 — interval-tail efficiency

Before abstention:

- median 95% half-width / all-available p95 error `<=1.25` on each axis;
- p95 95% half-width / all-available p95 error `<=2.25` on each axis.

All four conditions must pass.

### H4 — uncertainty-budget usefulness

After budget abstention:

- retain `>=90%` of preselection-available outputs;
- truth-visible usable availability `>=80%`;
- accepted p95 error does not exceed all-available p95 error on either axis.

### H5 — shift discrimination

Trajectory-level mean P1 severity AUROC between single-factor calibration and protected compositional validation must be `>=0.85`.

## Candidate-freeze rule

No feature, lambda, calibration rule, target set, transfer rule, nesting rule, budget quantile, or budget scale may change after this preregistration within P3.

Fit/calibration/transfer may be generated. Their fixed coefficients and transfer values must be archived before validation seed `154154` is exposed.

If the seen transfer split already fails P3 interval-tail efficiency badly, P3 may be stopped before validation and `154154` left ungenerated.

## Validation exposure policy

Once `154154` is generated/evaluated, it is permanently seen. Any method change after that requires P4 with new evidence.

A separate final Phase 11 frozen holdout is still **not generated or approved** by this protocol.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
- negative/mixed outcomes remain publishable evidence
