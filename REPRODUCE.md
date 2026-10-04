# Reproduce the research evidence

## Current status and scope

The original Phase 23 checkpoint is recovered. A fresh accepted replay matched **all 24 published aggregate metric cells exactly** and **all four prediction tables byte-for-byte**. The existing 516 cross-model outcomes were verified, and a separate 860-row within-model clean-versus-stressed table was generated.

The controlled-occlusion v2 artifacts were replay-verified; the failed original raw-source attempt remains failed. **Phase 26 has no admitted independent dataset.** These are retrospective KIOS and simulation evidence, not flight validation. See [the research record](docs/research_revalidation_2026_10_03.md).

## Read-only release-candidate checks, without model/data downloads

From a full-history checkout with the project dependencies installed:

```bash
pip install -e ".[dev]"
python scripts/validate_research_release.py
pytest -q
```

The validator checks the new frozen manifest, original-checkpoint replay receipt, original Phase 25 table hashes, 860 paired rows, exact f090da03 recovery source, saved controlled-occlusion matches, prospective admission lock, citation/report artifacts and generated site snapshots. A clean checkout is required. It does **not** rerun inference or admit an independent dataset; its report says `inputs_replayed: false`.

`python scripts/reproduce_release.py` remains a narrower Phase 25A baseline-only check. It no longer misreports the current Phase 23 checkpoint as missing. It is not the complete research release gate.

## Replay original detector inference with external inputs

Use the original official KIOS archive and frozen source/stress reconstructions; never replace or regenerate different image bytes and call them the original run. Extract `best.pt` from the authenticated Phase 22 and Phase 23 recovery ZIPs. The input gate rejects wrong checkpoints and images.

The original recovered inference lock is Python **3.13.2**, Ultralytics **8.4.160**, Torch **2.7.0+cu118**, NumPy **2.2.3**, Pillow **11.0.0**. Phase 23 requires an available CUDA device 0; the baseline uses CPU. Do not silently switch device, checkpoint, image size or package versions. Set `YOLO_AUTOINSTALL=False` before any Ultralytics import so test fixtures cannot mutate the pinned environment. Install versions in an isolated environment, not by opportunistic upgrades during a run. Supplemental dependency/hardware observations are documented separately from authenticated original locks.

Native Windows/Git Bash, when not using an editable install:

```bash
export PYTHONPATH='src;.;scripts'
export YOLO_AUTOINSTALL=False
```

On POSIX use `PYTHONPATH='src:.:scripts'` instead. Substitute actual local paths in this command:

```bash
python scripts/run_phase25_frame_audit.py \
  --archive /path/to/airisim_dataset2.7z \
  --source-root /path/to/kios_real_yolo \
  --stress-root /path/to/kios_real_stress \
  --baseline-weights /path/to/original_phase22_best.pt \
  --phase23-weights /path/to/original_phase23_best.pt \
  --out-dir /path/to/new_empty_replay
python scripts/analyze_phase25_failures.py \
  --results-dir /path/to/new_empty_replay
python scripts/verify_phase23_research_replay.py \
  --replay-dir /path/to/new_empty_replay \
  --out-dir /path/to/new_empty_verification
```

The runner checks archive/split/labels/image hashes, original weights, clean committed method/reference files and exact runtime versions. Aggregate validation happens **before** prediction export. The verifier compares every raw table with its frozen counterpart and writes new clean-versus-stressed pairs; it refuses an existing output directory. This is a strict original-evidence replay, not an invitation to tune until outcomes look favorable.

## Controlled occlusion

```bash
python scripts/verify_phase22_occlusion_v2.py
python scripts/summarize_controlled_occlusion.py \
  --out-dir /path/to/new_empty_controlled_summary
```

These commands authenticate and recompute **saved** detections and descriptive statistics. They do not run the detector. The ten recovery files must be exact commit `f090da03d20b2425c5addccb4d19117c8991bcc1`; no old branch/UI is merged. The original raw-source gate failure stays inconclusive. A fresh v2 detector rerun requires the actual `6a8623c` freeze checkout, its separately recorded Linux/CPU runtime and new outputs; see [the v2 method](docs/phase22_occlusion_v2.md). Do not update historical method hashes to match newer working code.

Windows' current atomic writer retains byte verification, file fsync and atomic replacement but cannot claim POSIX directory-fsync durability. Archived frozen method bytes stay unchanged. Exact recovered tests/runner are retained; only generated Windows test fixture paths are adapted outside them.

## Independent Phase 26 admission

```bash
python scripts/verify_phase26_admission_protocol.py
```

This verifies a method-only lock and explicitly returns `NO_DATASET_ADMITTED`, not independent validation. For a future candidate, run the generic screen with **`--near-distance 9`** and the complete checksum-verified reference archive; accepted dHash separation must be at least 10. The generic default 8 is too weak for this locked protocol.

A screening pass still needs documented capture-lineage, rights, annotation/ontology, negatives and disjoint-session review, a committed input lock, development-only rule selection and a sealed-test lock. Existing KIOS frames cannot fill this gate. No placeholder independent results are generated.

## v1.0 preparation boundary

The new manifest, report, real-data figure/table exports and citation/provenance guide prepare a **scoped research release candidate**. No v1.0 tag, release upload, DOI or independent-validation result is created by these commands. A final release still needs its explicit version/citation freeze and selected scope; the historical simulation lineage requires its existing parity/frozen validators for any unchanged simulation claims. Source image/model rights do not inherit the repository's MIT license.
