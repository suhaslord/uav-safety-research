"""Metadata preflight catches missing study design before slow archive screening."""
import csv
import hashlib
from pathlib import Path

from scripts.check_phase26_metadata import preflight


def manifest(tmp_path: Path, *, size=30, no_negatives=False, shared_video=False,
             shared_hash=False, shared_session=False, no_test_negative=False) -> Path:
    path = tmp_path / "manifest.csv"
    rows = []
    for i in range(size):
        split = "dev" if i < size // 2 else "test"
        empty = i == 0 or (i == size // 2 and not no_test_negative)
        if no_negatives:
            empty = False
        rows.append({
            "path": f"{split}/frame_{i:03d}.png",
            "partition": split,
            "session_id": "session-one" if (split == "dev" or shared_session) else "session-two",
            "source_video_id": "video-one" if (split == "dev" or shared_video) else "video-two",
            "target_count": "0" if empty else "1",
            "sha256": hashlib.sha256(str(0 if shared_hash and i == size // 2 else i).encode()).hexdigest(),
        })
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_complete_inventory_is_only_ready_for_archive_screen(tmp_path):
    result = preflight(manifest(tmp_path))
    assert result["status"] == "metadata_only_ready_for_archive_screen"
    assert result["total_images"] == 30
    assert result["documented_session_ids"] == 2
    assert result["counts"]["dev"]["empty_target_images"] == 1
    assert result["counts"]["test"]["empty_target_images"] == 1
    assert result["independent_test_admitted"] is False
    assert result["test_detector_inference_authorized"] is False
    assert not result["reasons"]


def test_insufficient_frames_and_no_negative_images_are_blocked(tmp_path):
    result = preflight(manifest(tmp_path, size=8, no_negatives=True))
    assert result["status"] == "blocked"
    assert "fewer_than_30_candidate_frames" in result["reasons"]
    assert "no_empty_target_frames" in result["reasons"]


def test_metadata_leaks_are_rejected(tmp_path):
    result = preflight(manifest(tmp_path, shared_video=True, shared_session=True, shared_hash=True))
    assert result["status"] == "blocked"
    assert "source_video_shared_between_dev_and_test" in result["reasons"]
    assert "session_shared_between_dev_and_test" in result["reasons"]
    assert "image_sha256_shared_between_dev_and_test" in result["reasons"]


def test_single_partition_negatives_are_reported_without_redefining_frozen_gate(tmp_path):
    # Frozen policy requires a verified negative inventory overall; report gaps
    # in either split without silently changing the preregistered admission rule.
    result = preflight(manifest(tmp_path, no_test_negative=True))
    assert result["status"] == "metadata_only_ready_for_archive_screen"
    assert result["warnings"] == ["no_empty_target_frames_in_test"]


def test_duplicate_paths_and_bad_sha_are_rejected(tmp_path):
    path = manifest(tmp_path)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    chunks = lines[2].split(",")
    chunks[0] = lines[1].split(",")[0]
    chunks[-1] = "not-a-hash"
    lines[2] = ",".join(chunks)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = preflight(path)
    assert "invalid_or_duplicate_image_path" in result["reasons"]
    assert "missing_or_invalid_image_sha256" in result["reasons"]
