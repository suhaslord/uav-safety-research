# Phase 21 final report — Orthogonal Context Spectrum

## Final verdict

**PASS — development, transfer, protected validation, and final holdout each passed all 10 preregistered gates.**

Phase 21 is closed. No rerun, threshold change, coefficient refit, factor-set change, or evidence-role reuse is authorized.

## Sequential evidence

| Role | Seed | Families | Run | Artifact | Result SHA-256 | Verdict |
|---|---:|---|---:|---:|---|---|
| development | `2121211` | `2217–2240` | `34014610015` | `9983534655` | `1fe5765af341fc8af21d5e4b1a9a2a70b1fe17ccbac93b0c313489f68c2d0215` | **PASS** |
| transfer | `2121212` | `2241–2264` | `34014762359` | `9983568761` | `245dde7406c163abdf8a68a0b3f91ccf2f88c0000d8fd694518f835ee7d0cc55` | **PASS** |
| protected | `2121213` | `2265–2288` | `34014872701` | `9983605823` | `2bddc712ccba4f0a0e5f116aaed21874c367c4e452e7ac84eae91adcecf6c0df` | **PASS** |
| final | `2121214` | `2289–2312` | `34015012804` | `9983638653` | `bc85a746cf1b770fb4119feb3979789975ed5201065d94de47c6dcc3a051d9ee` | **PASS** |

Final artifact digest:

`sha256:0a300ec589467e945ded1ba0b4c76b682db508198c894a247cc0569fea36f3d8`

Final evidence-generation scientific SHA:

`fc135a8dced251d2f5c5e5bddab4ec2296654023`

## Frozen predecessor identities

- Phase 12 candidate: `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991`
- Phase 14 bridge: `0443d4e45a1966c77544c5c9965de8caec6e622c79ef8c2ce47aee82a3c95981`
- Phase 17 fit candidate: `2ca52a418f5616e0e83ef84d0c9238ee429260cd4de7a553356b0c1bba44d8e0`
- Phase 20 final result: `f2a0cf4e1cf0765c3194025eb29072f9663f27e3cdd13b0594cde4643f33934e`

The Phase 20 object preserves the Phase 19 final PASS and immutable Phase 18 protected-validation FAIL. q90 remains descriptive only.

## Cross-stage endpoint attenuation

| Role | RMSE simple→hard attenuation | MAE simple→hard attenuation |
|---|---:|---:|
| development | **0.1367509157** | **0.1720186313** |
| transfer | **0.1705755000** | **0.2077244793** |
| protected | **0.1513164288** | **0.2041668881** |
| final | **0.1260043843** | **0.1560528074** |

The frozen simple-context latency coefficient remained advantageous relative to the Phase 14 coefficient at the simple endpoint and disadvantageous at the full hard endpoint on all four Phase 21 roles.

## Cross-stage orthogonal structure

| Role | RMSE first-order share | MAE first-order share |
|---|---:|---:|
| development | **87.70%** | **81.58%** |
| transfer | **79.45%** | **77.99%** |
| protected | **84.08%** | **75.20%** |
| final | **88.44%** | **78.01%** |

Every exposed role exceeded the locked `>=70%` first-order variance-share gate on both statistics.

Every exposed role also had all five first-order Walsh coefficients negative on both RMSE and MAE, meaning each modifier's balanced marginal effect pointed toward attenuation under the frozen synthetic factorial design.

## Final holdout

### Endpoint surface

RMSE:

- simple advantage: `0.0701724881627529`
- hard advantage: `-0.05583189616092166`
- attenuation: `0.12600438432367456`

MAE:

- simple advantage: `0.11863993302652676`
- hard advantage: `-0.03741287436406937`
- attenuation: `0.15605280739059613`

### Final RMSE spectrum

- first-order variance share: `0.8844091524005574`
- interaction share: `0.1155908475994426`
- Parseval absolute error: `1.0842021724855044e-19`

First-order coefficients:

- `edge`: `-0.012988585336688733`
- `oblique`: `-0.011431087859501834`
- `dim`: `-0.012251633630019795`
- `blur_noise`: `-0.010864895202556245`
- `low_contrast`: `-0.01332799773685341`

Order variance shares:

- order 1: `0.8844091524005574`
- order 2: `0.031981158356270814`
- order 3: `0.017442097671177343`
- order 4: `0.06464208789514204`
- order 5: `0.0015255036768526183`

### Final MAE spectrum

- first-order variance share: `0.7800968043940445`
- interaction share: `0.2199031956059555`
- Parseval absolute error: `4.336808689942018e-19`

First-order coefficients:

- `edge`: `-0.01723419028625879`
- `oblique`: `-0.011516763763164586`
- `dim`: `-0.01602131515060707`
- `blur_noise`: `-0.01354365114864526`
- `low_contrast`: `-0.017225215102175603`

Order variance shares:

- order 1: `0.7800968043940445`
- order 2: `0.04556801151711541`
- order 3: `0.04054307076577445`
- order 4: `0.1319697307777117`
- order 5: `0.0018223825453542407`

## Static-error boundary

Latency is not beneficial in the absolute estimation sense.

At the final simple endpoint:

- matched transitions: `1337`
- lateral p95 level-error inflation: `1.3908039264682617x`
- Phase 12 lateral 95% coverage delta: `-0.032798325191905064` (−3.28 pp)

At the final full hard endpoint:

- matched transitions: `1190`
- lateral p95 level-error inflation: `1.2486973391649028x`
- Phase 12 lateral 95% coverage delta: `-0.07574654042243267` (−7.57 pp)

Phase 12 widths remain unchanged between each matched control and pure-latency copy.

## Supported conclusion

> Across fresh development, transfer, protected, and final complete matched synthetic factorial evidence, the context dependence of the frozen simple-context latency coefficient's distribution-wide one-step lateral residual advantage was predominantly first-order under an exact orthogonal five-factor decomposition. Every predefined modifier's balanced first-order effect pointed toward attenuation on both RMSE and MAE, while latency-induced absolute level-error degradation persisted.

The result describes structure inside the frozen synthetic generator. It does not establish physical modifier causality, physical latency causality, or physical UAV safety.

## Maintenance boundary

The Phase 21 branch inherits the separately reviewed non-scientific Phase 13C writable-array compatibility repair. That repair only adds explicit `.copy()` calls before the historical deterministic noise mutation and does not change scientific constants or evidence.

## Claim boundary

`simulation_only = true`
`safety_acceptance = false`
`controller_tuning_allowed = false`

No physical-flight safety, real-sensor equivalence, full-simulator invariance, certification relevance, controller improvement, production readiness, or operational-safety claim is made.
