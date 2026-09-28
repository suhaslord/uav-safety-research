# Phase 13 execution amendment 02 — pre-result Spearman dependency remediation

## Status

**NON-SCIENTIFIC EXECUTION AMENDMENT RECORDED BEFORE ANY PHASE 13 DEVELOPMENT RESULT OR FRAME ARTIFACT EXISTS.**

This amendment follows `phase13_execution_amendment_01.md`. It does not alter the Phase 13 hypothesis, 13-domain manifest, stress magnitudes, gates, frozen Phase 12 candidate, family partitions, or downstream evidence.

## Second technical attempt

The first amended development execution was GitHub Actions run `34008280645` at head `5c59cdce776182a4ee09416cdda998ba1ace8850`, using replacement development seed `947947`.

Before the evaluation:

- all 49 focused tests passed;
- the parity-only overflow remediation passed its dedicated invariants;
- the exact Phase 12 candidate digest was reverified.

The evaluation proceeded through paired-control generation, shifted generation, predecessor summaries, and per-domain metric computation, then terminated while computing preregistered G13.5.

The failure was:

`ModuleNotFoundError: No module named 'scipy'`

Pandas delegates `Series.corr(..., method="spearman")` to `scipy.stats.spearmanr`, but SciPy was not installed by the repository's normal development extras.

The permanent failure artifact was `9981658507`, digest `sha256:a3f00cc3fc2ab9cfa389f9df336e870709539dbf8081d6b95c12c1f845cf174b`. The workflow had not yet reached any output-writing statement, so no paired-control frame CSV, shifted frame CSV, result JSON, result manifest, per-domain table, Phase 13 gate verdict, or scientific PASS/FAIL value was persisted or exposed.

No Phase 13 metric value from seed `947947` was observed.

## Conservative evidence decision

Because seed `947947` reached in-memory metric computation before the dependency exception, it is retired and will not be rerun.

Retired technical seeds:

- `946946` — invalid pre-result integer-overflow attempt;
- `947947` — invalid pre-result missing-dependency attempt.

Neither is a Phase 13 scientific result.

The final preregistered replacement development seed is fixed now, before its first execution:

- `948948`

The development families remain exactly `1201–1224`.

Downstream evidence remains unchanged and unexposed:

- transfer `957957`, families `1225–1248`
- protected validation `968968`, families `1249–1272`
- final `979979`, families `1273–1296`

## Dependency remediation

The scientific implementation already specified Spearman correlation through Pandas' `method="spearman"` path. The remediation therefore installs the missing runtime dependency rather than changing the statistic.

The authoritative workflow must install:

`scipy==1.16.2`

and must execute a pre-evidence Spearman smoke check before seed `948948` is used.

No Phase 13 metric definition changes.

## Scientific identity after the amendments

The following remain unchanged from the original preregistration:

- exact frozen Phase 12 candidate;
- all 13 domain names and base domains;
- all stress values;
- paired-control design;
- truth-leakage rule;
- all Phase 12 H1-H11 thresholds;
- G13.1-G13.6 definitions and thresholds;
- development families;
- all downstream seeds/families;
- zero-adaptation rule;
- claim boundary.

Only execution plumbing changed:

1. sign parity is bounded before NumPy integer arithmetic;
2. invalid technical seeds are retired rather than reused;
3. the missing SciPy dependency is installed.

## Claim boundary

`simulation_only = true`

`safety_acceptance = false`

`controller_tuning_allowed = false`
