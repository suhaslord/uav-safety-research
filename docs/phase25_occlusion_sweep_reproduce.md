# Publication recovery and future replay

This publication preserves the unchanged protocol, recovered runner source,
rejection tests, and historical metric records. It does **not** restore the lost
complete runtime inventory or original generated image tables. The restored
metric JSON is historical tool-output evidence, not a fresh reproduction.

Read `results/phase25_occlusion_sweep_recovered/restoration_record.json` first.

## Runtime and inputs

The runner rejects any mismatch in Python 3.12.14, torch 2.9.1, torchvision
0.24.1, Ultralytics 8.4.152, NumPy 2.5.3, Pillow 12.3.0, and OpenCV distribution
4.11.0.86. Its freeze command records the complete installed package inventory
and method/input hashes for a future implementation recovery.

The recorded supporting versions were py7zr 1.1.3 and pandas 3.0.6. These core
versions alone do not reconstruct the lost full dependency list.

Download only the persistent release:

```bash
mkdir -p data/external/phase22_recovery_release
curl -fL https://github.com/suhaslord/uav-safety-research/releases/download/phase22-baseline-recovery/phase22_recovery_bundle.zip -o data/external/phase22_recovery_release/phase22_recovery_bundle.zip
python scripts/download_kios_real_landing_dataset.py --accept-download
```

The runner validates the bundle, exact checkpoint, released provenance,
protected split, archive checksums, source image/label hashes, and settings.
There is no fallback to arbitrary local weights or the old Actions artifact.

## Future recovery commands

These are instructions for a future explicitly recorded replay, not commands
that were executed in this publication. Use the pinned environment and a fresh
workspace; do not overwrite valid existing data or historical outputs.

```bash
python scripts/run_phase25_occlusion_sweep.py freeze
python scripts/run_phase25_occlusion_sweep.py prepare
python scripts/run_phase25_occlusion_sweep.py verify
python scripts/run_phase25_occlusion_sweep.py infer
```

The new recovered implementation writes separate locks named
`phase25_occlusion_publication_implementation_freeze.json` and
`phase25_occlusion_publication_input_lock.json`. They must never be relabeled
as the missing original receipts.

Preparation uses lossless PNG compression 9 and LF CSV serialization. Its
complete case table must match the original checksum
`eb2c4202dcd36f792f0a767986bdc3369e32b04d36360ee9fc7ac6db5f7ead28`.
Every image is decoded and compared with the frozen mask pixels before
inference. Verification rejects incomplete, duplicate, corrupt, or altered cases.

The recorded original raw control returned exit code 2 because its mAP50 was
0.42390766686341674 versus the comparison reference 0.4266268678118929.
Any failure before the detector gate is a different failure and must be
reported separately. Never accept an absent gate receipt as the expected stop.

Only after an actually executed raw control gate fails, the separate clean-only
diagnostic can be run:

```bash
python scripts/run_phase25_occlusion_sweep.py diagnose
```

It verifies the published clean inventory and cannot authorize treatments.

## Publication tests

```bash
python -m pytest -q tests/test_phase25_occlusion_sweep_publication.py tests/test_phase25_reconstruction_lock.py tests/test_phase25_failure_audit.py
```

These exercise the recovered source's rejection paths without running a
detector. They are distinct from the earlier historical test receipt.
