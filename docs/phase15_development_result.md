# Phase 15 development result — recoverability feasibility frontier

## Verdict

**FAIL — Phase 15 closes at development on one preregistered gate.**

The natural residual-based feasibility frontier replicated strongly, but the exact fixed-two-frame latency cohort falsified the preregistered claim that the q90 transition-residual frontier would remain above the historical reference box on both axes.

Per the stop rule, Phase 15 transfer, protected, and final evidence remain unexposed.

## Evidence identity

- development run: `34010895342`
- artifact: `9982419806`
- artifact digest: `sha256:5d2653dfe96f9d6fc5a056fe41cb56614e3f94288322750a0d5d3fec27158714`
- result JSON SHA-256: `c13aac7de1d6584ecca4ccad89aaa3d40556b2d96952323bb040b19508a7d562`
- development seed: `1515151`
- families: `1617–1640`
- scientific SHA: `455332919b475c1d2a5c5072abfbdb806653b810`
- frontier candidate SHA-256: `446501d41bdc14f016026e075a506530c098f294acd71211b569cc38e0925a1b`

## Gate result

Passed:

- F15.1 lineage integrity
- F15.2 frontier construction integrity
- F15.3 natural residual-envelope replication
- F15.4 natural q90 infeasibility replication
- F15.5 natural state-uncertainty nontriviality
- F15.6 latency residual-envelope replication
- F15.8 latency state-uncertainty nontriviality
- F15.9 frontier direction stability
- F15.10 zero adaptation / claim boundary

Failed:

- **F15.7 latency q90 infeasibility replication**

## Natural cohort — strong replication

Eligible transitions beginning inside the historical box: `8,696`.

Phase 12 state-uncertainty containment fraction:

- `0.4903403864` = **49.03%**
- locked minimum: `25%`

### Lateral

Frozen frontier coverage on fresh natural evidence:

- q90 bound coverage: `0.8908693652`
- q95: `0.9466421343`
- q97.5: `0.9724011040`
- q99: `0.9899954002`

Fresh diagnostic minimal RPI half-widths:

- q90: `0.5406707590 m`
- q95: `0.7304228610 m`
- q97.5: `1.0971981853 m`
- q99: `1.8229009340 m`

Fresh q90 / historical reference ratio:

- **`1.8022358633x`**

### Altitude

Frozen frontier coverage:

- q90: `0.8976540938`
- q95: `0.9503219871`
- q97.5: `0.9767709292`
- q99: `0.9906853726`

Fresh diagnostic minimal RPI half-widths:

- q90: `1.2200962013 m`
- q95: `1.6458591770 m`
- q97.5: `2.1932494236 m`
- q99: `3.2438183244 m`

Fresh q90 / historical reference ratio:

- **`1.4354072957x`**

The natural cohort therefore reproduces the Phase 14 conclusion: the historical `0.30 / 0.85 m` box lies below even the q90 residual-based surrogate frontier.

## Fixed-two-frame latency cohort — preregistered falsification

Eligible transitions: `1,366`.

Phase 12 state-uncertainty containment fraction:

- `0.6515373353` = **65.15%**

The frozen residual bounds covered the latency residuals comfortably:

### Lateral frozen-bound coverage

- q90: `0.9787701318`
- q95: `0.9934114202`
- q97.5: `0.9992679356`
- q99: `1.0`

Fresh diagnostic minimal RPI half-widths:

- q90: **`0.2982139604 m`**
- q95: `0.3803249938 m`
- q97.5: `0.4826989697 m`
- q99: `0.6648514118 m`

The q90 lateral frontier is slightly below the historical `0.30 m` comparator:

- ratio: **`0.9940465348x`**

### Altitude frozen-bound coverage

- q90: `0.9853587116`
- q95: `0.9948755490`
- q97.5: `0.9992679356`
- q99: `1.0`

Fresh diagnostic minimal RPI half-widths:

- q90: **`0.5549244860 m`**
- q95: `0.7595800266 m`
- q97.5: `0.9950998449 m`
- q99: `1.4622291484 m`

The q90 altitude frontier is well below the historical `0.85 m` comparator:

- ratio: **`0.6528523365x`**

Thus F15.7 fails on both axes.

## Scientific interpretation

This does not reverse Phase 13C. Phase 13C showed that fixed two-frame latency is the dominant synthetic contributor to **absolute lateral uncertainty-coverage degradation** on the hardest compound domain.

Phase 15 measures a different object: **one-frame transition residual magnitude under a frozen diagonal error surrogate**.

The fresh latency result shows those quantities can move in opposite directions. A two-frame stale estimate can increase persistent/level error while simultaneously making consecutive error states more slowly varying, which can reduce the one-step residual `|e[k+1] - a e[k]|`.

That hypothesis was not preregistered as a Phase 15 PASS condition and is therefore only a mechanism interpretation to test in a new lineage.

## Evidence boundary

Permanently exposed in Phase 15:

- development `1515151`

Phase 15 freeze used only already-seen Phase 14 identification evidence and exposed no new evaluation role.

Remain unexposed and prohibited in this Phase 15 lineage:

- transfer `1515152`
- protected `1515153`
- final `1515154`

`simulation_only = true`
`safety_acceptance = false`
`controller_tuning_allowed = false`

No physical-flight, full-simulator invariance, certification, production-readiness, controller-improvement, or operational-safety claim is made.
