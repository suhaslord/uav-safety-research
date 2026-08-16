# Phase 11 P6 candidate freeze — source-conditional continuity calibration

## Status

**CANDIDATE FROZEN BEFORE PROTECTED VALIDATION EXPOSURE**

P6 preregistration: `docs/phase11_p6_source_conditional_preregistration.md`

Candidate-freeze workflow:

- run: `31972988822`
- scientific freeze head SHA: `33e6ff85baa71f796bdcdb7dab2bc26f14b8f71a`
- artifact ID: `9270300062`
- artifact digest: `sha256:09a5b14a6ab374007b3d577dfaab41a195a44f94d2058bd0b57bcbd3f6dac4ca`
- `candidate_freeze.json` SHA-256: `2bbb91fd0cb45ef11ba4411b406f4b311eff8c5d24020a7e7a64df823ac68073`
- `transfer_result.json` SHA-256: `ec2ba41ef9417e7cdc6abaa3daf6ecdb9e23d100fcb76ded684dab42631d3c62`

Protected validation seed `286286` is ungenerated/unseen at this checkpoint.

## Frozen candidate

P6 keeps the P5 perception-continuity method unchanged:

- maximum total continuity horizon: `5` frames;
- damping: `0.85`;
- velocity-cap rule: fit-derived per-axis absolute slope q99;
- genuine outputs only as motion-history anchors;
- no inherited-bridge or continuity-extension output can become an anchor;
- no future information or truth labels are inference inputs.

P6 changes only the second-stage compositional calibration:

- group `base_output` for all available non-continuity outputs;
- group `continuity_extension` for P5 continuity rows;
- no pooled fallback;
- minimum transfer rows: `200` base / `40` continuity.

All scale-model and single-factor conformal rules remain the P5 rules, including ridge lambda `4.0` and nested intervals.

## Seen transfer-calibration checkpoint

Evidence role: `phase11_p6_seen_source_conditional_transfer`

Seen transfer seed: `275275` — permanently seen after this checkpoint.

Group counts:

- `base_output`: `1353` rows;
- `continuity_extension`: `64` rows.

All preregistered development gates passed:

| Gate | Frozen seen-transfer result | Verdict |
|---|---:|---|
| H1 availability | `98.40%` | PASS |
| H2 lateral 95% overall coverage | `95.20%` | PASS |
| H2 altitude 95% overall coverage | `95.20%` | PASS |
| H3 calibration MACE | `0.001537` | PASS |
| H4 lateral median width / p95 error | `0.663x` | PASS |
| H4 lateral p95 width / p95 error | `1.027x` | PASS |
| H4 altitude median width / p95 error | `0.769x` | PASS |
| H4 altitude p95 width / p95 error | `1.383x` | PASS |
| H5 continuity lateral 95% coverage | `96.88%` | PASS |
| H5 continuity altitude 95% coverage | `96.88%` | PASS |
| H5 continuity lateral p95 width / error | `1.486x` | PASS |
| H5 continuity altitude p95 width / error | `1.047x` | PASS |
| H6 base lateral 95% coverage | `95.12%` | PASS |
| H6 base altitude 95% coverage | `95.12%` | PASS |
| H6 base lateral p95 width / error | `1.274x` | PASS |
| H6 base altitude p95 width / error | `1.378x` | PASS |
| H7 trajectory shift AUROC | `0.9462` | diagnostic PASS |

Overall development verdict: **PASS — eligible for exactly one protected P6 validation exposure.**

## Validation exposure lock

The protected validation run must:

1. download the exact candidate artifact `9270300062` from workflow run `31972988822`;
2. verify candidate SHA-256 `2bbb91fd0cb45ef11ba4411b406f4b311eff8c5d24020a7e7a64df823ac68073`;
3. verify the P6 scientific script, invariant tests, and preregistration are unchanged from freeze SHA `33e6ff85baa71f796bdcdb7dab2bc26f14b8f71a`;
4. expose seed `286286` only after those checks succeed;
5. freeze the resulting outcome without retuning.

After seed `286286` is exposed it becomes permanently seen regardless of outcome.

A successful P6 protected validation does **not** authorize any final Phase 11 frozen holdout. That remains behind a separate explicit user approval checkpoint.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
