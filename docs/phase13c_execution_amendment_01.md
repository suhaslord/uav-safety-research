# Phase 13C execution amendment 01 — writable-array remediation

## Status

This is a **non-scientific execution amendment recorded before any Phase 13C development evidence was generated or exposed**.

## Failed pre-evidence run

- workflow run: `34009501311`
- development seed named in configuration: `1313135`
- candidate recovery: **not reached**
- Phase 13C evidence generation: **not reached**
- result JSON: **not generated**
- evidence artifact: **not generated**

The run stopped during pre-evidence tests with:

`ValueError: assignment destination is read-only`

The failing path was the `noise_only` component contrast in `scripts/run_phase13c_compound_attribution.py`. Under the runner's pandas behavior, a sliced estimate column returned a read-only NumPy view, and the already-preregistered in-place deterministic noise addition attempted to mutate that view.

## Remediation

The execution-only wrapper `scripts/run_phase13c_compound_attribution_remediation1.py` makes explicit `.copy()` calls for the sliced lateral and altitude estimate arrays before in-place component operations.

Nothing scientific changes:

- development seed remains `1313135` because it was never generated or scored;
- families remain `1393–1416`;
- all thirteen contrasts remain unchanged;
- components A–F remain unchanged;
- all component magnitudes remain unchanged;
- base domain remains unchanged;
- deterministic noise stream remains unchanged;
- frozen Phase 12 candidate remains unchanged;
- C13.1–C13.5 remain unchanged;
- downstream evidence partitions remain unexposed.

The original full-compound path continues to call the frozen Phase 13 domain-13 transform directly. The equivalence fixture remains a mandatory pre-evidence test.

## Claim boundary

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`
