# Phase 22 Controlled Occlusion Sweep v2 — Historical Q95 Representation

This is a separate versioned follow-up to the inconclusive raw-source sweep.
The original sweep remains **INCONCLUSIVE — CLEAN GATE FAILED — NO TREATMENT
INFERENCE RUN**. Stage A remains frozen at commits `9dd9293` and `3373aa8`;
its previous missing-protocol readiness record describes that earlier point
in time and is not rewritten by this follow-up.

## Recovery provenance

Only the ten research recovery files from commit
`f090da03d20b2425c5addccb4d19117c8991bcc1` on
`codex/all-work-publication-2026-09-30` were copied byte-for-byte. The old
branch's website/UI history was not merged or cherry-picked.

The original protocol is `docs/phase25_occlusion_sweep_protocol.md`, SHA-256
`e169e16ea40ca44ee60ca8b6074d054c33aeeaf1a3d24e55fa4cd3b8581882d7`.
The recovered publication runner is `scripts/run_phase25_occlusion_sweep.py`,
SHA-256 `939b286418c66fa7a8ab39c6dc981b43324b5804f21f026ff1090a84e95c79a4`.
The source commit explicitly documents that the lost original implementation
freeze and complete runtime receipt were not recovered. We retain that
qualification; the publication runner is not claimed to be byte-identical to
the lost earlier implementation.

A fresh geometry-only replay reconstructed 86 sources × six original doses
`[0, .15, .30, .45, .60, .75]`. Both complete historical manifests match:

| Manifest | SHA-256 |
| --- | --- |
| Image cases | `eb2c4202dcd36f792f0a767986bdc3369e32b04d36360ee9fc7ac6db5f7ead28` |
| Target masks | `76f00fe7050e629a319b9b4d1fb65a0d45c6e9bd127f8f075b2d264d5a4d9554` |

No detector ran during that replay. Hashes of all 516 derived images are in
`results/phase22_occlusion_original_recovery/dose_image_manifest.csv`.
Exact normalized source labels are retained in `source_labels.csv` for
portable, detector-free artifact replay.

## Frozen v2 execution

`results/phase22_occlusion_v2/protocol.json` locks the original dose grid,
mask geometry, matching, outcomes, clean tolerance, descriptive plan,
methods, current runtime, and provenance. Commit this protocol and its
implementation before any v2 detector execution.

The only scientific intervention change is the starting representation:
original JPEG → Pillow RGB decode → historical JPEG Q95 canonicalization →
decode Q95 → original centered RGB(127,127,127) mask → lossless PNG treatment
serialization. Dose zero retains the exact canonical Q95 JPEG bytes; no
nonzero treatment gets another lossy JPEG encoding. The Q95 inventory must
match the historical inventory `2412380094b505c1c21e4dfba9333e534d00ac77ac48fcf12b6b72d709c85316`.

The runtime is the fully recorded Stage A CPU runtime. The historical
publication record used CUDA-built Torch while executing on CPU and recorded
OpenCV 4.11; v2 uses CPU-built Torch and OpenCV 5.0 as recorded in its own
freeze. This is not a claim to reconstruct the missing complete old runtime.
The fresh clean control checks its actual behavior against the historical
benchmark before treatments.

The zero-dose gate uses official validation recall and mAP50, read from
`results/phase23_robust_detector/robustness_comparison.csv`, with tolerance
0.001. Precision and mAP50–95 are also recorded. Treatments are prohibited if
this gate or Stage A fails. Derived treatments are generated only after the
v2 clean gate passes.

The original runner's `model.predict` per-dose execution and confidence-ranked
one-to-one IoU ≥ .50 scoring are preserved. Aggregate clean recall uses the
validator operating point; primary frame/object outcomes use the frozen
confidence floor .001. These are distinct metrics and need not be numerically
identical. All-target frame success permits false positives; FP/frame is
reported separately. Best-overlap confidence refers to the prediction with
highest target IoU, with the original confidence/index tie breaks. Matched-TP
IoU and confidence are labeled as survivor-only summaries.

## Reproduce

Use the runtime in the JSON protocol and supply the verified archive,
original protected source split and exact recovered checkpoint. Substitute
your own absolute paths below. Do not regenerate or overwrite previous
versioned run outputs.

```bash
python scripts/run_phase22_occlusion_v2.py recover \
  --source /path/to/raw_source --weights /path/to/best.pt \
  --archive /path/to/airisim_dataset2.7z --work /path/to/original_replay

python scripts/run_phase22_occlusion_v2.py freeze \
  --source /path/to/raw_source --weights /path/to/best.pt \
  --archive /path/to/airisim_dataset2.7z --work /path/to/v2_views

# Commit protocol and methods before inference; record the exact protocol SHA.
python scripts/run_phase22_occlusion_v2.py run \
  --source /path/to/raw_source --weights /path/to/best.pt \
  --archive /path/to/airisim_dataset2.7z --work /path/to/v2_views \
  --canonical /path/to/HISTORICAL_Q95 --protocol-sha EXACT_PROTOCOL_SHA

python scripts/verify_phase22_occlusion_v2.py
python scripts/reproduce_release.py
python -m pytest
```

The runner refuses inference unless the protocol and methods match their
separate committed freeze. Its preflight receipt is `run_manifest.json`;
`run_outcome.json` is the authoritative final completion/failure status.
Original recovery records are kept unchanged in their imported paths.

Exact pre-inference method bytes are also preserved under
`results/phase22_occlusion_v2/frozen_methods/`. The shared reconstruction helper
was subsequently updated by the independently integrated Phase 23 work.
Offline replay authenticates the archived original bytes against the unchanged
v2 protocol and actual freeze commit; it does not pretend the newer shared
helper was used for v2 inference. To perform a fresh detector rerun of this
frozen implementation, use a separate checkout of `6a8623c` and new output
directories. Do not change the historical protocol's method hashes to match
newer shared files after seeing results.

## Interpretation

The original protocol supports descriptive paired changes from dose zero and
adjacent-dose transitions. The repeated-measures unit is the **86 source
frames**, from two temporally dependent sequences. There are no significance
tests, population-level confidence intervals, or random resampling. There is
therefore no random seed to invent or change. Analysis is deterministic.

The original protocol contains **no preregistered threshold criterion**.
Threshold finding is NOT APPLICABLE; selecting a curve threshold after
inspection is prohibited. Visibility measures annotation-box pixels, not
physical pad surface area. These retrospective, static detector results do
not establish independent-session generalization or flight safety.
