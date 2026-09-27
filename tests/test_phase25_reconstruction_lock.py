"""The input gate must reject content changes even when names and labels still match."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.phase25_reconstruction_lock import CONDITIONS, load_lock, verify_archive, verify_images


def hash_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def test_reconstruction_gate_rejects_image_and_label_tampering(tmp_path: Path) -> None:
    source, stress = tmp_path / "source", tmp_path / "stress"
    row = {"image": "frame.jpg", "label": "frame.txt"}
    source_image = source / "images/test/frame.jpg"
    source_label = source / "labels/test/frame.txt"
    source_image.parent.mkdir(parents=True)
    source_label.parent.mkdir(parents=True)
    source_image.write_bytes(b"original archive image")
    source_label.write_bytes(b"0 0.5 0.5 0.2 0.2\n")
    conditions = {}
    for condition in CONDITIONS:
        image = stress / condition / "images/test/frame.jpg"
        label = stress / condition / "labels/test/frame.txt"
        image.parent.mkdir(parents=True)
        label.parent.mkdir(parents=True)
        image.write_bytes(f"original {condition} image".encode())
        label.write_bytes(source_label.read_bytes())
        conditions[condition] = hash_bytes(f"frame.jpg:{hash_bytes(image.read_bytes())}\n".encode())
    lock = {
        "protected_test_files": {row["image"]: {
            "label": row["label"],
            "image_sha256": hash_bytes(source_image.read_bytes()),
            "label_sha256": hash_bytes(source_label.read_bytes()),
        }},
        "condition_image_inventory_sha256": conditions,
    }
    assert verify_images([row], source, stress, lock) == conditions

    (stress / "noise/images/test/frame.jpg").write_bytes(b"wrong seed, same name")
    with pytest.raises(ValueError, match="noise image bytes differ"):
        verify_images([row], source, stress, lock)

    (stress / "noise/images/test/frame.jpg").write_bytes(b"original noise image")
    source_image.write_bytes(b"different source extraction")
    with pytest.raises(ValueError, match="Source image differs"):
        verify_images([row], source, stress, lock)

    source_image.write_bytes(b"original archive image")
    source_label.write_bytes(b"0 0.5 0.5 0.9 0.9\n")
    for condition in CONDITIONS:
        (stress / condition / "labels/test/frame.txt").write_bytes(source_label.read_bytes())
    with pytest.raises(ValueError, match="Derived source label differs"):
        verify_images([row], source, stress, lock)


def test_archive_is_bound_to_frozen_sha256_and_zenodo_md5(tmp_path: Path) -> None:
    archive = tmp_path / "archive.7z"
    archive.write_bytes(b"verified example archive")
    lock = {
        "zenodo_archive_md5": hashlib.md5(archive.read_bytes()).hexdigest(),
        "zenodo_archive_sha256": hash_bytes(archive.read_bytes()),
    }
    verify_archive(archive, lock)
    archive.write_bytes(b"different archive bytes")
    with pytest.raises(ValueError, match="archive does not match"):
        verify_archive(archive, lock)


def test_frozen_rebuild_reconciles_with_previously_recorded_condition_digests() -> None:
    lock = load_lock()
    report = json.loads((Path(__file__).resolve().parents[1] / "docs/phase25_reconstruction_audit.json").read_text())
    assert len(lock["protected_test_files"]) == 86
    assert lock["condition_image_inventory_sha256"] == report["reconstructed_condition_image_inventory_sha256"]
