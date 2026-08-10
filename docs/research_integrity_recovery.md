# Research integrity recovery — Phase 6 image experiments

## Purpose

This note records an execution/history issue discovered during Phase 6D development and supersedes any earlier document or metadata field that still describes seeds `868686` or `878787` as unseen.

No historical result is deleted or relabeled. The goal is to preserve the evidence and make the later validation protocol unambiguous.

## What was discovered

The historical Phase 6B frozen-evaluation workflow had already been executed before the Phase 6D freeze decision:

- GitHub Actions run: `31355377934`
- frozen executable commit: `b4e9838555e935a5ec42690495315473629b58f6`
- landing seed: `868686`
- selective-perception seed: `878787`

Therefore both `868686` and `878787` are **permanently seen historical seeds**. They may be reported as Phase 6B held-out evidence, but they must never be described or reused as held-out validation for Phase 6C, Phase 6D, Phase 6E, or any later architecture.

The archived Phase 6B evidence remains preserved on the historical `phase6-image-aegis` line, including provenance committed by GitHub Actions. That historical branch is not force-rewritten in this recovery.

## Branch recovery

Later Phase 6C/6D development commits were no longer present at the tip of `phase6-image-aegis` after the historical archival line advanced from an older Phase 6B snapshot.

A new working branch was therefore created from the last intact Phase 6D development commit:

- recovery branch: `phase6-integrity-recovery`
- recovery base commit: `61b7d9eaaec3113cad19ef49aa89d847a7fb9773`

The old Phase 6B frozen-evaluation workflow is disabled as an experiment runner on the recovery branch. It now contains only a historical notice so the old seeds cannot be accidentally rerun by editing that workflow.

## Replacement held-out seeds

Before any new Phase 6E development or later held-out evaluation, two replacement top-level seed families were selected and searched in the repository. No repository matches were found for either value at reservation time.

- **replacement landing held-out seed:** `918271`
- **replacement selective-perception held-out seed:** `928271`

These seeds are reserved from this point forward and must not be used for:

- development tuning;
- diagnostics;
- threshold selection;
- ablations;
- candidate comparisons;
- smoke tests.

They may be executed only after a final architecture and all constants are frozen in writing. Each replacement seed is to be run once for the corresponding final evaluation and reported regardless of outcome.

## Seed status table

| Seed | Role | Status |
|---|---|---|
| `747474` | historical Phase 6 landing | seen |
| `757575` | historical Phase 6 selective perception | seen |
| `868686` | historical Phase 6B frozen landing | seen; do not reuse as held-out |
| `878787` | historical Phase 6B frozen selective perception | seen; do not reuse as held-out |
| `626262` | Phase 6 development landing family | seen development |
| `616161` | calibration family | seen development/calibration |
| `918271` | replacement final landing | **reserved unseen** |
| `928271` | replacement final selective perception | **reserved unseen** |

## Phase 6D status at recovery

Phase 6D is **not frozen**.

Its candidate landing rates on the development family were strong, but the preregistered alias-audit criterion failed because the 3-sigma hard-altitude-alias detector activated widely in nominal conditions, including essentially all clean episodes and most blur episodes. This is treated as a detector-calibration failure even though the landing outcome table was favorable.

The next revision must therefore be developed from estimator-consistency evidence, not by changing the 3-sigma number to improve the landing table.

## Required next step

Diagnose the false hard-alias activations on already-seen development episodes and construct an altitude-specific, age-aware consistency benchmark. Any Phase 6E rule must be selected on that detector benchmark before it is connected to landing outcomes.
