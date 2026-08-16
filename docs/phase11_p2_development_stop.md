# Phase 11 P2 development stop — composition-calibrated uncertainty budget

## Status

**DEVELOPMENT FROZEN — PROTECTED VALIDATION NOT EXPOSED**

P2 preregistration: `docs/phase11_p2_composition_calibrated_preregistration.md`

Freeze workflow:

- run: `31970116572`
- head SHA: `818af49c3bec7c55cfe7880e8e4d5c0f7ec91e50`
- artifact ID: `9269551595`
- artifact digest: `sha256:b654f03de9aa0c1f0ea5b0b90859cbe6031481d59a216bed10ddaae1072a1e25`
- candidate JSON SHA-256: `f4391e71d1c1e1f5cb2c6b8a094f3f60b8ce321067835ca1b63ec99c43443e81`
- transfer-result SHA-256: `8d01f37551c88197ca5062122690fffdd402720452666588bb50c81fc5c16ab8`

The freeze workflow's invariant test verified that validation seed `112112` was **not generated** and that no validation frames/result existed in the artifact.

## Seen transfer-calibration result

Evidence role: `phase11_p2_seen_transfer_calibration`

The two-stage composition calibration worked extremely well for coverage on the seen transfer split:

- lateral 95% coverage: `95.12%` — development component pass;
- altitude 95% coverage: `95.12%` — development component pass;
- mean absolute coverage error across 50/68/80/90/95 targets: `0.000784` — development component pass;
- uncertainty-budget retention conditional on availability: `98.80%`;
- truth-visible usable availability after budget: `97.08%`;
- trajectory-level shift AUROC: `0.9392`.

However, P2 exposed a new failure mode in interval-tail efficiency:

- lateral median 95% half-width / p95 error: `0.851x`;
- altitude median ratio: `0.856x`;
- lateral p95 95% half-width / p95 error: **`5.705x`**;
- altitude p95 ratio: **`3.332x`**.

The preregistered P2 efficiency gate requires the p95 ratios to be `<=2.25x`; the seen transfer result therefore fails that component badly.

## Decision before validation

P2 protected validation seed `112112` is intentionally **not exposed**.

The development evidence is already sufficient to reject this candidate as an efficient uncertainty method. Exposing a protected validation split for a candidate with a known preregistered development pathology would spend unseen evidence without scientific benefit.

The failure is consistent with double-counting high-risk state:

1. the P1 ridge scale model already contains the inference-visible risk components, risk score, nonlinear risk term, bridge state, and source;
2. P2 then multiplies that prediction by the inherited hand multiplier `1 + 3*coactivation + 6*risk + 2*bridge`;
3. composition calibration restores empirical coverage, but extreme high-risk rows inherit very large interval tails.

This interpretation is a development diagnosis only. It is not a validation claim.

## Next revision

P3 should test whether the hand multiplier can be removed and its useful information represented directly inside a low-capacity error-scale model, followed by the same two-stage single-factor + compositional transfer calibration.

P3 must use new fit/calibration/transfer/validation seeds and new trajectory families. It may not tune on P0 `33033`, duplicate `63333`, P1 `77077`, or any P2 seen transfer rows as hidden evidence.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
