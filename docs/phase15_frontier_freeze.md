# Phase 15 frontier freeze — recoverability feasibility scale

## Status

**FROZEN BEFORE PHASE 15 DEVELOPMENT EVIDENCE.**

The frontier uses only the already-seen Phase 14 identification artifact. No Phase 15 evaluation seed has been exposed.

## Identity

- freeze run: `34010831493`
- artifact: `9982395324`
- artifact digest: `sha256:5b404072ff6ad103c725b08a778a6b3c14189634041b0c5e7008bd93ed4a49e2`
- scientific SHA: `455332919b475c1d2a5c5072abfbdb806653b810`
- frontier candidate SHA-256: `446501d41bdc14f016026e075a506530c098f294acd71211b569cc38e0925a1b`
- source Phase 14 bridge candidate: `0443d4e45a1966c77544c5c9965de8caec6e622c79ef8c2ce47aee82a3c95981`

## Frozen diagonal coefficients

- lateral `a = 0.6102677720`
- altitude `a = 0.6227394449`

No Phase 15 evaluation role may refit these values.

## Frozen absolute-residual frontier

| q | Lateral residual bound | Lateral minimal RPI half-width | Altitude residual bound | Altitude minimal RPI half-width |
|---:|---:|---:|---:|---:|
| 0.90 | `0.2025000107 m` | `0.5195875428 m` | `0.4549080333 m` | `1.2058192332 m` |
| 0.95 | `0.2764723433 m` | `0.7093905082 m` | `0.6226148791 m` | `1.6503577454 m` |
| 0.975 | `0.3950681603 m` | `1.0136912782 m` | `0.8588857776 m` | `2.2766381644 m` |
| 0.99 | `0.7008800880 m` | `1.7983631779 m` | `1.2699894546 m` | `3.3663457191 m` |

Historical reference half-widths remain fixed comparators:

- lateral `0.30 m`
- altitude `0.85 m`

At q90, the frozen frontier is already:

- lateral `1.7319584760x` the historical reference half-width
- altitude `1.4186108626x` the historical reference half-width

## Interpretation

This freeze does not claim the historical box is invariant. It creates a quantitative residual-based feasibility frontier that fresh Phase 15 partitions can attempt to replicate.

Phase 12 current-state uncertainty remains a separate quantity and will be scored separately during evaluation.

`simulation_only = true`
`safety_acceptance = false`
`controller_tuning_allowed = false`
