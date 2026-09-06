# Phase 13C development result — Thirteen-Contrast Compound Interaction Attribution

## Verdict

**PASS — the preregistered Phase 13B compound-failure phenomenon replicated on fresh evidence, and the thirteen-contrast attribution study completed without adaptation.**

This is a simulation-only mechanism-attribution result. It does not repair Phase 13A or Phase 13B and does not establish physical UAV safety.

## Canonical evidence identity

- workflow run: `34009627595`
- artifact: `9982053254`
- artifact digest: `sha256:528829389811cd112043f14d1bfe1fff2551ce6a7e2d31103c20f221e5337333`
- scientific Git SHA at exposure: `de181594cbf451f42424ef61f3139351ad0946cd`
- development seed: `1313135`
- families: `1393–1416`
- result JSON SHA-256: `8040a86b7c114a8b122d7e7c16012c5d7edd56bd32d63ad05adaef6a2f2c7264`
- frozen Phase 12 candidate SHA-256: `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`

The earlier run `34009501311` stopped during pre-evidence tests because pandas returned a read-only NumPy view in the `noise_only` contrast. Candidate recovery and evidence generation were never reached. The execution-only remediation is documented in `docs/phase13c_execution_amendment_01.md`; seed `1313135` remained unexposed until the canonical run.

## Phase 13C gates

| Gate | Result | Key value |
|---|---|---|
| C13.1 construction integrity | **PASS** | 13 / 13 contrasts |
| C13.2 full-compound execution equivalence | **PASS** | direct frozen Phase 13 domain-13 path |
| C13.3 fresh failure-phenomenon replication | **PASS** | lateral delta `-0.1230101302`, shifted coverage `0.8263386397` |
| C13.4 attribution completeness | **PASS** | 6 singleton + 6 leave-one-out effects, all finite |
| C13.5 zero adaptation | **PASS** | no candidate/base/component/calibration/controller change |

`phase13c_pass = true`

## Fresh full-compound replication

Matched control on the exact hard domain-13 base distribution:

- lateral 95% coverage: `0.9493487699`
- altitude 95% coverage: `0.9363241679`
- lateral p95 error: `0.2240907306 m`
- altitude p95 error: `0.4515412197 m`
- useful availability: `0.9597222222`

Frozen full compound:

- lateral 95% coverage: `0.8263386397`
- altitude 95% coverage: `0.9052098408`
- lateral coverage delta: **`-0.1230101302`** (`-12.30 pp`)
- altitude coverage delta: `-0.0311143271`
- lateral p95 error: `0.3100306891 m`
- lateral p95 error inflation: `1.3835051911x`
- useful availability: unchanged at `0.9597222222`

The preregistered Phase 13B failure phenomenon therefore replicated on a fresh Phase 13C family partition while remaining above the inherited catastrophic `0.80` lateral-coverage floor.

## Primary attribution finding

The preregistered ranking rules independently selected **component A — fixed 2-frame latency** as both:

1. the largest singleton lateral coverage loss; and
2. the largest leave-one-out recovery from the full compound.

### Singleton lateral coverage losses

| Component | Meaning | Coverage loss vs control |
|---|---|---:|
| **A** | fixed 2-frame latency | **`0.0904486252` (9.04 pp)** |
| C | lateral wind drift | `0.0224312590` (2.24 pp) |
| B | bias pair | `0.0166425470` (1.66 pp) |
| E | innovation response | `0.0000000000` |
| F | severity response | `-0.0007235890` |
| D | measurement-noise pair | `-0.0014471780` |

Latency alone reduced lateral coverage from `94.93%` to `85.89%` and inflated lateral p95 error by `1.3163x`.

### Leave-one-out lateral recovery from the full compound

| Removed component | Recovery vs full compound |
|---|---:|
| **A — latency** | **`0.0911722142` (9.12 pp)** |
| B — bias pair | `0.0246020260` (2.46 pp) |
| C — wind drift | `0.0079594790` (0.80 pp) |
| E — innovation response | `0.0065123010` (0.65 pp) |
| F — severity response | `0.0057887120` (0.58 pp) |
| D — noise pair | `0.0028943560` (0.29 pp) |

Removing latency increased full-compound lateral coverage from `82.63%` to `91.75%`.

## Interaction result

- full lateral coverage loss: `0.1230101302`
- sum of singleton lateral losses: `0.1273516643`
- interaction excess: **`-0.0043415340`** (`-0.43 pp`)

The interaction-excess statistic is slightly negative rather than strongly positive. Under this preregistered synthetic decomposition, the domain-13 failure is therefore **not primarily explained by a super-additive interaction among all six components**.

The strongest supported interpretation is narrower:

> Fixed two-frame latency is the dominant synthetic driver of the domain-13 lateral-coverage failure on this hard base distribution, while bias and wind contribute smaller additional losses and the remaining components have limited stand-alone effect under the frozen study design.

This is an attribution statement about the synthetic Phase 13 transform only, not a physical causal claim about real sensors, wind, aircraft, or flight systems.

## Evidence boundary after development

Per preregistration, development passing does not authorize silent tuning. Before transfer exposure, the discovered mechanism identity and exact effect sizes must be frozen in a separate confirmation note.

No scientific implementation, contrast, magnitude, threshold, candidate, or base domain may change before transfer.

## Claim boundary

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`

Supported claim:

> On fresh simulation-only Phase 13C development evidence, the frozen thirteenth compound failure replicated, and the preregistered thirteen-contrast decomposition identified fixed two-frame latency as the dominant synthetic contributor by both singleton loss and leave-one-out recovery, without model adaptation.
