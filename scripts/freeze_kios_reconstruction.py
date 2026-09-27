#!/usr/bin/env python3
"""Rebuild protected source and stress digests independently from the verified 7z archive.

Requires py7zr. Review the generated lock before committing it; the audit and
prediction runner only *read* that committed lock and never refresh it.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import platform
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from phase25_reconstruction_lock import CONDITIONS, sha256  # noqa: E402
from build_real_image_stress_suite import _rng_for, degrade  # noqa: E402
from uav_safety.real_landing_dataset import read_yolo_boxes, write_single_class_yolo  # noqa: E402

PREFIX = "airisim_dataset2/Real_images_tight_labels/"
METHODS = (
    "scripts/build_real_image_stress_suite.py",
    "scripts/prepare_kios_real_yolo_split.py",
    "src/uav_safety/real_landing_dataset.py",
)


def freeze(archive: Path) -> dict:
    try:
        import py7zr
    except ImportError as exc:
        raise RuntimeError("Install py7zr to verify source files directly against the KIOS archive") from exc

    md5, archive_sha = hashlib.md5(), hashlib.sha256()
    with archive.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            md5.update(block)
            archive_sha.update(block)
    if md5.hexdigest() != "865515c2d8f5e9cd9b2ee1e1ec294270":
        raise ValueError("Archive MD5 differs from the Zenodo record")

    with (ROOT / "results/phase25_failure_atlas/protected_test_manifest.csv").open(newline="", encoding="utf-8") as handle:
        protected = list(csv.DictReader(handle))
    if len(protected) != 86 or len({row["image"] for row in protected}) != 86:
        raise ValueError("Protected manifest does not contain 86 unique images")

    import numpy
    import PIL

    with TemporaryDirectory(prefix="phase25-archive-rebuild-") as directory:
        temp = Path(directory)
        with py7zr.SevenZipFile(archive) as seven_zip:
            members = [name for name in seven_zip.getnames() if name.startswith(PREFIX)]
            real_images = {Path(name).name for name in members if name.lower().endswith(".jpg")}
            if len(real_images) != 422:
                raise ValueError(f"Expected 422 KIOS real images inside the official archive, found {len(real_images)}")
            for row in protected:
                if row["image"] not in real_images or PREFIX + row["label"] not in members:
                    raise ValueError(f"Missing protected image or annotation in archive: {row['image']}")
            targets = [PREFIX + row[name] for row in protected for name in ("image", "label")]
            seven_zip.extract(path=temp, targets=targets)

        source_dir = temp / PREFIX
        label_dir = temp / "derived_labels"
        label_dir.mkdir()
        source_files = {}
        for row in protected:
            name, label = row["image"], row["label"]
            raw_image = source_dir / name
            raw_label = source_dir / label
            boxes = read_yolo_boxes(raw_label, class_id=0)
            write_single_class_yolo(label_dir / label, boxes)
            source_files[name] = {
                "label": label,
                "image_sha256": sha256(raw_image),
                "label_sha256": sha256(label_dir / label),
            }

        # Compute new expectations from the archive bytes, not from caller-supplied
        # source/stress directories or the previous audit output.
        from PIL import Image
        digests = {}
        for condition in CONDITIONS:
            inventory = hashlib.sha256()
            for row in protected:
                name = row["image"]
                with Image.open(source_dir / name) as image:
                    transformed = degrade(image, condition, label_dir / row["label"], _rng_for(name, 20260915))
                    output = temp / "condition.jpg"
                    transformed.save(output, quality=95)
                inventory.update(f"{name}:{sha256(output)}\n".encode())
            digests[condition] = inventory.hexdigest()

    return {
        "schema_version": 1,
        "zenodo_archive_md5": md5.hexdigest(),
        "zenodo_archive_sha256": archive_sha.hexdigest(),
        "split_manifest_sha256": "32623634069c4f3082b79a6a42bca408c636f4b626e5f7691276257999544905",
        "protected_test_files": source_files,
        "condition_image_inventory_sha256": digests,
        "method_sha256": {path: sha256(ROOT / path) for path in METHODS},
        "seed": 20260915,
        "rebuild_runtime": {
            "python": platform.python_version(),
            "pillow": PIL.__version__,
            "numpy": numpy.__version__,
            "py7zr": py7zr.__version__,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.write_text(json.dumps(freeze(args.archive), indent=2) + "\n", encoding="utf-8")
    print(f"Wrote archive-derived reconstruction lock: {args.out}")


if __name__ == "__main__":
    main()
