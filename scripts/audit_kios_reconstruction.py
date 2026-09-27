#!/usr/bin/env python3
"""Verify the reconstructed KIOS inputs without bypassing the Phase 25 model gate."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONDITIONS = ("clean", "blur", "low_light", "noise", "occlusion", "mixed")
SPLIT_SHA256 = "32623634069c4f3082b79a6a42bca408c636f4b626e5f7691276257999544905"


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def audit(archive: Path, source: Path, stress: Path, baseline: Path) -> dict[str, object]:
    if digest(archive, "md5") != "865515c2d8f5e9cd9b2ee1e1ec294270":
        raise ValueError("2024 KIOS Zenodo archive checksum differs from the published MD5")
    if digest(baseline) != "3a1801b192d624f8dcdda4bc5d9a9157309000df67a4c30d62368c37901feddd":
        raise ValueError("Phase 22 baseline checkpoint differs from the recovered Actions artifact")
    split = source / "split_manifest.csv"
    if digest(split) != SPLIT_SHA256:
        raise ValueError("Reconstructed split manifest differs from the original Phase 22 Actions artifact")
    rows = read_csv(split)
    protected = read_csv(ROOT / "results/phase25_failure_atlas/protected_test_manifest.csv")
    test_rows = [{key: row[key] for key in ("sequence", "frame_index", "image", "label")}
                 for row in rows if row["split"] == "test"]
    if test_rows != protected:
        raise ValueError("Reconstructed test rows differ from the protected Phase 25 manifest")
    splits = {split_name: sum(row["split"] == split_name for row in rows)
              for split_name in ("train", "val", "embargo", "test")}
    if splits != {"train": 252, "val": 64, "embargo": 20, "test": 86}:
        raise ValueError(f"Unexpected temporal split counts: {splits}")

    names = {row["image"] for row in protected}
    labels = {row["label"] for row in protected}
    condition_digests: dict[str, str] = {}
    for condition in CONDITIONS:
        folder = stress / condition
        image_dir, label_dir = folder / "images/test", folder / "labels/test"
        if {path.name for path in image_dir.iterdir() if path.is_file()} != names:
            raise ValueError(f"Incorrect protected image inventory for {condition}")
        if {path.name for path in label_dir.iterdir() if path.is_file()} != labels:
            raise ValueError(f"Incorrect protected label inventory for {condition}")
        inventory = hashlib.sha256()
        for row in protected:
            label_path = label_dir / row["label"]
            if label_path.read_bytes() != (source / "labels/test" / row["label"]).read_bytes():
                raise ValueError(f"Source label changed in {condition}: {row['label']}")
            image_path = image_dir / row["image"]
            inventory.update(f"{row['image']}:{digest(image_path)}\n".encode())
        condition_digests[condition] = inventory.hexdigest()

    return {
        "status": "reconstructed_inputs_verified_phase25_predictions_blocked",
        "zenodo_record": "https://zenodo.org/records/13682584",
        "zenodo_archive_md5": digest(archive, "md5"),
        "phase22_baseline_sha256": digest(baseline),
        "split_manifest_sha256": digest(split),
        "protected_manifest_sha256": digest(ROOT / "results/phase25_failure_atlas/protected_test_manifest.csv"),
        "split_counts": splits,
        "condition_count": len(CONDITIONS),
        "frame_condition_count": len(protected) * len(CONDITIONS),
        "reconstructed_condition_image_inventory_sha256": condition_digests,
        "limits": "Original Phase 23 checkpoint and inference package versions absent; original stress-image hashes unpublished; no detector predictions produced.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--stress", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = json.dumps(audit(args.archive, args.source, args.stress, args.baseline), indent=2) + "\n"
    if args.out:
        args.out.write_text(report, encoding="utf-8")
    print(report, end="")


if __name__ == "__main__":
    main()
