# Phase 11 P9 development stop — soft update + direct grouped conformal

## Status

**DEVELOPMENT STOP BEFORE CANDIDATE FREEZE — TRANSFER / PROTECTED VALIDATION NOT EXPOSED**

P9 preregistration: `docs/phase11_p9_soft_update_direct_conformal_preregistration.md`

Development workflow:

- run: `31974299425`
- workflow/scientific head: `03adfb90c540170bf1346868a2ec1029672ddefa`
- invariant tests: PASS (`4 passed`)
- failure stage: candidate construction from fresh fit + grouped calibration evidence

## Exposure ledger

The candidate-freeze stage generated the fit and grouped-calibration splits before the preregistered sample-size assertion stopped construction.

Therefore these seeds are permanently **seen**:

- fit: `407407`
- grouped calibration: `418418`

The workflow stopped before either later stage ran:

- transfer seed `429429`: **NOT EXPOSED**;
- protected validation seed `440440`: **NOT EXPOSED**.

Both unexposed seeds are retired with P9 rather than recycled into a future revision.

## Failure

P9 preregistered four direct-conformal calibration groups and minimum counts before data generation:

- `base_output >= 1000`;
- `continuity_h3 >= 120`;
- `continuity_h45 >= 60`;
- `continuity_h67 >= 30`.

Observed grouped-calibration `continuity_h3` rows: **`110`**.

Candidate construction correctly stopped with:

`RuntimeError: P9 calibration group continuity_h3 rows 110 < 120`

Because the exact candidate was never created, no P9 transfer-performance or interval-performance claim is made.

## Interpretation

This is a power/sample-size failure, not evidence for or against the P9 soft-update/direct-conformal hypothesis.

The correct next step is **not** to lower the `120`-row minimum after seeing `110`. A new revision should preserve the P9 scientific method and use fresh evidence with a larger grouped-calibration cohort so every preregistered horizon group has enough observations before a candidate is frozen.

## Next revision

P10 should be a powered replication of P9 with:

- the same soft bounded-influence anchor update;
- the same velocity/innovation-scale rules;
- the same four direct absolute-error conformal groups;
- the same group minimums and H1-H6 gates;
- fresh fit/calibration/transfer/validation seeds and families;
- more grouped-calibration trajectory families than P9;
- no reuse of P9 `407407` / `418418` as hidden evidence.

P10 must preregister before generation.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
