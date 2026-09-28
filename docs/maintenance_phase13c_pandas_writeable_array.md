# Maintenance note — Phase 13C Pandas/NumPy writable-array compatibility

## Scope

This is a non-scientific compatibility repair performed only after the Phase 20 scientific lineage was sealed.

The repository-wide CI failure was inherited from the historical Phase 13C `noise_only` fixture under the current Pandas/NumPy stack:

`ValueError: assignment destination is read-only`

The failure occurred because two arrays produced from `.loc[...].to_numpy(float)` were not guaranteed writable before the existing in-place deterministic noise mutation.

## Change

Only these two local extraction statements changed:

- lateral estimate slice now ends with `.copy()`;
- altitude estimate slice now ends with `.copy()`.

No seed, family, domain, component magnitude, deterministic noise stream, candidate, threshold, gate, control policy, Phase 12 interval, or scientific result was changed.

The historical Phase 13C evidence remains immutable. This patch is not a rerun, reinterpretation, or replacement of any evidence artifact.

## Boundary

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`
