# Phase 13 execution amendment 01 — pre-result integer-overflow remediation

## Status

**NON-SCIENTIFIC EXECUTION AMENDMENT RECORDED BEFORE ANY PHASE 13 DEVELOPMENT RESULT OR FRAME ARTIFACT EXISTS.**

This note does not alter the Phase 13 hypothesis, the 13-domain manifest, any stress magnitude, any gate, the frozen Phase 12 candidate, or any downstream evidence partition.

## Failed technical attempt

The first Phase 13 development workflow attempt was GitHub Actions run `34008119532` at scientific head `01a031ca887d33d6bb1f63ff4bf0626a3edd9acf`.

Pre-evidence checks succeeded:

- all 45 focused scientific/invariant tests passed;
- the exact frozen Phase 12 candidate was recovered;
- candidate SHA-256 `e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991` was verified.

The execution then terminated before writing any Phase 13 frame file, result JSON, or result manifest.

The failure was:

`OverflowError: Python int too large to convert to C long`

at the preregistered `reacquisition_shock` sign calculation, where a SHA-derived Python integer was added directly to a NumPy integer frame array before reducing the expression modulo 2.

The uploaded audit artifact was `9981606849`, digest `sha256:d21c386954f10667770c9c8c8a5a3881ffdd18c78980667e752f432eae9ce79f`, and contained only an empty `phase13-development.log`. It contained no frames, no metrics, no gate verdict, and no result JSON.

No scientific outcome was observed from seed `946946`.

## Conservative evidence decision

Even though no usable result was emitted, seed `946946` is retired rather than reused because the failed process had already entered the event-generation code path before the integer exception.

Retired technical seed:

- `946946` — **INVALID_TECHNICAL_ATTEMPT / NEVER_A_PHASE13_RESULT**

Replacement development seed, fixed before its first execution:

- `947947`

The replacement seed is development-only and may never become transfer, protected, or final evidence.

The family range remains exactly `1201–1224`.

Downstream preregistered evidence is unchanged and remains unexposed:

- transfer `957957`, families `1225–1248`
- protected validation `968968`, families `1249–1272`
- final `979979`, families `1273–1296`

## Code remediation

The intended reacquisition-shock rule requires only a deterministic parity bit for sign selection.

The remediation reduces the two-argument SHA-derived sign seed to its parity bit **before** NumPy arithmetic:

`parity = stable_seed(sequence_id, profile_name) & 1`

and then uses:

`(frame + parity) % 2`

All other SHA-derived streams — latency jitter, sequence phase, and noise RNG seeds — remain byte-for-byte governed by the original stable-seed function.

This fixes integer representation only. It does not change:

- any domain definition;
- any stress magnitude;
- any error gain, bias, lag, drift, gust, tail probability, or noise sigma;
- any innovation gain or severity delta;
- any Phase 12 model parameter;
- any interval radius;
- any evaluation gate or threshold;
- any evidence-role rule;
- the claim boundary.

## Authoritative development execution

The authoritative first Phase 13 development result must therefore:

1. use replacement seed `947947`;
2. use families `1201–1224`;
3. use the unchanged 13-domain manifest;
4. use the exact frozen Phase 12 candidate;
5. use the parity-only overflow remediation described above;
6. emit persistent paired-control frames, shifted frames, result JSON, manifest, and log;
7. be exposed once only.

The failed run `34008119532` and artifact `9981606849` remain part of the permanent audit trail and must not be represented as a Phase 13 scientific result.

## Claim boundary

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`
