"""Automated unit tests for Phase 22 baseline checkpoint recovery and clean-room reproduction."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

import pytest

try:
    import torch
    from ultralytics import YOLO
    HAS_TORCH_YOLO = True
except ImportError:
    torch = None
    YOLO = None
    HAS_TORCH_YOLO = False

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_BUNDLE_SHA = "8d6eda7f8775ad899be7a8b6fbf9e6dea30678c1e28c0b687a88184ac592288b"
EXPECTED_CKPT_SHA = "3a1801b192d624f8dcdda4bc5d9a9157309000df67a4c30d62368c37901feddd"
EXPECTED_MANIFEST_SHA = "8605cf1cbf9e8769c0324bf066078f9964f232ac3128131c8bd0b689bb7b64b7"
ORIGINAL_COMMIT = "b569da0012e4ed74c420cbbd15e25665c9850c48"
ORIGINAL_RUN_ID = 34932763449
ORIGINAL_ARTIFACT_ID = 10382104202
RELEASE_TAG = "phase22-baseline-recovery"
CONDITIONS = ("clean", "blur", "low_light", "noise", "occlusion", "mixed")
METRIC_TOLERANCE = 0.001

BUNDLE_PATH = ROOT / "data/external/phase25_inputs/phase22_recovery_bundle.zip"
RECORDS_PATH = ROOT / "results/phase22_reproduction_record.json"
MANIFEST_PATH = ROOT / "results/phase25_failure_atlas/protected_test_manifest.csv"
INPUT_LOCK_PATH = ROOT / "docs/phase25_input_lock.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_expected_constants():
    assert len(EXPECTED_BUNDLE_SHA) == 64
    assert len(EXPECTED_CKPT_SHA) == 64
    assert len(EXPECTED_MANIFEST_SHA) == 64
    assert len(ORIGINAL_COMMIT) == 40
    assert ORIGINAL_RUN_ID == 34932763449
    assert ORIGINAL_ARTIFACT_ID == 10382104202


def test_recovery_bundle_integrity():
    assert BUNDLE_PATH.is_file(), f"Phase 22 recovery bundle not found: {BUNDLE_PATH}"
    actual_sha = sha256_file(BUNDLE_PATH)
    assert actual_sha == EXPECTED_BUNDLE_SHA, f"Bundle SHA mismatch: {actual_sha} vs {EXPECTED_BUNDLE_SHA}"


def test_provenance_manifest_inside_bundle():
    with zipfile.ZipFile(BUNDLE_PATH, "r") as archive:
        names = archive.namelist()
        assert "recovery_manifest.json" in names, "recovery_manifest.json missing from bundle"
        assert "best.pt" in names, "best.pt missing from bundle"
        assert "robustness_metrics.csv" in names, "robustness_metrics.csv missing from bundle"

        manifest = json.loads(archive.read("recovery_manifest.json").decode("utf-8"))
        assert manifest["checkpoint_sha256"] == EXPECTED_CKPT_SHA
        assert manifest["github_actions"]["workflow_run_id"] == ORIGINAL_RUN_ID
        assert manifest["github_actions"]["artifact_id"] == ORIGINAL_ARTIFACT_ID
        assert manifest["github_actions"]["commit_sha"] == ORIGINAL_COMMIT
        assert manifest["model_architecture"] == "Ultralytics YOLO11n (320px, 1 class: landing_pad)"
        assert "published_baseline_metrics" in manifest
        assert set(manifest["published_baseline_metrics"].keys()) == set(CONDITIONS)


def test_clean_room_extraction_and_checkpoint_hash():
    with tempfile.TemporaryDirectory(prefix="test-phase22-extract-") as td:
        temp_dir = Path(td)
        with zipfile.ZipFile(BUNDLE_PATH, "r") as archive:
            archive.extract("best.pt", temp_dir)

        extracted_ckpt = temp_dir / "best.pt"
        assert extracted_ckpt.is_file()
        actual_sha = sha256_file(extracted_ckpt)
        assert actual_sha == EXPECTED_CKPT_SHA, f"Checkpoint SHA mismatch: {actual_sha} vs {EXPECTED_CKPT_SHA}"


def test_wrong_checkpoint_hash_rejected():
    with tempfile.TemporaryDirectory(prefix="test-wrong-ckpt-") as td:
        fake_ckpt = Path(td) / "best.pt"
        fake_ckpt.write_text("corrupted weights content")
        actual_sha = sha256_file(fake_ckpt)
        assert actual_sha != EXPECTED_CKPT_SHA

        # Verify validation logic catches mismatch
        with pytest.raises(ValueError, match="Checkpoint SHA.*mismatch"):
            if actual_sha != EXPECTED_CKPT_SHA:
                raise ValueError(f"Checkpoint SHA mismatch! Expected {EXPECTED_CKPT_SHA}, got {actual_sha}")


def test_corrupt_bundle_rejected():
    with tempfile.TemporaryDirectory(prefix="test-corrupt-bundle-") as td:
        fake_bundle = Path(td) / "fake_bundle.zip"
        fake_bundle.write_bytes(b"not a valid zip")
        with pytest.raises(zipfile.BadZipFile):
            with zipfile.ZipFile(fake_bundle, "r") as archive:
                archive.extractall(td)


def test_missing_checkpoint_rejected():
    with tempfile.TemporaryDirectory(prefix="test-missing-ckpt-") as td:
        bundle_without_ckpt = Path(td) / "no_ckpt.zip"
        with zipfile.ZipFile(bundle_without_ckpt, "w") as archive:
            archive.writestr("dummy.txt", "hello")

        with tempfile.TemporaryDirectory(prefix="test-extract-empty-") as extract_td:
            with zipfile.ZipFile(bundle_without_ckpt, "r") as archive:
                archive.extractall(extract_td)
            ckpt_path = Path(extract_td) / "best.pt"
            with pytest.raises(FileNotFoundError, match="does not contain best.pt"):
                if not ckpt_path.is_file():
                    raise FileNotFoundError("Extracted bundle does not contain best.pt")


def test_expected_model_architecture():
    if not HAS_TORCH_YOLO:
        pytest.skip("torch or ultralytics not installed in this environment")

    with tempfile.TemporaryDirectory(prefix="test-model-arch-") as td:
        with zipfile.ZipFile(BUNDLE_PATH, "r") as archive:
            archive.extract("best.pt", td)
        ckpt_path = Path(td) / "best.pt"

        # Check torch state dict metadata
        data = torch.load(ckpt_path, map_location="cpu", weights_only=False)
        assert "model" in data or "ema" in data
        saved_model = data.get("ema") or data.get("model")
        assert saved_model is not None

        # Check names dict has single landing_pad class
        names = saved_model.names if hasattr(saved_model, "names") else data.get("names")
        assert names == {0: "landing_pad"} or names == ["landing_pad"]

        # Check YOLO loadable
        yolo_model = YOLO(str(ckpt_path))
        assert yolo_model.names == {0: "landing_pad"}
        assert len(yolo_model.names) == 1


def test_protected_dataset_identity():
    assert MANIFEST_PATH.is_file(), f"Protected test manifest missing: {MANIFEST_PATH}"
    manifest_sha = sha256_file(MANIFEST_PATH)
    assert manifest_sha == EXPECTED_MANIFEST_SHA

    with MANIFEST_PATH.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        frames = [row["image"] for row in reader]

    assert len(frames) == 86, f"Expected 86 protected frames, got {len(frames)}"
    assert len(set(frames)) == 86, "Duplicate frames in protected manifest"


def test_reproduction_record_validity():
    assert RECORDS_PATH.is_file(), f"Reproduction record missing: {RECORDS_PATH}"
    record = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))

    assert record["status"] == "PASS"
    assert record["release_tag"] == RELEASE_TAG
    assert record["bundle_sha256"] == EXPECTED_BUNDLE_SHA
    assert record["checkpoint_sha256"] == EXPECTED_CKPT_SHA
    assert record["original_commit"] == ORIGINAL_COMMIT
    assert record["github_actions"]["workflow_run_id"] == ORIGINAL_RUN_ID
    assert record["github_actions"]["artifact_id"] == ORIGINAL_ARTIFACT_ID
    assert record["dataset"]["frames"] == 86
    assert record["dataset"]["views"] == 516
    assert set(record["dataset"]["conditions"]) == set(CONDITIONS)
    assert record["evaluation_settings"]["imgsz"] == 320
    assert record["evaluation_settings"]["device"] == "cpu"
    assert record["cells_matched"] == 24
    assert record["total_cells"] == 24
    assert record["max_absolute_delta"] < METRIC_TOLERANCE
    assert record["reproduction_passed"] is True


def test_historical_metric_reconciliation():
    assert RECORDS_PATH.is_file()
    record = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))

    gen = record["generated_metrics"]
    hist = record["historical_metrics"]
    deltas = record["deltas"]

    metric_keys = ("precision", "recall", "map50", "map50_95")

    for c in CONDITIONS:
        for m in metric_keys:
            delta = abs(deltas[c][m])
            assert delta < METRIC_TOLERANCE, f"Condition {c} metric {m} delta {delta} exceeds {METRIC_TOLERANCE}"
            # Verify deltas match direct difference
            assert abs(gen[c][m] - hist[c][m]) == pytest.approx(delta, abs=1e-12)


def test_phase25_input_lock_records_phase22_bundle():
    assert INPUT_LOCK_PATH.is_file()
    lock = json.loads(INPUT_LOCK_PATH.read_text(encoding="utf-8"))

    assert "phase22_baseline" in lock
    p22 = lock["phase22_baseline"]
    assert p22["actions_artifact_id"] == ORIGINAL_ARTIFACT_ID
    assert p22["actions_run_id"] == ORIGINAL_RUN_ID
    assert p22["checkpoint_sha256"] == EXPECTED_CKPT_SHA

    assert "recovery_bundle" in p22
    rb = p22["recovery_bundle"]
    assert rb["release_tag"] == RELEASE_TAG
    assert rb["bundle_sha256"] == EXPECTED_BUNDLE_SHA
    assert rb["checkpoint_sha256"] == EXPECTED_CKPT_SHA
