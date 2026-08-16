# Phase 11 P7 development stop — powered horizon-aware calibration

## Status

**INDEPENDENT DEVELOPMENT CHALLENGE FROZEN — PROTECTED VALIDATION NOT EXPOSED**

Candidate freeze:

- freeze run: `31971298967`
- freeze head: `3be4423afa24dfa85af9ed36e4064b007fcc5e13`
- candidate artifact ID: `9269862892`
- candidate artifact digest: `sha256:7a3e156da21deefd2374b8597e5ec9aa0550f151907692b60a3e6464ed57ff9a`
- artifact candidate JSON SHA-256: `9ed0a09bb32095dd7a1b03c97e10e16d70571ebd28c2922e99f2e633575fc1eb`
- horizon calibration counts: `2,785` direct/short and `84` long rows.

Independent development challenge:

- seed: `341341`
- run: `31971385499`
- workflow head: `62ab65c139116e51fa6f62a23d6a260989866867`
- artifact ID: `9269881816`
- artifact digest: `sha256:755b65da5dd179eda7e2a88c39af5f23dfc2a14d612e8fa92bcd8552f67c9ff4`
- `development_frames.csv` SHA-256: `96a3cb39935026afd6f2838798988a87eb21363c0ca1de9e4b485c2b6ef2b855`
- `development_result.json` SHA-256: `2bd8365b7853f1dc0e01c4d0d7994404c241d28beb777b77572b659eebf79164`

Development seed `341341` is permanently seen.

## Preregistered development gates

| Gate | Frozen result | Verdict |
|---|---:|---|
| D1 availability | `93.61%` | PASS |
| D2 lateral 95% coverage | `93.32%` | PASS |
| D2 altitude 95% coverage | `93.18%` | PASS |
| D3 calibration MACE | `0.01991` | PASS |
| D4 lateral median half-width / p95 error | `0.502x` | PASS |
| D4 altitude median ratio | `0.512x` | PASS |
| D4 lateral p95 half-width / p95 error | `1.565x` | PASS |
| D4 altitude p95 ratio | `1.623x` | PASS |
| D5 long-bridge count | `80` | sufficient |
| D5 long-bridge lateral 95% coverage | **`81.25%`** | **FAIL** |
| D5 long-bridge altitude 95% coverage | `95.00%` | PASS |
| D5 lateral p95 half-width / long p95 error | `0.673x` | PASS |
| D5 altitude ratio | `1.026x` | PASS |
| D6 direct/short lateral 95% coverage | `94.09%` | PASS |
| D6 direct/short altitude 95% coverage | `93.06%` | PASS |
| D7 shift AUROC | `0.9670` | PASS |

Overall P7 independent development result: **MIXED / FAILED** solely because long-bridge lateral coverage failed.

## Read-only horizon forensics

After development exposure, the long-bridge rows were inspected descriptively. This does not authorize retuning on seed `341341`.

Using the frozen P7 95% long-bridge half-width, empirical coverage by horizon was approximately:

| Bridge horizon | n | lateral 95% coverage | altitude 95% coverage |
|---|---:|---:|---:|
| `3` | `41` | `87.8%` | `97.6%` |
| `4` | `24` | `83.3%` | `95.8%` |
| `5` | `15` | `60.0%` | `86.7%` |

The P7 transfer-calibration panel itself contained:

- h=3: `58` available rows;
- h=4: `17` rows;
- h=5: `9` rows.

Thus the pooled `h=3..5` multiplier had adequate total long-group support but insufficient support to represent the strong horizon trend, especially h=4/h=5.

## Decision before protected validation

Protected seed `352352` is intentionally **not generated** and is retired rather than recycled.

The P7 preregistration required every independent development gate to pass before protected validation. D5 failed, so protected validation is not run.

No P7 bridge rule, velocity cap, scale model, conformal rule, horizon grouping, multiplier, gate, or seed was changed after development exposure.

## Next revision

P8 should keep the P5/P7 continuity estimator unchanged but calibrate uncertainty separately for exact long horizons `h=3`, `h=4`, and `h=5`, while retaining one direct/short group for `h=0..2`.

Because P7 had only 17 h=4 and 9 h=5 transfer rows, P8 should increase transfer-calibration trajectories rather than lower the minimum-support requirement after seeing those counts.

## Claim boundaries

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- no physical-flight validation claim
- no controller-performance claim
- no new raw-camera accuracy claim
