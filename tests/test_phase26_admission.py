"""Research boundaries: never leak labels or accept a contaminated test split."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from PIL import Image
import pytest

from scripts.audit_phase26_manifest import audit
from scripts.phase26_reliability import (
    accept, confidence_score, select_development_threshold, top_localization_correct,
)
from scripts.reproduce_release import verify


def save_image(path: Path, color: str) -> None:
    image = Image.new("RGB", (12, 12), color)
    image.putpixel((1, 1), (13, 98, 190))
    image.save(path)


def candidate(tmp_path: Path, *, same_image=False, same_session=False, empty_session=False):
    ref = tmp_path / "reference"
    ext = tmp_path / "external"
    ref.mkdir()
    ext.mkdir()
    save_image(ref / "original.png", "red")
    save_image(ext / "dev.png", "red" if same_image else "green")
    save_image(ext / "test.png", "blue")
    rows = []
    for name, partition, count in (("dev.png", "dev", 0), ("test.png", "test", 1)):
        rows.append({"path": name, "partition": partition, "session_id": "s1" if same_session else ("" if empty_session else partition),
                     "source_video_id": "v1" if same_session else partition, "target_count": count,
                     "sha256": hashlib.sha256((ext / name).read_bytes()).hexdigest()})
    manifest = tmp_path / "manifest.csv"
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return ref, ext, manifest


def test_no_label_access_at_runtime_and_negative_policy() -> None:
    wrong = [{"class": "landing_target", "score": 0.92, "box": (0, 0, 1, 1)}]
    matched = [{"class": "landing_target", "score": 0.71, "box": (2, 2, 3, 3)}]
    assert confidence_score(wrong) == 0.92
    assert accept(wrong, 0.70)
    assert not top_localization_correct(wrong, [])
    assert top_localization_correct(matched, [(2, 2, 3, 3)])
    assert confidence_score([]) == 0
    assert not accept([], 0.05)
    assert not top_localization_correct([], [])
    assert not accept(wrong, None)


def test_development_selection_keeps_full_trace_and_failed_gate() -> None:
    selection = select_development_threshold([(0.9, True), (0.8, False), (0.2, True)])
    assert selection["threshold"] == 0.9  # higher threshold wins an equal-coverage tie
    assert len(selection["trace"]) == 19
    assert select_development_threshold([(0.9, False)])["threshold"] is None


def test_reference_duplicate_blocks_admission(tmp_path: Path) -> None:
    result = audit(*candidate(tmp_path, same_image=True), expected_reference_count=1)
    assert result["status"] == "blocked"
    assert "candidate_overlaps_KIOS" in result["reasons"]
    assert any(row["kind"] == "decoded_pixels" for row in result["exact_overlaps"])
    assert result["empty_target_count"] == 1


def test_unknown_or_shared_sessions_block_admission(tmp_path: Path) -> None:
    ref, ext, manifest = candidate(tmp_path, same_session=True)
    result = audit(ref, ext, manifest, expected_reference_count=1, near_distance=0)
    assert "session_shared_between_dev_and_test" in result["reasons"]
    assert "source_video_shared_between_dev_and_test" in result["reasons"]


def test_manifest_requires_exact_file_inventory_and_hash(tmp_path: Path) -> None:
    ref, ext, manifest = candidate(tmp_path)
    (ext / "extra.png").write_bytes((ext / "dev.png").read_bytes())
    with pytest.raises(ValueError, match="omits"):
        audit(ref, ext, manifest, expected_reference_count=1)
    (ext / "extra.png").unlink()
    (ext / "test.png").write_bytes((ext / "dev.png").read_bytes())
    with pytest.raises(ValueError, match="hash mismatch"):
        audit(ref, ext, manifest, expected_reference_count=1)


def test_committed_baseline_hashes_replay_without_phase23_claim() -> None:
    result = verify(check_site=False)
    assert result["status"] == "committed_phase25a_verified"
    assert result["inputs_replayed"] is False
    assert result["phase23"].startswith("PENDING")


def test_reproduction_page_identifies_exact_artifacts_and_pending_results() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "results/phase25_baseline_diagnostic/run_manifest.json").read_text())
    page = (root / "deploy/vercel/reproduce.html").read_text()
    for field in ("source_archive_sha256", "checkpoint_sha256"):
        assert manifest[field] in page
    assert manifest["input_verification"]["split_manifest_sha256"] in page
    assert "Phase 23 exact weights" in page and "Unavailable" in page
    assert "inputs_replayed: false" in page
