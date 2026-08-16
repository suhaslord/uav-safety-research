# Phase 11 P4 candidate freeze — all-available calibrated uncertainty

## Status

**CANDIDATE FROZEN BEFORE PROTECTED VALIDATION**

P4 preregistration: `docs/phase11_p4_all_available_preregistration.md`

Freeze workflow:

- run: `31970592820`
- freeze code/head SHA: `79e85654516cfec27aaf017f4119e90820e6f9d7`
- artifact ID: `9269679511`
- artifact digest: `sha256:390ce0ecfa56fcc01357b58b96b45ffb80a2fd0a2dd37ae7adf3af648e4cffd2`
- artifact candidate JSON SHA-256: `09be4cd8cce775e74addb65964454d0a4116c8c933f4811fbba3c77de1232ecb`
- artifact transfer-result SHA-256: `3e05d96dffeee1982b85ea3373f2fb37eb2be45405f10c94f636ba3409964b4d`

The workflow passed all P4 invariant tests and verified that protected validation seed `198198` was not generated during candidate freeze.

The committed `results/phase11_p4/candidate_freeze.json` is a semantic copy of the frozen candidate used by the validation runner. The immutable Actions artifact/hash above remains the byte-authoritative freeze receipt.

## Seen transfer-calibration gates

All preregistered development gates passed:

| Gate | Frozen development result | Verdict |
|---|---:|---|
| H1 lateral 95% coverage | `95.14%` | PASS |
| H1 altitude 95% coverage | `95.14%` | PASS |
| H2 calibration-curve MACE | `0.000912` | PASS |
| H3 lateral median half-width / p95 error | `0.623x` | PASS |
| H3 altitude median ratio | `0.739x` | PASS |
| H3 lateral p95 half-width / p95 error | `1.506x` | PASS |
| H3 altitude p95 ratio | `1.417x` | PASS |
| H4 preselection availability | `94.24%` | PASS |
| H5 trajectory-level shift AUROC | `0.94097` | PASS |

Overall seen-development result: **PASS — candidate eligible for protected validation.**

## Frozen model details

- ridge lambda: `4.0`;
- target winsorization: fit-split log-error q02/q98 per axis;
- prediction guard: fit-prediction q01/q99 expanded by `0.35` log units;
- no hand-written multiplicative risk inflation;
- no severity acceptance threshold;
- no interval-width abstention in primary evaluation;
- two-stage finite-sample conformal calibration: single-factor then seen-composition transfer;
- protected validation seed: `198198`;
- protected validation families: `69..71`.

No coefficient, basis term, winsor bound, prediction guard, conformal quantile, transfer multiplier, gate, or seed may change after this freeze and before protected validation.

## Exposure boundary

Seed `198198` is still **unseen at this freeze checkpoint**. The next allowed action is exactly one protected-validation evaluation of this frozen P4 candidate.

Passing that protected validation would still not authorize the final Phase 11 holdout; the final holdout remains subject to a separate explicit approval checkpoint.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
