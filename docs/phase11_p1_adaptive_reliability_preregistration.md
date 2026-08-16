# Phase 11 P1 duplicate draft — superseded / non-authoritative

## Status

**ABORTED DUPLICATE — DO NOT USE AS THE P1 PROTOCOL**

This file records a duplicate P1 design drafted after the authoritative P1 candidate had already been frozen and validated on this branch.

The authoritative P1 protocol/freeze is:

- `docs/phase11_p1_candidate_freeze.md`
- candidate implementation commit `445606c9b962a3452af5565c5291562369660eb8`
- protected validation seed `77077`
- authoritative validation workflow run `31968903756`
- authoritative result `docs/phase11_p1_validation_result.md`

That P1 result is permanently frozen as **mixed / failed overall**.

## Duplicate-exposure ledger

During a later continuation attempt, a separate simple continuous-severity draft was sketched with seeds:

- fit `41111`
- calibration `52222`
- challenge `63333`

Challenge seed `63333` was generated/evaluated once locally before the pre-existing authoritative P1 freeze/result was rediscovered. It is therefore **permanently seen** and may never be used as a hidden, protected, or frozen test in any later Phase 11 revision.

The duplicate draft produced an overall failed exploratory result and is not an authoritative P1 benchmark. No conclusion from it overrides or modifies the frozen P1 validation result.

## Scientific boundary

Do not merge the duplicate method into the authoritative P1 candidate and do not retune or re-evaluate it on `63333` as unseen evidence.

Any follow-up after P1 must be named a new benchmark revision (P2 or later), use new seeds/families, preregister its method before challenge/validation exposure, and preserve all prior negative/mixed evidence.

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
