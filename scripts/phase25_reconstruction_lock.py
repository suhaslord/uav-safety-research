"""Frozen byte checks shared by the KIOS audit and the Phase 25 runner."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "docs/phase25_reconstruction_lock.json"
CONDITIONS = ("clean", "blur", "low_light", "noise", "occlusion", "mixed")


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def load_lock(path: Path = LOCK_PATH) -> dict:
    lock = json.loads(path.read_text(encoding="utf-8"))
    if lock.get("schema_version") != 1 or lock.get("zenodo_archive_md5") != "865515c2d8f5e9cd9b2ee1e1ec294270":
        raise ValueError("Unrecognized Phase 25 reconstruction lock")
    if lock.get("split_manifest_sha256") != "32623634069c4f3082b79a6a42bca408c636f4b626e5f7691276257999544905":
        raise ValueError("Reconstruction lock does not pin the original temporal split")
    if set(lock.get("condition_image_inventory_sha256", {})) != set(CONDITIONS):
        raise ValueError("Reconstruction lock must pin all six conditions")
    if lock.get("seed") != 20260915:
        raise ValueError("Reconstruction lock uses an unexpected stress seed")
    hashes = [lock.get("zenodo_archive_sha256"), *lock["condition_image_inventory_sha256"].values()]
    if any(not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None for value in hashes):
        raise ValueError("Reconstruction lock has missing or malformed content hashes")
    for path, expected in lock.get("method_sha256", {}).items():
        if path not in {"scripts/build_real_image_stress_suite.py", "scripts/prepare_kios_real_yolo_split.py", "src/uav_safety/real_landing_dataset.py"}:
            raise ValueError(f"Unexpected reconstruction method: {path}")
        if sha256(ROOT / path) != expected:
            raise ValueError(f"Reconstruction method changed since freeze: {path}")
    if len(lock.get("method_sha256", {})) != 3:
        raise ValueError("Reconstruction lock does not pin all method files")
    return lock


def verify_archive(archive: Path, lock: dict) -> None:
    md5 = hashlib.md5()
    sha = hashlib.sha256()
    with archive.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            md5.update(block)
            sha.update(block)
    if md5.hexdigest() != lock["zenodo_archive_md5"] or sha.hexdigest() != lock["zenodo_archive_sha256"]:
        raise ValueError("KIOS archive does not match the frozen verified Zenodo download")


def verify_images(rows: list[dict[str, str]], source: Path, stress: Path, lock: dict) -> dict[str, str]:
    """Compare actual file bytes against archive-derived sources and frozen stress digests."""
    expected = lock.get("protected_test_files", {})
    if {row["image"] for row in rows} != set(expected):
        raise ValueError("Frozen source image IDs differ from the protected manifest")
    if len(rows) != len(expected):
        raise ValueError("Frozen source image inventory has duplicate IDs")
    for row in rows:
        name, label = row["image"], row["label"]
        frozen = expected[name]
        if frozen["label"] != label:
            raise ValueError(f"Source label ID changed for {name}")
        if sha256(source / "images/test" / name) != frozen["image_sha256"]:
            raise ValueError(f"Source image differs from the verified Zenodo archive: {name}")
        if sha256(source / "labels/test" / label) != frozen["label_sha256"]:
            raise ValueError(f"Derived source label differs from the Zenodo annotation: {label}")

    names = set(expected)
    label_names = {row["label"] for row in rows}
    condition_digests = {}
    for condition in CONDITIONS:
        image_dir = stress / condition / "images/test"
        label_dir = stress / condition / "labels/test"
        if {p.name for p in image_dir.iterdir() if p.is_file()} != names:
            raise ValueError(f"Incorrect protected image inventory for {condition}")
        if {p.name for p in label_dir.iterdir() if p.is_file()} != label_names:
            raise ValueError(f"Incorrect protected label inventory for {condition}")
        inventory = hashlib.sha256()
        for row in rows:
            name, label = row["image"], row["label"]
            if (label_dir / label).read_bytes() != (source / "labels/test" / label).read_bytes():
                raise ValueError(f"Source label changed in {condition}: {label}")
            inventory.update(f"{name}:{sha256(image_dir / name)}\n".encode())
        observed = inventory.hexdigest()
        if observed != lock["condition_image_inventory_sha256"][condition]:
            raise ValueError(f"{condition} image bytes differ from the frozen reconstruction")
        condition_digests[condition] = observed
    return condition_digests
