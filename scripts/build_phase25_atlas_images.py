#!/usr/bin/env python3
"""Rebuild and publish verified, web-sized Phase 25 frame images."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import py7zr
from PIL import Image

from phase25_reconstruction_lock import (
    CONDITIONS,
    load_lock,
    sha256,
    verify_archive,
    verify_images,
)

ROOT = Path(__file__).resolve().parents[1]
SPLIT_SHA256 = "32623634069c4f3082b79a6a42bca408c636f4b626e5f7691276257999544905"
PROTECTED_MANIFEST_SHA256 = "8605cf1cbf9e8769c0324bf066078f9964f232ac3128131c8bd0b689bb7b64b7"
MAX_WIDTH = 640


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def prepare_reconstruction(archive: Path, work: Path) -> tuple[Path, Path]:
    extracted = work / "extracted"
    source = work / "kios_real_yolo"
    stress = work / "kios_real_stress"
    dataset_root = extracted / "airisim_dataset2"
    if not (dataset_root / "Real_images_tight_labels").is_dir():
        shutil.rmtree(extracted, ignore_errors=True)
        extracted.mkdir(parents=True, exist_ok=True)
        with py7zr.SevenZipFile(archive, mode="r") as bundle:
            names = [
                name for name in bundle.getnames()
                if name.startswith("airisim_dataset2/Real_images_tight_labels/")
            ]
            if len(names) != 845:
                raise ValueError(f"Expected 845 labeled real-image archive entries, found {len(names)}")
            bundle.extract(path=extracted, targets=names)

    subprocess.run(
        [sys.executable, str(ROOT / "scripts/prepare_kios_real_yolo_split.py"),
         "--dataset-root", str(extracted), "--out", str(source)],
        cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT / "src")}, check=True,
    )
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_real_image_stress_suite.py"),
         "--split-root", str(source), "--out", str(stress), "--seed", "20260915"],
        cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT / "src")}, check=True,
    )
    return source, stress


def build_assets(archive: Path, source: Path, stress: Path, output: Path) -> dict[str, object]:
    lock = load_lock()
    verify_archive(archive, lock)
    split_manifest = source / "split_manifest.csv"
    if sha256(split_manifest) != SPLIT_SHA256:
        raise ValueError("Rebuilt split does not match the original protected temporal split")
    rows = read_rows(split_manifest)
    protected = read_rows(ROOT / "results/phase25_failure_atlas/protected_test_manifest.csv")
    protected_rows = [
        {key: row[key] for key in ("sequence", "frame_index", "image", "label")}
        for row in rows if row["split"] == "test"
    ]
    if protected_rows != protected:
        raise ValueError("Rebuilt test IDs differ from the protected Phase 25 manifest")
    if sha256(ROOT / "results/phase25_failure_atlas/protected_test_manifest.csv") != PROTECTED_MANIFEST_SHA256:
        raise ValueError("The protected Phase 25 manifest changed")

    inventories = verify_images(protected, source, stress, lock)
    shutil.rmtree(output, ignore_errors=True)
    manifest: dict[str, object] = {
        "status": "verified_reconstruction_web_previews",
        "zenodo_record": "https://zenodo.org/records/13682584",
        "archive_sha256": lock["zenodo_archive_sha256"],
        "protected_manifest_sha256": PROTECTED_MANIFEST_SHA256,
        "stress_inventory_sha256": inventories,
        "preview_max_width": MAX_WIDTH,
        "preview_count": 0,
        "conditions": {},
    }
    total = 0
    for condition in CONDITIONS:
        entries: dict[str, dict[str, object]] = {}
        source_dir = stress / condition / "images/test"
        names = sorted(path.name for path in source_dir.iterdir() if path.is_file())
        if names != sorted(row["image"] for row in protected):
            raise ValueError(f"Unexpected {condition} preview input inventory")
        for filename in names:
            source_image = source_dir / filename
            target = output / condition / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(source_image) as opened:
                image = opened.convert("RGB")
                if image.width > MAX_WIDTH:
                    height = round(image.height * MAX_WIDTH / image.width)
                    image = image.resize((MAX_WIDTH, height), Image.Resampling.LANCZOS)
                image.save(target, format="JPEG", quality=86, optimize=True)
                width, height = image.size
            entries[filename] = {
                "source_sha256": sha256(source_image),
                "preview_sha256": sha256(target),
                "width": width,
                "height": height,
                "bytes": target.stat().st_size,
            }
            total += 1
        manifest["conditions"][condition] = entries

    if total != 516:
        raise ValueError(f"Expected 516 frame-condition previews, created {total}")
    manifest["preview_count"] = total
    manifest["preview_bytes"] = sum(
        item["bytes"] for condition_rows in manifest["conditions"].values()
        for item in condition_rows.values()
    )
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=ROOT / "deploy/vercel/media/phase25")
    args = parser.parse_args()
    lock = load_lock()
    verify_archive(args.archive, lock)
    source, stress = prepare_reconstruction(args.archive, args.work)
    manifest = build_assets(args.archive, source, stress, args.out)
    print(json.dumps({key: manifest[key] for key in ("status", "preview_count", "preview_bytes", "stress_inventory_sha256")}, indent=2))


if __name__ == "__main__":
    main()
