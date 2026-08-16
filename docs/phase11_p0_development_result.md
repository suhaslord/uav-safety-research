# Phase 11 P0 development result — domain-shift-aware reliability

## Status

**FROZEN DEVELOPMENT RESULT — MIXED / FAILED OVERALL**

Evidence role: `phase11_p0_non_authoritative_synthetic_development`

Benchmark code commit: `c89942aeb535b21ba2a1edd9883b07b9650bbf21`

Challenge seed `33033` is now **permanently seen**. It may not be reused as hidden/frozen evidence after any Phase 11 method change.

## Scope

This is a controlled synthetic reliability-layer benchmark. It does **not** establish new raw-camera accuracy, external-simulator fidelity, controller performance, or physical-flight safety.

- `simulation_only = true`
- `safety_acceptance = false`
- `controller_tuning_allowed = false`

## Preregistered gate result

| Gate | Result | Verdict |
|---|---:|---|
| H1 context 95% lateral coverage | `53.55%` | FAIL |
| H1 context 95% altitude coverage | `52.67%` | FAIL |
| H2 lateral median-width ratio vs global | `0.9761x` | PASS |
| H2 altitude median-width ratio vs global | `0.9758x` | PASS |
| H3 selective lateral p95 improvement | `37.05%` | PASS component |
| H3 selective altitude p95 improvement | `39.34%` | PASS component |
| H3 usable availability | `27.50%` | FAIL |
| H4 trajectory-level shift AUROC | `0.9097` | PASS |

Overall preregistered result: **MIXED / FAILED**.

## Interpretation

The P0 benchmark exposes a useful failure mode rather than a win:

1. The fixed reliability score separates compositional shift from calibration trajectories well (`AUROC 0.910`).
2. Conditioning intervals by the preregistered risk strata remains sharp relative to global conformal (`~0.976x` median width), but coverage transfers extremely poorly under unseen compositions (`~53%`, far below the required 90–98%).
3. The frozen q90 risk abstention removes a meaningful part of the error tail (`37–39%` p95 improvement), but it is far too conservative on the challenge distribution: only `27.5%` usable availability remains, below the preregistered `70%` minimum.
4. Therefore the current Phase 11 P0 reliability rule can identify shift, but it cannot yet convert that signal into both honest intervals and useful selective perception.

No threshold, risk weight, stratum, conformal rule, or generator parameter was changed after challenge exposure.

## Reproducibility hashes

The deterministic benchmark emitted the following artifacts:

| Artifact | SHA-256 |
|---|---|
| `fit_frames.csv` | `04a704c44725872fdbdebe30072209c073b31a092762720fe122354fc0ef1e69` |
| `calibration_frames.csv` | `fc9710ff826abecc9d68992b0c33600f953ede8bad1b670ab0a57af71da9329f` |
| `challenge_frames.csv` | `a0a545dc393f605de342c7403b4436fceb1c6e6c31938588550bba4e4e9773b6` |
| `calibration.json` | `dc598ff0f36fe9f8495687d1ad65b2d3c66d216f2b39bc8109bbc9d7cfc6da91` |
| `benchmark_result.json` | `7fa0e8951db5e58687987610087ade888a63ad12ab7ca6231d4b4d2ce0372529` |
| `benchmark_summary.md` | `9984ddd04676fa83c679e6f2ad5fdd16a7fbedea5fb217bd4405e0839a962dd7` |

The frame CSVs are generated reproducibly by `scripts/run_phase11_domain_shift_benchmark.py` from the preregistered seeds and are not used as hidden evidence after this result.

## Next scientific boundary

Do **not** tune on challenge seed `33033`.

The next research milestone must create a **new preregistered development/challenge split** if the reliability method changes. A protected Phase 11 frozen holdout remains ungenerated and requires a separate explicit approval only after a candidate is frozen on new development evidence.
