# Reproduce the current evidence

Phase 25A has measured Phase 22 baseline detections over 516 verified KIOS
views. Phase 23 paired outcomes and Phase 26 external reliability results are
still pending.

## Verify the committed outputs without private inputs

```bash
python scripts/reproduce_release.py
```

This read-only command checks SHA-256 hashes for every Phase 25A result table
and frozen method file listed in
`results/phase25_baseline_diagnostic/run_manifest.json`. It also checks that
both site snapshots rebuild to the committed bytes. It prints a machine-readable
report and returns a nonzero exit code if any check fails. For a saved report,
use `--out PATH` with a path that does not yet exist.

**Scope:** a successful check verifies the committed evidence and site data.
It does not rerun model inference, prove image identity without the external
inputs, reconstruct the original Phase 23 checkpoint, or validate Phase 26.
The JSON report includes `inputs_replayed: false` for that reason.

## Replay Phase 25A inference with external inputs

Follow [the Phase 25A diagnostic](docs/phase25_baseline_diagnostic.md) to
recover the checksum-verified official KIOS archive, the exact Phase 22 model,
and all six frozen reconstructed image inventories. Run the baseline runner in
its pinned Python/Torch/Ultralytics/NumPy/Pillow environment on an **empty**
output directory, then compare its table hashes to the run manifest. The
runner checks archive, source, split, stress and checkpoint identity before
inference. Never substitute a fresh model or regenerated image with different
bytes and call it the original Phase 25A run.

## Next gates

- Paired Phase 25: recover exact Phase 23 `best.pt` and original inference
  versions, then pass all six published aggregate checks before exporting boxes.
- Phase 26: run the [candidate admission protocol](docs/phase26_imav2025_preregistration.md)
  against the verified official KIOS archive before freezing a development
  threshold. The development-rule lock rejects test outcome rows. Admission
  also requires independent session, annotation and rights review before the
  new test set is opened.
- v1.0: complete the manuscript, admission/paired-result record or an explicit
  scope amendment, release manifest, citation version and clean-clone check
  before tagging. No v1.0 release is claimed here.
