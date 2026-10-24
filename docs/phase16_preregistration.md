# Phase 16 preregistration — matched latency level-error / local-dynamics decomposition

## Status

**PREREGISTERED BEFORE ANY PHASE 16 EVALUATION EVIDENCE.**

Phase 16 is a new simulation-only mechanism lineage motivated by the closed Phase 15 falsification. Phase 13A, 13B, Phase 14, and Phase 15 remain immutable failed lineages. Phase 13C remains the frozen successful attribution lineage.

## Scientific question

Can the same pure fixed-two-frame estimate lag simultaneously:

1. worsen **absolute lateral estimation error / Phase 12 interval coverage**, while
2. increase **temporal persistence** and reduce **one-step local error increments / frozen-surrogate residuals**?

If so, that would explain why Phase 13C found latency harmful for absolute uncertainty coverage while Phase 15 found a smaller q90 transition-residual frontier under a latency cohort.

Phase 16 tests this directly with matched no-latency controls on the same simulation base event. It is not a physical-causality experiment.

## Exact frozen latency intervention

Phase 16 uses **only component A from Phase 13C**:

- fixed lag = exactly 2 frames,
- applied to lateral and altitude point estimates,
- no bias,
- no wind/drift,
- no measurement noise,
- no innovation response,
- no severity response,
- no Phase 12 recalibration,
- no controller change.

The scientific implementation must be execution-equivalent to the Phase 13C `latency_only` component path.

This is intentionally narrower than the Phase 13 `fixed_latency_2f` profile, which also changed inference-visible innovation/severity. Phase 16 isolates the stale-estimate effect itself.

## Two matched base contexts

Every Phase 16 stage evaluates both of these frozen base domains:

### Context S — simple latency base

`small_scale+temporal_dropout`

This is the base distribution used by the Phase 13 timing profile and the Phase 15 latency cohort.

### Context H — hard attribution base

`edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout`

This is the exact hard base distribution used by Phase 13C, where pure two-frame latency was the dominant synthetic contributor to lateral coverage loss.

For each context and stage:

1. generate one base event,
2. copy it as the no-latency control,
3. apply only the frozen Phase 13C latency component to the paired shifted copy,
4. retain a stable pair identifier before applying the suffix/metadata changes.

Control and latency copies must have identical:

- row counts,
- truth-visible masks,
- useful-availability masks,
- truth values,
- Phase 12 half-widths on matched rows.

## Frozen predecessor identities

Phase 12 candidate SHA-256:

`e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`

Phase 14 bridge candidate SHA-256:

`0443d4e45a1966c77544c5c9965de8caec6e622c79ef8c2ce47aee82a3c95981`

Frozen Phase 14 diagonal coefficients used only for the one-step residual diagnostic:

- lateral `a_x = 0.6102677720`
- altitude `a_z = 0.6227394449`

These coefficients are never refit in Phase 16.

Historical reference box remains descriptive only:

- lateral `0.30 m`
- altitude `0.85 m`

## Fresh evidence roles

| Role | Seed | Families | Rule |
|---|---:|---:|---|
| development | `1616161` | `1713–1736` | first pass/fail role; permanently seen after run |
| transfer | `1616162` | `1737–1760` | expose only if development passes |
| protected | `1616163` | `1761–1784` | expose only if transfer passes |
| final | `1616164` | `1785–1808` | expose exactly once only if protected passes |

## Primary lateral metrics

The mechanism question is lateral-primary because Phase 13C's replicated failure and attribution were lateral-primary. Altitude is always reported but is secondary/descriptive unless required by construction integrity.

### Level-error metrics

On all matched useful rows:

- Phase 12 lateral 95% coverage,
- lateral median absolute error,
- lateral p95 absolute error,
- latency/control p95-error inflation ratio,
- latency-minus-control coverage delta.

### Matched temporal metrics

Construct adjacent one-frame transitions and retain only pair keys present in both control and latency copies.

For the temporal-primary matched subset, the current transition must begin inside the historical box in **both** control and latency copies.

Report:

1. no-intercept diagnostic persistence coefficient
   `a_diag = sum(e[k]e[k+1]) / sum(e[k]^2)`
2. adjacent signed-error Pearson correlation,
3. q90 raw increment magnitude `|e[k+1]-e[k]|`,
4. q90 frozen-Phase14 residual magnitude `|e[k+1]-a_x e[k]|`,
5. corresponding diagnostic q90 minimal RPI half-width
   `r90 = q90_residual / (1-|a_x|)`.

The diagnostic persistence coefficient is not used to change the frozen Phase 14 coefficient.

## Locked gates

A stage passes only if every gate passes.

### L16.1 — paired construction integrity

For both Context S and Context H:

- identical row counts,
- identical truth-visible masks,
- identical useful-availability masks,
- identical lateral/altitude truth,
- at least 500 matched temporal transitions after the both-inside-box filter.

### L16.2 — Phase 12 width identity under pure lag

Because component A changes only point estimates, not inference-visible reliability features, matched control and latency rows must have identical Phase 12 95% half-widths to numerical tolerance `1e-12` on both axes in both contexts.

### L16.3 — lateral level-error degradation replicates

Context S must satisfy both:

- lateral p95 error inflation `>= 1.15x`,
- lateral coverage delta `<= -0.01`.

Context H must satisfy both:

- lateral p95 error inflation `>= 1.15x`,
- lateral coverage delta `<= -0.05`.

These thresholds are below the already-seen Phase 13B / Phase 13C effect sizes and are frozen before Phase 16 development.

### L16.4 — matched lateral persistence increases

In both contexts:

- latency diagnostic `a_diag - control a_diag >= 0.10`, and
- latency adjacent-error correlation minus control correlation `>= 0.10`.

### L16.5 — raw one-step lateral increments compress

In both contexts:

`q90(|Delta e|)_latency / q90(|Delta e|)_control <= 0.90`.

### L16.6 — frozen-surrogate lateral residuals compress

Using frozen Phase 14 `a_x` in both contexts:

`q90(|e[k+1]-a_x e[k]|)_latency / control <= 0.90`.

### L16.7 — q90 residual frontier compresses

Because the same frozen `a_x` is used for control and latency, the q90 residual-based RPI frontier ratio must satisfy in both contexts:

`r90_latency / r90_control <= 0.90`.

This gate is algebraically redundant with L16.6 but is retained as an explicit recoverability-facing audit quantity.

### L16.8 — divergence is context-stable

Both Context S and Context H must simultaneously show:

- worse lateral p95 level error under latency, and
- smaller lateral q90 frozen-surrogate residual under latency.

### L16.9 — no refit / no adaptation

Required:

- exact frozen Phase 12 candidate,
- exact frozen Phase 14 bridge candidate,
- no refit of Phase 14 `a`,
- no intervention magnitude change,
- no post-development threshold change,
- no controller tuning.

### L16.10 — claim boundary

Required:

- `simulation_only = true`,
- `safety_acceptance = false`,
- `controller_tuning_allowed = false`.

## Stop rules

1. Development failure closes Phase 16; all later seeds remain unexposed.
2. Transfer failure leaves protected/final unexposed.
3. Protected failure leaves final unexposed.
4. Final is exposed once and never rerun for a better scientific outcome.
5. Pre-evidence technical failures may be repaired only if the intervention, metrics, thresholds, predecessor identities, and evidence role remain unchanged.

## Supported interpretation if Phase 16 passes

A PASS would support only:

> In two matched AegisLand simulation contexts, the frozen pure two-frame estimate lag increased lateral level error while increasing temporal persistence and reducing one-step lateral residual magnitude under the frozen Phase 14 surrogate, providing a simulation-only explanation for why absolute uncertainty coverage and residual-based recoverability diagnostics can move in opposite directions.

It would not establish a physical latency mechanism, physical-flight safety, controller safety, full-simulator invariance, certification relevance, or operational reliability.
