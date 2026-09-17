# Phase 13 development result — Thirteen-Domain Gauntlet

## Verdict

**PHASE13 ZERO-SHOT DEVELOPMENT: FAIL — LINEAGE CLOSED AT DEVELOPMENT.**

Transfer seed `957957` is **not authorized for exposure**.

The failure is scientifically meaningful because the preregistered paired control itself failed predecessor primary gates. Under the Phase 13 interpretation ladder, that means the shifted result cannot be cleanly attributed to the added stress layer.

The exact frozen Phase 12 candidate was not changed, recalibrated, widened, or retuned.

## Canonical evidence identity

- workflow run: `34008402512`
- canonical artifact: `9981691482`
- artifact digest: `sha256:402432a78c91a77d0a32fb6289310cf38d5659a90874018b3e000813198286a4`
- scientific Git SHA: `75522d4b7791342b56939680f254dd61858254f8`
- development seed: `948948`
- development families: `1201–1224`
- frozen Phase 12 scientific SHA: `8d0617a83d699cd14eae6194ce3a86a5c034dfbc`
- frozen Phase 12 candidate SHA-256: `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`
- result JSON SHA-256: `2e851c4cef6c965dfce5c629f9ef0ce7d3d28bae11d80256a3f0d60ec9eab26b`
- paired-control frames SHA-256: `e60ab9133966b221c67d09361c2e6fbba4a4c736ad990354da72fa3d2e4c2475`
- shifted frames SHA-256: `5125e5354458dbd7d87549d685e49804f9b656ca51a98b74de3d531d2f5184c3`
- result manifest SHA-256: `c4e5c78738e4223d263742dba85de7e16112857abe4c4aeab5eb8327e3441276`

## Execution audit before the canonical result

Two pre-result technical attempts are retained as invalid execution history rather than erased.

### Attempt 1 — retired seed `946946`

- run: `34008119532`
- failure: integer overflow in the preregistered `reacquisition_shock` sign-parity calculation
- audit artifact: `9981606849`
- artifact digest: `sha256:d21c386954f10667770c9c8c8a5a3881ffdd18c78980667e752f432eae9ce79f`
- persisted scientific outputs: none
- status: `INVALID_TECHNICAL_ATTEMPT / NEVER_A_PHASE13_RESULT`

The parity-only remediation is recorded in `docs/phase13_execution_amendment_01.md`.

### Attempt 2 — retired seed `947947`

- run: `34008280645`
- failure: missing SciPy dependency while Pandas attempted the preregistered Spearman calculation
- audit artifact: `9981658507`
- artifact digest: `sha256:a3f00cc3fc2ab9cfa389f9df336e870709539dbf8081d6b95c12c1f845cf174b`
- persisted scientific outputs: none
- status: `INVALID_TECHNICAL_ATTEMPT / NEVER_A_PHASE13_RESULT`

The dependency remediation is recorded in `docs/phase13_execution_amendment_02.md`.

Neither technical seed was reused. The canonical result used fresh replacement seed `948948`.

## Phase 13 gate summary

| Gate | Result | Key value |
|---|---:|---|
| G13.1 paired-control integrity | **FAIL** | predecessor primary gates failed on no-shift paired control |
| G13.2 zero-shot shifted primary gates | **FAIL** | predecessor primary gates failed on combined shifted aggregate |
| G13.3 thirteen-domain honesty | **FAIL** | `12 / 13` domains met both 88% coverage floors |
| G13.4 no catastrophic domain | **PASS** | worst lateral `0.842531`; worst altitude `0.916851` |
| G13.5 reliability mechanism survives | **PASS** | continuity innovation/error Spearman `0.393945` >= `0.20` |
| G13.6 zero adaptation | **PASS** | no candidate change, recalibration, or post-hoc threshold change |

Overall:

`phase13_pass = false`

## G13.1 — paired-control integrity failure

The no-shift paired control retained high raw coverage and availability but failed calibration/efficiency gates.

### Paired-control headline metrics

- useful availability: `0.9916132479`
- lateral 95% coverage: `0.9762969348`
- altitude 95% coverage: `0.9775359586`
- H3 MACE: `0.0759759737` — **FAIL**
- H4 lateral median width/error ratio: `0.8883820476`
- H4 lateral p95 width/error ratio: `2.8356409274` — **FAIL**
- H4 altitude median width/error ratio: `1.0548688221`
- H4 altitude p95 width/error ratio: `2.4373149865` — **FAIL**

Additional predecessor gate results:

- H1 useful availability: PASS
- H2 overall 95% coverage: PASS
- H3 calibration curve: **FAIL**
- H4 overall interval efficiency: **FAIL**
- H5 primary-continuity honesty: **FAIL**
- H6 base-output honesty: **FAIL**
- H7 shift discrimination: diagnostic PASS, AUROC `0.9766960470`
- H8 high-severity honesty: PASS
- H9 rescue-output honesty: PASS
- H10 rescue accuracy floor: PASS
- H11 rescue effectiveness: PASS
- group minimums: PASS

H5 paired-control details:

- rows: `2612`
- lateral coverage: `0.9950229709`
- lateral p95 width/error ratio: `2.1861409441`
- altitude coverage: `0.9954058193`
- altitude p95 width/error ratio: `1.9494018000`

H6 paired-control details:

- rows: `13263`
- lateral coverage: `0.9785116489`
- lateral p95 width/error ratio: `2.6541742906`
- altitude coverage: `0.9789640353`
- altitude p95 width/error ratio: `2.4576780962`

### Interpretation of G13.1

This is the first Phase 13 boundary.

The frozen Phase 12 model is not simply failing because the synthetic stress overlay made errors larger. Even before the overlay, the deliberately different Phase 13 base-domain mixture changes the calibration/efficiency behavior enough that the predecessor gates do not reproduce.

Therefore the current Phase 13 shifted aggregate cannot be labeled a clean external-domain-shift failure caused by the overlays alone.

The correct conclusion is narrower:

> The frozen Phase 12 candidate did not preserve its full predecessor calibration/efficiency gate set on the preregistered Phase 13 paired-control distribution.

That is itself an external-validity limitation.

## G13.2 — shifted aggregate

The combined 13-domain shifted distribution also failed predecessor primary gates.

### Shifted headline metrics

- useful availability: `0.9916132479`
- lateral 95% coverage: `0.9628831547`
- altitude 95% coverage: `0.9750040403`
- H3 MACE: `0.0551926951` — PASS
- H4 lateral median width/error ratio: `1.0151741321`
- H4 lateral p95 width/error ratio: `2.8874519514` — **FAIL**
- H4 altitude median width/error ratio: `1.2563364797`
- H4 altitude p95 width/error ratio: `2.3809326927` — **FAIL**

Required predecessor gates:

- H1: PASS
- H2: PASS
- H3: PASS
- H4: **FAIL**
- H5: **FAIL**
- H6: **FAIL**
- H8: PASS
- H9: **FAIL**
- H10: PASS
- H11: PASS
- group minimums: PASS

### Shifted continuity/base behavior

H5 primary continuity:

- rows: `2612`
- lateral coverage: `0.9931087289`
- lateral p95 width/error ratio: `2.0778332771`
- altitude coverage: `0.9911944870`
- altitude p95 width/error ratio: `1.9036013594`

H6 base output:

- rows: `13263`
- lateral coverage: `0.9795672171`
- lateral p95 width/error ratio: `2.2109299600`
- altitude coverage: `0.9825077283`
- altitude p95 width/error ratio: `2.3002700466`

### Shifted rescue behavior

H9 rescue-output honesty failed:

- rows: `2688`
- lateral 95% coverage: `0.8511904762`
- lateral p95 width/error ratio: `0.6746778770`
- altitude 95% coverage: `0.9222470238`
- altitude p95 width/error ratio: `0.8750971601`

H10 rescue accuracy still passed:

- lateral MAE: `0.1176398577 m`
- lateral p95 error: `0.3079759766 m`
- altitude MAE: `0.1864420233 m`
- altitude p95 error: `0.4622469579 m`

H11 rescue effectiveness still passed:

- primary unavailable rows: `2845`
- rescued rows: `2688`
- recovered fraction: `0.9448154657`

The important distinction is that rescue remained effective and reasonably accurate as a point estimate, but its frozen uncertainty envelope was no longer honest enough under the combined Phase 13 shifts.

## G13.3 — thirteen-domain honesty

Twelve of thirteen individual domains met the preregistered requirement of at least 88% 95%-interval coverage on both axes.

The sole failure was:

### `latency_wind_calibration_compound`

- lateral 95% coverage: `0.8425312730` — **FAIL** vs `0.88`
- altitude 95% coverage: `0.9168506255` — PASS
- available fraction: `0.94375`
- lateral p95 error: `0.333052 m`
- altitude p95 error: `0.522706 m`
- lateral p95 half-width / p95 error: `2.208664`
- altitude p95 half-width / p95 error: `3.245868`

All other 12 domains cleared both per-domain 88% floors.

## G13.4 — no catastrophic domain

PASS.

Worst individual-domain coverage:

- lateral: `0.8425312730`
- altitude: `0.9168506255`

Both remained above the locked catastrophic floor of `0.80`.

So Phase 13 found a material local honesty miss, not a complete collapse.

## G13.5 — reliability mechanism

PASS.

Continuity normalized anchor innovation remained positively associated with lateral absolute error under the shifted aggregate:

- Spearman: `0.3939451210`
- required minimum: `0.20`

This is important because the inference-visible mechanism that motivated the Phase 12 v3 architecture still carries useful ordering information under the new stress family, even though the complete frozen gate set does not transfer.

## Per-domain shifted results

| Domain | Category | Lateral 95% cov | Altitude 95% cov | Result |
|---|---|---:|---:|---:|
| camera_scale_miscalibration | sensing | 0.974948 | 0.981907 | PASS |
| lateral_sensor_bias | sensing | 0.975610 | 0.981882 | PASS |
| correlated_measurement_noise | sensing | 0.989547 | 0.979791 | PASS |
| heavy_tail_measurement_noise | sensing | 0.981158 | 0.986741 | PASS |
| fixed_latency_2f | timing | 0.962963 | 0.993012 | PASS |
| jittered_latency_0_4f | timing | 0.959610 | 0.985376 | PASS |
| burst_staleness_5f | timing | 0.962396 | 0.975627 | PASS |
| lateral_wind_drift | dynamics | 0.979109 | 0.983983 | PASS |
| vertical_gust | dynamics | 0.983927 | 0.965758 | PASS |
| dynamics_gain_mismatch | dynamics | 0.934965 | 0.958741 | PASS |
| oscillatory_drift | dynamics | 0.980488 | 0.982578 | PASS |
| reacquisition_shock | compound | 0.983905 | 0.979706 | PASS |
| latency_wind_calibration_compound | compound | **0.842531** | 0.916851 | **FAIL** |

## What Phase 13 development established

It did **not** establish broad zero-shot external validity.

It did establish four useful findings:

1. **Distribution composition matters before added stress.** The no-shift paired-control mixture itself breaks predecessor calibration/efficiency gates despite high nominal 95% coverage.
2. **The innovation signal still generalizes directionally.** Its continuity error correlation remains meaningful at `0.393945`.
3. **Most individual stress domains remain coverage-honest at the preregistered 88% floor.** Twelve of thirteen passed.
4. **The compound latency + wind + calibration shift is a concrete boundary.** It is the only individual-domain honesty miss and drives lateral coverage down to `84.25%` without reaching catastrophic collapse.

A fifth secondary finding is that the rescue point estimate remains effective/accurate while its interval calibration degrades under the aggregate stress distribution.

## Decision

The preregistered development decision rule is enforced exactly:

- `phase13_pass = false`
- transfer exposure: **PROHIBITED**
- protected exposure: **PROHIBITED**
- final exposure: **PROHIBITED**
- Phase 12 candidate modification inside this lineage: **PROHIBITED**

No Phase 13 downstream seed has been exposed.

Any follow-up architecture must be a separately preregistered Phase 13B lineage with a new scientific identity. It may use this permanently seen development result diagnostically, but it may not rewrite or relabel the zero-shot Phase 13 result.

## Claim boundary

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`

Supported claim:

> The frozen Phase 12 Iteration 3 model did not pass the preregistered Phase 13 zero-shot development gauntlet. The paired no-shift Phase 13 control itself failed predecessor calibration/efficiency gates, 12 of 13 shifted domains met the 88% per-domain coverage floor, the compound latency/wind/calibration domain missed that floor laterally, and the innovation/error reliability relationship remained positive.

This is not physical-flight, certification, production-readiness, or operational-safety evidence.
