# Citation and provenance for the research release candidate

Use `CITATION.cff` for the repository author/software citation. Cite the exact Git revision and frozen manifest used; do not cite a moving branch alone. The software/citation version is frozen as **1.0.0rc1**, a release candidate, not an invented final v1.0 tag. This maintenance work does not invent a v1.0 tag, DOI or publication.

## Evidence identities

- Published Phase 23 aggregate result: commit [`7677bacdae1f3a3b73f9473f5fa51f2059d9525a`](https://github.com/suhaslord/uav-safety-research/commit/7677bacdae1f3a3b73f9473f5fa51f2059d9525a).
- Original Phase 23 recovery: [checkpoint recovery release](https://github.com/suhaslord/uav-safety-research/releases/tag/phase23-checkpoint-recovery), bundle SHA-256 `a55531930988deeadf81853d00b63c7e589c6b7fd2270f57653abdb5cdd3e55d`, checkpoint SHA-256 `43240be969708c32b3e11340c9846b3a588baf361378398677c794d16a455310`.
- Original KIOS detector baseline: [Phase 22 baseline recovery release](https://github.com/suhaslord/uav-safety-research/releases/tag/phase22-baseline-recovery), checkpoint SHA-256 `3a1801b192d624f8dcdda4bc5d9a9157309000df67a4c30d62368c37901feddd`. This detector baseline is a different evidence track from the frozen simulation Phase 22 result.
- Recovered controlled-occlusion research source: **only** [`f090da03d20b2425c5addccb4d19117c8991bcc1`](https://github.com/suhaslord/uav-safety-research/commit/f090da03d20b2425c5addccb4d19117c8991bcc1). The lost earlier implementation receipt is not claimed recovered.
- Separately versioned Q95 controlled-occlusion inference freeze: [`6a8623cbeb54951f43b8ca65293598e7c41a474e`](https://github.com/suhaslord/uav-safety-research/commit/6a8623cbeb54951f43b8ca65293598e7c41a474e), with its own saved runtime and failed-original/positive-v2 distinction.
- Accepted original-detector revalidation: [`replay_receipt.json`](../results/research_revalidation_2026_10_03/replay_receipt.json), binding the actual inference commit, original model/runtime identifiers, data hashes, all raw tables and exact source recovery checks.
- Prospective independent-data methods: [`phase26_admission_execution_lock.json`](phase26_admission_execution_lock.json), **no admitted dataset and no independent result**.

## External sources and rights

Credit and cite the creators and exact revision of the [KIOS 2024 Zenodo record](https://zenodo.org/records/13682584), separately from this software. The verified source archive hash is recorded in the reconstruction lock and revalidation receipt. The [older KIOS 2022 record](https://zenodo.org/records/7477560) is an overlapping lineage, not independent validation.

Ultralytics/PyTorch and the recovered model weights are separate software/model dependencies. Check their applicable upstream terms and the recovery release's provenance before redistributing weights. Source imagery, annotations, external model weights and NASA context photographs do not acquire MIT licensing merely because the repository software is MIT. No new source-data permission is inferred here; repository-generated previews are context, not an independent dataset.

## How to cite results without overclaiming

State the checkpoint hash, runtime lock, 86 source frames/two sequences, condition construction, confidence floor and matching convention. Distinguish official aggregate operating-point metrics from frame matches at confidence 0.001. Distinguish 516 cross-model views from 860 within-model clean/stress pairs. Cite the separately frozen controlled v2 study when describing its curve; never attach it to the failed original attempt.

Reference the new retrospective detector report as a research supplement, not a physical-flight or independent generalization study. For a final v1.0 release, freeze the chosen release/citation version and exact scope before publishing; do not imply a DOI or independent dataset that does not exist.
