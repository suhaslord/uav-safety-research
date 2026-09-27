#!/usr/bin/env python3
"""Screen a proposed Phase 26 image archive against every Phase 25 KIOS real frame."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


def normalized_name(name: str) -> str:
    return re.sub(r"^\d+_", "", Path(name).name).casefold()


def candidate_audit(reference_root: Path, candidate_zip: Path) -> dict[str, object]:
    reference = sorted(p for p in reference_root.rglob("*") if p.is_file() and p.suffix.lower() in SUFFIXES)
    if not reference:
        raise ValueError("No reference images found")
    reference_hashes: dict[str, str] = {}
    reference_names: dict[str, str] = {}
    for path in reference:
        reference_hashes[hashlib.sha256(path.read_bytes()).hexdigest()] = str(path.relative_to(reference_root))
        reference_names[normalized_name(path.name)] = str(path.relative_to(reference_root))
    hashes_matched: set[str] = set()
    names_matched: set[str] = set()
    images = 0
    archive_sha256 = hashlib.sha256()
    with candidate_zip.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            archive_sha256.update(block)
    with zipfile.ZipFile(candidate_zip) as archive:
        for member in archive.infolist():
            if member.is_dir() or Path(member.filename).suffix.lower() not in SUFFIXES:
                continue
            images += 1
            with archive.open(member) as source:
                value = hashlib.sha256()
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    value.update(block)
            if value.hexdigest() in reference_hashes:
                hashes_matched.add(reference_hashes[value.hexdigest()])
            normalized = normalized_name(member.filename)
            if normalized in reference_names:
                names_matched.add(reference_names[normalized])
    if not images:
        raise ValueError("Candidate archive has no images")
    return {
        "status": "rejected_overlap" if hashes_matched or names_matched else "no_exact_or_name_overlap_found_further_review_required",
        "reference_image_count": len(reference),
        "candidate_archive_sha256": archive_sha256.hexdigest(),
        "candidate_image_count": images,
        "reference_exact_byte_matches": len(hashes_matched),
        "reference_matching_source_names": len(names_matched),
        "limitations": "A pass is not evidence of independence: screen perceptual near-duplicates, source sequences, annotations, rights, and collection history before assigning any development or new evaluation split.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-root", type=Path, required=True)
    parser.add_argument("--candidate-zip", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = candidate_audit(args.reference_root, args.candidate_zip)
    content = json.dumps(report, indent=2) + "\n"
    if args.out:
        args.out.write_text(content, encoding="utf-8")
    print(content, end="")
    return 2 if report["status"] == "rejected_overlap" else 0


if __name__ == "__main__":
    raise SystemExit(main())
