# Phase 13C transfer confirmation — frozen development discovery

## Status

**FROZEN AFTER PHASE 13C DEVELOPMENT AND BEFORE ANY PHASE 13C TRANSFER EVIDENCE IS EXPOSED.**

This note records the exact development-stage mechanism discovery that transfer will attempt to confirm. It is not a tuning document.

## Development evidence identity

- development run: `34009627595`
- development artifact: `9982053254`
- development scientific Git SHA: `de181594cbf451f42424ef61f3139351ad0946cd`
- development seed: `1313135`
- families: `1393–1416`
- result JSON SHA-256: `8040a86b7c114a8b122d7e7c16012c5d7edd56bd32d63ad05adaef6a2f2c7264`

## Frozen development phenomenon

The full compound replicated the Phase 13B paired failure on fresh development evidence:

- control lateral 95% coverage: `0.9493487698986975`
- full-compound lateral 95% coverage: `0.8263386396526773`
- paired lateral delta: `-0.12301013024602026`
- full-compound lateral p95 error inflation: `1.3835051911454124x`

C13.3 passed because the paired loss was at least 8 percentage points while shifted lateral coverage remained above the catastrophic 0.80 floor.

## Frozen discovered attribution

### Largest singleton loss

**A — latency**

- singleton lateral coverage loss: `0.09044862518089725`
- latency-only lateral coverage: `0.8589001447178003`
- latency-only lateral p95 error inflation: `1.3163420732709517x`

### Largest leave-one-out recovery

**A — latency**

- leave-one-out lateral recovery: `0.09117221418234445`
- full-minus-latency lateral coverage: `0.9175108538350217`

### Development component values

Singleton losses:

- A latency: `0.09044862518089725`
- B bias pair: `0.01664254703328505`
- C lateral wind drift: `0.02243125904486254`
- D measurement-noise pair: `-0.0014471780028944004`
- E innovation response: `0.0`
- F severity response: `-0.0007235890014472002`

Leave-one-out recoveries:

- A latency: `0.09117221418234445`
- B bias pair: `0.02460202604920403`
- C lateral wind drift: `0.00795947901591898`
- D measurement-noise pair: `0.0028943560057886897`
- E innovation response: `0.0065123010130245795`
- F severity response: `0.005788712011577379`

Interaction excess:

- `-0.004341534008682979`

## Transfer confirmation rule

Transfer seed `1313136` is permitted to be exposed exactly once only with the exact development scientific implementation from Git SHA `de181594cbf451f42424ef61f3139351ad0946cd`.

Transfer is considered a mechanism confirmation only if all of the following hold on the fresh transfer partition:

1. construction integrity passes for all 13 contrasts;
2. full-compound execution equivalence remains locked to the frozen Phase 13 domain-13 path;
3. the full-compound failure phenomenon replicates under the existing C13.3 rule;
4. attribution is complete and finite;
5. zero adaptation remains true;
6. **A — latency** is again the largest singleton lateral coverage loss under the preregistered ranking rule;
7. **A — latency** is again the largest leave-one-out lateral recovery under the preregistered ranking rule.

No minimum numerical closeness to the development effect sizes is added post hoc. Transfer tests replication of the preregistered phenomenon and the discovered component identity, not exact numeric equality.

If either component-identity confirmation fails, the development attribution is not treated as transferred and no protected Phase 13C evidence is exposed.

## No-change declaration

Between development and transfer:

- Phase 12 candidate: unchanged
- Phase 13C base domain: unchanged
- component magnitudes: unchanged
- thirteen contrasts: unchanged
- C13.1–C13.5: unchanged
- ranking rule: unchanged
- tie-break rule: unchanged
- interval calibration: unchanged
- controller behavior: unchanged

## Claim boundary

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`
