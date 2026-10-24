# Phase 19 final result — Distribution-Wide Residual Advantage

## Final verdict

**PASS — Phase 19 passed development, transfer, protected validation, and final holdout with all 10 preregistered gates passing at every stage.**

This closes the Phase 19 scientific lineage successfully.

Phase 18 remains an immutable protected-validation FAIL. Phase 19 does not repair or replace Phase 18's failed q90 claim. Instead, it confirms a narrower distribution-wide residual effect on fresh evidence using RMSE and MAE as preregistered gate metrics while q90 remained descriptive only.

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`

No physical-flight, real-sensor, certification, controller-improvement, production-readiness, or operational-safety claim is made.

## Frozen scientific objects

- Phase 12 candidate SHA-256: `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`
- Phase 14 bridge SHA-256: `0443d4e45a1966c77544c5c9965de8caec6e622c79ef8c2ce47aee82a3c95981`
- Phase 17 fit candidate SHA-256: `2ca52a418f5616e0e83ef84d0c9238ee429260cd4de7a553356b0c1bba44d8e0`
- failed Phase 18 protected result SHA-256: `ad96ca1a5119fcd594a84fd72a04f8efcc377ba788383d90dda9ef7eecad4431`

Every Phase 19 stage explicitly reverified the failed Phase 18 result before evidence exposure.

## Sequential evidence record

| Role | Seed | Families | Run | Artifact | Result SHA-256 | Verdict |
|---|---:|---|---:|---:|---|---|
| development | `1919191` | `2025–2048` | `34012185448` | `9982804293` | `515e431aa0e91faa2bf204277fdcb9ec3defbdc3e0242e7f5c8cd4a53b81ddd6` | **PASS** |
| transfer | `1919192` | `2049–2072` | `34012247907` | `9982824343` | `0b6f03e001ea2f23c39017f16dd3341c913f4365c8c20126544d963b58e97529` | **PASS** |
| protected | `1919193` | `2073–2096` | `34012321140` | `9982850544` | `196234b9b39b127895db36730e9e00507cfb977d337102a9f969bdeb409bd87c` | **PASS** |
| final | `1919194` | `2097–2120` | `34012403543` | `9982867507` | `8c23b9b9c8c9fb2f9146bf739e52074f8709d2fe9a81c794e64fb43f360acebf` | **PASS** |

Artifact digests:

- development: `sha256:aeb73f2064bce2cf1acffad0e505f7cd4538f64128dac809bdc295c9c77535ad`
- transfer: `sha256:5891493936d06b269828c3192db7fb74180f4c105487ecbdf4cc7856dc0fd341`
- protected: `sha256:b0220f9e005548c463c7ee15791d2e737869b2e53cb0c6c0771c9d550c4f7de3`
- final: `sha256:25d40c5cfc5fdbe5d5cc81745011f4c3c1785a6a78db8ab3eaa43100ab11e8e1`

Scientific heads at evidence exposure:

- development: `4fec27c6d789189bb7bb352bcf47089b4df2155c`
- transfer: `9e66e377c605df938d55665966d5e4dac5561b0e`
- protected: `a7e5c13328cba4ab9e3c26c5f7a6f7a8bc81f95a`
- final: `29b31cb3e006f3f2bfad97d8a1daa217916021e9`

Only result notes and the next sequential workflow were permitted between evidence roles; the scientific implementation and thresholds remained frozen.

## Gate record

At each of the four evidence roles, all of the following passed:

- D19.1 lineage integrity
- D19.2 matched construction and exact Phase 12 width identity
- D19.3 simple-context RMSE advantage
- D19.4 hard-context RMSE neutrality
- D19.5 RMSE context-advantage gap
- D19.6 simple-context MAE advantage
- D19.7 hard-context MAE neutrality
- D19.8 MAE context-advantage gap
- D19.9 static latency degradation remains present
- D19.10 zero adaptation and claim boundary

## Primary result across all evidence roles

### Simple context — frozen latency coefficient advantage

| Role | RMSE ratio vs Phase14 | RMSE improvement | MAE ratio vs Phase14 | MAE improvement |
|---|---:|---:|---:|---:|
| development | `0.8949356280` | **`10.51%`** | `0.8561580872` | **`14.38%`** |
| transfer | `0.9186086367` | **`8.14%`** | `0.8639149669` | **`13.61%`** |
| protected | `0.9287583371` | **`7.12%`** | `0.8667395284` | **`13.33%`** |
| final | `0.9105932608` | **`8.94%`** | `0.8535517802` | **`14.64%`** |

The frozen simple-context latency coefficient therefore produced a substantial distribution-wide residual reduction on all four fresh partitions.

### Hard context — frozen latency coefficient remains near neutral

| Role | RMSE ratio vs Phase14 | RMSE improvement | MAE ratio vs Phase14 | MAE improvement |
|---|---:|---:|---:|---:|
| development | `0.9958077725` | `0.42%` | `0.9981259105` | `0.19%` |
| transfer | `0.9961379371` | `0.39%` | `0.9982136103` | `0.18%` |
| protected | `0.9939459862` | `0.61%` | `0.9987093625` | `0.13%` |
| final | `0.9965845811` | `0.34%` | `0.9997774466` | `0.02%` |

The analogous hard-context coefficient provided essentially no distribution-wide advantage relative to Phase14.

## Final holdout detail

### Simple context

Matched transitions: `1,347`

- RMSE latency-fit / Phase14: `0.9105932608`
- RMSE improvement: **`8.9406739240%`**
- MAE latency-fit / Phase14: `0.8535517802`
- MAE improvement: **`14.6448219817%`**
- q90 ratio, descriptive only: `0.8922584085`
- coverage delta: `-0.0314026518` (`-3.14 pp`)
- p95 level-error inflation: `1.4564356646x`
- median level-error inflation: `3.5561312770x`

### Hard context

Matched transitions: `1,223`

- RMSE latency-fit / Phase14: `0.9965845811`
- RMSE improvement: `0.3415418917%`
- MAE latency-fit / Phase14: `0.9997774466`
- MAE improvement: `0.0222553365%`
- q90 ratio, descriptive only: `0.9789618783`
- coverage delta: `-0.0861070912` (`-8.61 pp`)
- p95 level-error inflation: `1.3583242296x`
- median level-error inflation: `1.3649809712x`

Final context gaps:

- RMSE improvement gap: **`0.0859913203`** >= locked `0.05`
- MAE improvement gap: **`0.1462256665`** >= locked `0.05`

## Static degradation remains separate from residual predictability

Across every Phase 19 role, pure two-frame latency continued to worsen lateral level-error behavior in both contexts while Phase 12 interval widths remained exactly unchanged.

The result therefore does not say latency is beneficial. It supports a narrower distinction:

> A context-specific coefficient can better predict the local one-step evolution of the stale-estimate error in the simple synthetic context even while the stale estimate itself is less accurate in absolute level error.

On the hard synthetic context, the same coefficient substitution provides almost no distribution-wide predictive advantage.

## Relationship to Phase 18

Phase 18 remains FAIL because its stronger q90 thresholds did not survive protected validation.

Phase 19 deliberately did not retry q90 under weakened gates. q90 was descriptive only throughout Phase 19.

The successful Phase 19 claim is therefore different:

> The simple-versus-hard **distribution-wide residual advantage** of the exact frozen coefficient object replicated across development, transfer, protected validation, and final holdout on RMSE and MAE without refitting.

## Evidence boundary

All preregistered Phase 19 evidence roles are now permanently exposed exactly once:

- `1919191`
- `1919192`
- `1919193`
- `1919194`

No additional Phase 19 evidence role exists. No rerun, coefficient refit, threshold change, context change, or intervention change is authorized within this closed lineage.

## Claim boundary

Supported claim only:

> In the preregistered simulation-only Phase 19 matched study, the exact frozen simple-context latency coefficient produced a repeatable distribution-wide one-step lateral residual reduction relative to the frozen Phase14 coefficient on RMSE and MAE across development, transfer, protected, and final evidence, while the analogous hard-context coefficient remained approximately neutral and static latency-induced level-error degradation persisted.

This does not establish physical latency causality, physical UAV safety, real-sensor behavior, full-simulator invariance, certification relevance, controller improvement, production readiness, or operational reliability.