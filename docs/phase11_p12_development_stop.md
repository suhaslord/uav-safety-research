# Phase 11 P12 development stop — three-group direct conformal

## Status

**FROZEN SEEN-TRANSFER FAILURE — PROTECTED VALIDATION NOT EXPOSED**

P12 preregistration: `docs/phase11_p12_three_group_direct_conformal_preregistration.md`

Simulation benchmark:

- run: `31974897515`
- scientific/workflow head: `72fba1f0752d22296da3327aa808e5f2c62337d3`
- artifact ID: `9270787484`
- artifact digest: `sha256:a6dd91f43103e3964377d43131f8ba87bc49b268a6d380c7dc7a0fe6f1301b5e`
- frozen candidate SHA-256: `39b8fdf2b311a59f7f94bfce74234bea5c6bd32475f7e831c06194cc5dc59ae0`
- transfer frames SHA-256: `0149c09db1664d41a1ad600827246f180b4dfc3dcad48645ee406e3aa5741957`
- transfer result SHA-256: `f8196a9c9c0565bc96becb3815f7841f43c7bf3c3173886f08321b60d61c3b0a`

The candidate was frozen and hashed before the seen-transfer split was generated.

## Exposure ledger

Permanently seen:

- fit seed `539539`;
- grouped-calibration seed `550550`;
- seen-transfer seed `561561`.

Protected-validation seed `572572` was **not generated** and is retired rather than recycled.

## Candidate sample-size checkpoint

The three-group redesign solved the earlier sparse-bucket problem with substantial margin:

- grouped calibration `base_output`: `22,386` rows (`>=1,500` required);
- `continuity_h3`: `442` (`>=150`);
- `continuity_h47`: `160` (`>=100`).

Seen transfer also satisfied all sample minimums:

- `base_output`: `8,339` (`>=1,000`);
- `continuity_h3`: `531` (`>=100`);
- `continuity_h47`: `542` (`>=60`).

P12 therefore failed for calibration transfer, not statistical power.

## Preregistered seen-transfer result

| Gate | Frozen result | Verdict |
|---|---:|---|
| H1 availability | `98.04%` | PASS |
| H2 lateral 95% coverage | `83.82%` | **FAIL** |
| H2 altitude 95% coverage | `84.01%` | **FAIL** |
| H3 calibration MACE | `0.20439` | **FAIL** |
| H4 lateral median width / p95 error | `0.385x` | PASS |
| H4 lateral p95 width / p95 error | `1.297x` | PASS |
| H4 altitude median ratio | `0.450x` | PASS |
| H4 altitude p95 ratio | `0.928x` | PASS |
| H5 continuity lateral 95% coverage | `87.05%` | **FAIL** |
| H5 continuity altitude 95% coverage | `85.09%` | **FAIL** |
| H5 continuity lateral p95 width/error | `0.801x` | PASS component |
| H5 continuity altitude p95 width/error | `0.827x` | PASS component |
| H6 base lateral 95% coverage | `83.40%` | **FAIL** |
| H6 base altitude 95% coverage | `83.87%` | **FAIL** |
| H7 shift AUROC | `0.99557` | diagnostic PASS |

Overall: **FAILED**. Protected validation was therefore not eligible for exposure.

## Interpretation

P12 separates two problems that earlier revisions had conflated:

1. **Power is solved.** The three-group partition has ample calibration and transfer support.
2. **Efficiency is not the problem.** P12 intervals are compact relative to observed p95 errors and easily pass H4.
3. **Coverage transfer is the problem.** Calibration radii learned from the grouped-calibration compositions are systematically too small on the harder seen-transfer compositions.
4. The failure affects both `base_output` and continuity groups, so it is not primarily a continuity-motion issue.
5. Strong AUROC (`0.9956`) confirms a major distribution shift is visible, but one-stage grouped conformal does not compensate for it.

Therefore P12 should not be retuned on seed `561561` and should not expose protected seed `572572`.

## Next revision

P13 should preserve:

- the P9 soft bounded-influence point estimator unchanged;
- the P12 three fixed groups unchanged;
- direct finite-sample absolute-error conformal as the base interval;

and add exactly one new reliability step on entirely fresh evidence:

**a disjoint compositional transfer-calibration split that conformalizes the ratio of true absolute error to the already-frozen base grouped radius.**

The final group/axis/target radius should be:

`R_final(group,axis,q) = R_base(group,axis,q) * T_transfer(group,axis,q)`

where `T_transfer` is frozen from a new transfer-calibration split before any later challenge/validation exposure.

P13 should then use a separate fresh seen-challenge split to decide whether protected validation may be exposed. This keeps shift adaptation separate from evaluation and avoids reintroducing P2/P8's learned-scale stack.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
