# Phase 19 transfer result — Distribution-Wide Residual Advantage

## Verdict

**PASS — all 10 preregistered transfer gates passed.**

- run `34012247907`
- artifact `9982824343`
- artifact digest `sha256:5891493936d06b269828c3192db7fb74180f4c105487ecbdf4cc7856dc0fd341`
- scientific SHA `9e66e377c605df938d55665966d5e4dac5561b0e`
- seed `1919192`
- families `2049–2072`
- result SHA-256 `0b6f03e001ea2f23c39017f16dd3341c913f4365c8c20126544d963b58e97529`

`simulation_only = true`
`safety_acceptance = false`
`controller_tuning_allowed = false`

## Simple context

- matched transitions `1,345`
- RMSE ratio `0.9186086367` → improvement **`8.1391363326%`**
- MAE ratio `0.8639149669` → improvement **`13.6085033057%`**
- q90 ratio descriptive only `0.8529166777`
- coverage delta `-3.89 pp`
- p95 level-error inflation `1.5486072213x`

## Hard context

- matched transitions `1,183`
- RMSE ratio `0.9961379371` → improvement `0.3862062902%`
- MAE ratio `0.9982136103` → improvement `0.1786389661%`
- q90 ratio descriptive only `0.9841579623`
- coverage delta `-8.77 pp`
- p95 level-error inflation `1.2524596016x`

## Context gaps

- RMSE improvement gap `0.0775293004` >= `0.05`
- MAE improvement gap `0.1342986434` >= `0.05`

## Protected authorization

Protected seed `1919193`, families `2073–2096`, is the only next authorized evidence. Before exposure the exact transfer scientific SHA and result SHA above must be reverified. Final `1919194` remains unexposed.

Phase 18 remains recorded as a protected-validation FAIL. q90 remains descriptive only in Phase 19.

No physical latency causality, physical-flight safety, real-sensor equivalence, certification, controller improvement, production readiness, or operational-safety claim is made.