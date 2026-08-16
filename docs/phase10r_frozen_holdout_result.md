# Phase 10R frozen holdout result

## Verdict

**Mixed / failed overall under the preregistered all-gates rule.**

The protected `phase10r_frozen_holdout` was exposed exactly once after the user approved the frozen checkpoint. The candidate implementation, partial-view threshold, and uncertainty calibration were fixed before holdout generation. No raw frame was manually inspected before automated evaluation and artifact preservation.

This result is frozen. It is not being retuned away.

## Provenance

- frozen candidate SHA: `e1d566f8baa47bf10f9bdf39dd5988724208be80`
- frozen `MIN_VISIBLE`: `0.66`
- frozen calibration SHA-256: `3ffdf1e37c94361ac01d8175f902a0ae4fb8d831274bb7850c171e92d79c527b`
- holdout generation/evaluation commit: `bdfcfe7bc263b3364c194b0ec8450c204be035bf`
- holdout seed: `1618033`
- workflow run: `31925087516`
- artifact ID: `9257643369`
- artifact ZIP SHA-256: `b7b4ac34f8c3fc86826fe1f017cabfbc8f1a413a3851021fa810c4d0bac860d1`
- evidence role: `phase10r_frozen_holdout`

## Holdout design

- 12 new geometry trajectory IDs;
- 3 appearance conditions: nominal, dim/contrast shift, blur+noise;
- 36 sequence IDs;
- 48 frames per sequence;
- **1,440 truth-visible frames**;
- truth-not-visible prefixes/suffixes retained for false-positive measurement;
- raw frame bytes and hashes preserved in the Actions artifact.

## Frozen gate table

| Gate | Threshold | Frozen result | Status |
|---|---:|---:|:---:|
| Clean lateral MAE | ≤ 1.10× Phase 9 | **0.704×** | PASS |
| Clean altitude MAE | ≤ 1.10× Phase 9 | **0.417×** | PASS |
| Ambiguous lateral MAE improvement | ≥ 30% | **79.2%** | PASS |
| Ambiguous altitude MAE improvement | ≥ 30% | **73.7%** | PASS |
| Ambiguous lateral p95 improvement | ≥ 25% | **−1.1%** | FAIL |
| Ambiguous altitude p95 improvement | ≥ 25% | **7.3%** | FAIL |
| Truth-visible miss rate | ≤ 10% | **20.0%** | FAIL |
| False-positive rate | ≤ 1% | **0.0%** | PASS |
| Lateral 95% uncertainty coverage | 90–98% | **84.3%** | FAIL |
| Altitude 95% uncertainty coverage | 90–98% | **79.7%** | FAIL |

All applicable gates did **not** pass.

## What improved

Average ambiguous/partial-view geometry improved substantially:

- lateral MAE: `0.05161 m → 0.01072 m` (**79.2% improvement**);
- altitude MAE: `0.16799 m → 0.04410 m` (**73.7% improvement**).

Clean observations also remained strong rather than paying a regression cost:

- clean lateral MAE ratio: `0.704×` Phase 9;
- clean altitude MAE ratio: `0.417×` Phase 9.

The candidate produced **0 false positives** on truth-not-visible frames.

## What failed

The final shift exposed three important weaknesses that the development/validation result did not fully reveal.

### 1. Availability did not generalize enough

The candidate miss rate was **20.0%**, above the preregistered `≤10%` requirement. Phase 9's paired baseline miss rate was `23.75%`, so Phase 10R improved availability, but not enough for the frozen success gate.

### 2. Tail geometry did not improve

The mean/MAE story looked strong, but the p95 story did not:

- lateral p95 changed from `0.03342 m` to `0.03378 m` (**−1.1% improvement / slight regression**);
- altitude p95 changed from `0.13547 m` to `0.12564 m` (**7.3% improvement**).

This means the candidate reduced typical ambiguous-view errors while leaving a hard tail of difficult cases largely unresolved.

### 3. Development-frozen uncertainty became under-covering

The development calibration no longer achieved its intended 95% coverage under the harder holdout shift:

- lateral: **84.3%**;
- altitude: **79.7%**.

This is direct evidence of calibration degradation under distribution shift. Phase 10 and Phase 10R validation showed much better uncertainty honesty inside their earlier domains; the final holdout demonstrates that those calibration guarantees did not transfer automatically.

## Scientific interpretation

The final Phase 10R result is more informative than a simple success/failure label:

1. causal partial-view recovery can dramatically reduce **average** ambiguous geometry error;
2. that improvement can coexist with an unresolved **tail-risk** problem;
3. a calibration model that looks strong on development/validation can become materially overconfident after appearance + geometry shift;
4. detector availability remains an independent bottleneck even when the accepted estimates themselves become better.

That combination motivates the next research phase: **domain-shift-aware perception reliability**, with explicit focus on coverage under shift, tail failures, and principled abstention rather than another round of post-hoc Phase 10R threshold tuning.

## Integrity statement

- no post-holdout Phase 10R retuning is included in this result;
- historical Phase 10 evidence was not used for Phase 10R model selection;
- validation seed `271828` was not used for post-validation retuning;
- the result remains simulation-only;
- `safety_acceptance = false`;
- `controller_tuning_allowed = false`;
- no physical-flight or certification claim is made.
