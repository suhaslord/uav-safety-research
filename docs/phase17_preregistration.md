# Phase 17 preregistration — Context-Conditional Coefficient Mismatch Audit

## Status

**PREREGISTERED BEFORE PHASE 17 FIT EVIDENCE.**

Phase 16 is immutable and remains a valid development FAIL. Phase 17 is a new scientific lineage. It does not modify, reinterpret into a pass, or rerun Phase 16.

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`

No physical-flight, real-sensor, certification, production-readiness, controller-improvement, or operational-safety claim is authorized by this study.

## Motivation from the already-seen Phase 16 result

Phase 16 used exact matched control / pure-two-frame-lag pairs and found:

- lateral level error worsened under latency in both preregistered contexts;
- Phase 12 95% half-widths remained exactly identical between control and latency;
- temporal persistence increased strongly under latency;
- the stronger preregistered claim that raw increments and the frozen Phase 14 residual would compress was false.

The already-seen Phase 16 development diagnostics were heterogeneous:

- simple context latency diagnostic coefficient: approximately `0.843`, versus frozen Phase 14 lateral `a = 0.6102677720`;
- hard context latency diagnostic coefficient: approximately `0.582`, close to frozen Phase 14 lateral `a`.

That observation motivates a new question. It is not Phase 17 evidence.

## Scientific question

> Does pure two-frame latency create a reproducible, context-dependent mismatch between the effective one-step lateral error-propagation coefficient and the frozen Phase 14 coefficient, such that a separately fitted latency coefficient materially reduces out-of-sample residuals in the simple context but provides little advantage in the hard context?

This is a mechanism-identification study about the synthetic simulation transform only.

## Frozen intervention

Phase 17 uses the same pure latency intervention as Phase 16 and Phase 13C component A:

- lag: exactly `2` frames;
- point-estimate lag only;
- no innovation-response change;
- no severity-response change;
- no bias;
- no wind;
- no measurement-noise addition;
- no Phase 12 recalibration;
- no controller change.

The exact frozen Phase 12 candidate remains:

`e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`

The exact frozen Phase 14 bridge candidate remains:

`0443d4e45a1966c77544c5c9965de8caec6e622c79ef8c2ce47aee82a3c95981`

The frozen Phase 14 lateral coefficient is:

`a_phase14 = 0.6102677720` approximately, read from the exact candidate at execution.

## Frozen contexts

### Context S — simple

`small_scale+temporal_dropout`

### Context H — hard

`edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout`

No context may be added, removed, or substituted after fit evidence is exposed.

## Evidence partitions

Every role uses exactly 24 fresh families split evenly across the inherited four strata (`bootstrap5`, `gap3`, `gap7`, `gap12`).

| Role | Seed | Families | Purpose |
|---|---:|---|---|
| fit | `1717170` | `1809–1832` | identify and freeze context/cohort coefficients only |
| development | `1717171` | `1833–1856` | first out-of-sample confirmation |
| transfer | `1717172` | `1857–1880` | only after development PASS |
| protected | `1717173` | `1881–1904` | only after transfer PASS |
| final | `1717174` | `1905–1928` | only after protected PASS |

No Phase 16 family or seed is reused.

## Matched construction

For each context and evidence role:

1. generate one frozen base event;
2. create an unchanged control copy;
3. create a latency copy using only the pure two-frame lag;
4. preserve row count, pair identity, truth-visible mask, useful-availability mask, truth values, severity, and anchor-innovation inputs;
5. verify Phase 12 95% half-width identity to numerical tolerance `1e-12`.

The primary temporal subset contains one-to-one matched adjacent transitions where both control and latency copies begin inside the historical reference box:

- lateral `|e_x| <= 0.30 m`;
- altitude `|e_z| <= 0.85 m`.

The historical box is a reference analysis region only. Phase 17 does not claim it is a physically invariant set.

## Frozen coefficient form

For each context, cohort (`control`, `latency`), and axis, fit one no-intercept diagonal one-step coefficient on the fit partition only:

`e_{t+1} = a * e_t + r_t`

with

`a = sum(e_t * e_{t+1}) / sum(e_t^2)`.

Rules:

- no intercept;
- no regularization;
- no clipping;
- no post-hoc shrinkage;
- no context pooling;
- no family weighting beyond the generated rows;
- coefficient must be finite and satisfy `|a| < 0.98`;
- at least `500` matched temporal transitions per context are required.

The frozen Phase 17 fit candidate stores all context/cohort/axis coefficients and the scientific Git SHA. Development may read but may not modify them.

## Residual definitions for out-of-sample evaluation

On fresh development latency rows, compute lateral absolute one-step residuals under three frozen coefficients:

1. **Phase 14 residual**
   `|e_{t+1} - a_phase14 * e_t|`

2. **Phase 17 control-coefficient residual**
   `|e_{t+1} - a_fit(context, control, lateral) * e_t|`

3. **Phase 17 latency-coefficient residual**
   `|e_{t+1} - a_fit(context, latency, lateral) * e_t|`

Primary residual statistic: finite-conformal q90 absolute residual.

Secondary descriptive statistic: RMSE of signed one-step prediction residual.

No residual quantile is fitted on development.

## Fit eligibility gates

Fit evidence is allowed to produce a frozen candidate only if all of the following preregistered conditions hold.

### F17.1 construction integrity

Both contexts must have:

- exact paired row/truth/availability integrity;
- exact Phase 12 width identity;
- at least 500 matched temporal transitions.

### F17.2 finite contractive coefficient candidate

Every stored coefficient must be finite and satisfy `|a| < 0.98` without clipping.

### F17.3 simple-context large latency shift

For lateral coefficients in Context S:

- `a_latency - a_control >= 0.15`;
- `|a_latency - a_phase14| >= 0.15`.

### F17.4 hard-context Phase-14 proximity

For lateral latency coefficient in Context H:

- `|a_latency - a_phase14| <= 0.10`.

### F17.5 mismatch heterogeneity

The simple-context frozen-Phase14 mismatch magnitude must exceed the hard-context mismatch magnitude by at least `0.10`:

`|a_S_latency - a_phase14| - |a_H_latency - a_phase14| >= 0.10`.

If any fit gate fails, Phase 17 closes at fit and development seed `1717171` remains unexposed.

## Development gates

Development may be exposed only after the exact fit candidate is frozen.

### M17.1 lineage and matched-construction integrity

- exact frozen Phase 12 candidate;
- exact frozen Phase 14 bridge candidate;
- exact frozen Phase 17 fit candidate;
- exact paired row/truth/availability integrity;
- exact Phase 12 width identity;
- at least 500 matched temporal transitions in each context.

### M17.2 coefficient transfer

For each context and cohort, the fresh development diagnostic lateral coefficient must remain within `0.10` absolute of its frozen fit coefficient.

### M17.3 simple-context mismatch replication

On development diagnostics:

- `a_S_latency - a_S_control >= 0.15`;
- `|a_S_latency - a_phase14| >= 0.15`.

### M17.4 hard-context proximity replication

On development diagnostics:

- `|a_H_latency - a_phase14| <= 0.10`.

### M17.5 context heterogeneity replication

On development diagnostics:

`|a_S_latency - a_phase14| - |a_H_latency - a_phase14| >= 0.10`.

### M17.6 simple-context out-of-sample mismatch penalty

On Context S latency transitions, using the frozen Phase 17 latency coefficient must reduce the q90 absolute residual by at least 10% relative to the frozen Phase 14 coefficient:

`q90(residual_latency_fit) / q90(residual_phase14) <= 0.90`.

The latency-fit coefficient must also outperform the frozen Phase 17 control coefficient on Context S:

`q90(residual_latency_fit) / q90(residual_control_fit) <= 0.95`.

### M17.7 hard-context limited coefficient advantage

On Context H latency transitions, the frozen Phase 17 latency-coefficient q90 residual must remain within ±10% of the frozen Phase 14 q90 residual:

`0.90 <= q90(residual_latency_fit) / q90(residual_phase14) <= 1.10`.

This gate tests the preregistered hypothesis that the large mismatch mechanism is context-conditional rather than universal.

### M17.8 simple mismatch advantage exceeds hard advantage

Define relative q90 improvement:

`I = 1 - q90(residual_latency_fit) / q90(residual_phase14)`.

Require:

`I_simple - I_hard >= 0.08`.

### M17.9 latency level-error degradation remains present

The mechanism result is not allowed to erase the already-established static degradation. Require:

Context S lateral:
- p95 error inflation `>= 1.10`;
- 95% coverage delta `<= -0.01`.

Context H lateral:
- p95 error inflation `>= 1.10`;
- 95% coverage delta `<= -0.05`.

### M17.10 zero adaptation and claim boundary

Must remain true:

- no Phase 12 interval change;
- no Phase 14 candidate change;
- no controller change;
- no latency-magnitude change;
- no context change;
- no post-hoc threshold change;
- `simulation_only = true`;
- `safety_acceptance = false`;
- `controller_tuning_allowed = false`.

Phase 17 development PASS requires **all M17.1–M17.10**.

## Interpretation boundary

A PASS would support only this narrow simulation statement:

> In the preregistered matched synthetic study, pure two-frame latency produced a context-dependent change in the effective one-step lateral error coefficient. A coefficient identified on separate latency data reduced out-of-sample residuals materially on the simple context but not materially on the hard context, while static level-error degradation remained.

A PASS would **not** establish that real latency has the same mechanism, would not prove invariant-set safety, and would not justify changing the frozen Phase 12 uncertainty model or a controller.

A FAIL is a valid result. No coefficient, threshold, context, seed, family range, or intervention may be changed to force Phase 17 to pass.