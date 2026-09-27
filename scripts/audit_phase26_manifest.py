#!/usr/bin/env python3
"""Screen a labeled external-image manifest without running a detector.

Input CSV: path,partition,session_id,source_video_id,target_count,sha256.
The source IDs must come from capture provenance, never inferred from pixels.
An audit cannot certify provenance, class geometry, rights, or independence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re

from PIL import Image, ImageOps

SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
FIELDS = {"path", "partition", "session_id", "source_video_id", "target_count", "sha256"}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def fingerprint(path: Path) -> tuple[str, int]:
    """Decoded-pixel SHA-256 and a 64-bit horizontal difference hash."""
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        pixels = hashlib.sha256(image.width.to_bytes(4, "big") + image.height.to_bytes(4, "big") + image.tobytes()).hexdigest()
        gray = image.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
        values = list(gray.tobytes())
    dhash = sum((values[y * 9 + x] > values[y * 9 + x + 1]) << (y * 8 + x)
                for y in range(8) for x in range(8))
    return pixels, dhash


def images_under(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in SUFFIXES)


def normalized_name(path: Path) -> str:
    return re.sub(r"^\d+_", "", path.name.casefold())


def audit(reference_root: Path, candidate_root: Path, manifest_path: Path,
          expected_reference_count: int = 422, near_distance: int = 8) -> dict[str, object]:
    if not 0 <= near_distance <= 64:
        raise ValueError("near_distance must be between 0 and 64")
    reference_root, candidate_root = reference_root.resolve(), candidate_root.resolve()
    references = images_under(reference_root)
    candidates = images_under(candidate_root)
    if len(references) != expected_reference_count or not candidates:
        raise ValueError("Reference count mismatch or no candidate images")
    with manifest_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not FIELDS.issubset(reader.fieldnames):
            raise ValueError(f"Manifest requires {', '.join(sorted(FIELDS))}")
        records = list(reader)
    if not records:
        raise ValueError("Candidate manifest is empty")
    candidate_set = set(candidates)
    seen: set[Path] = set()
    sessions: dict[str, set[str]] = {}
    videos: dict[str, set[str]] = {}
    image_rows = []
    reasons = []
    for row in records:
        relative = Path(row["path"])
        path = (candidate_root / relative).resolve()
        if not relative.as_posix() or path not in candidate_set or path in seen:
            raise ValueError(f"Missing, duplicate, or non-image manifest path: {relative}")
        seen.add(path)
        partition = row["partition"].strip()
        if partition not in {"dev", "test"}:
            raise ValueError(f"Invalid partition for {relative}: {partition}")
        try:
            count = int(row["target_count"])
        except ValueError as exc:
            raise ValueError(f"Invalid target count for {relative}") from exc
        if count < 0:
            raise ValueError(f"Negative target count for {relative}")
        actual_sha = digest(path)
        if row["sha256"].strip().lower() != actual_sha:
            raise ValueError(f"Image hash mismatch for {relative}")
        session, video = row["session_id"].strip(), row["source_video_id"].strip()
        if not session or not video:
            reasons.append(f"missing_capture_provenance:{relative.as_posix()}")
        else:
            sessions.setdefault(session, set()).add(partition)
            videos.setdefault(video, set()).add(partition)
        pixel_sha, dhash = fingerprint(path)
        image_rows.append({"path": relative.as_posix(), "partition": partition,
                           "session_id": session, "source_video_id": video,
                           "target_count": count, "sha256": actual_sha,
                           "decoded_sha256": pixel_sha, "dhash": dhash})
    if seen != candidate_set:
        raise ValueError(f"Manifest omits {len(candidate_set - seen)} candidate images")
    if any(len(parts) > 1 for parts in sessions.values()):
        reasons.append("session_shared_between_dev_and_test")
    if any(len(parts) > 1 for parts in videos.values()):
        reasons.append("source_video_shared_between_dev_and_test")
    reference_rows = [(p.relative_to(reference_root).as_posix(), digest(p), *fingerprint(p))
                      for p in references]
    byte_index: dict[str, list[str]] = {}
    pixel_index: dict[str, list[str]] = {}
    name_index: dict[str, list[str]] = {}
    for name, byte_sha, pixel_sha, _ in reference_rows:
        byte_index.setdefault(byte_sha, []).append(name)
        pixel_index.setdefault(pixel_sha, []).append(name)
        name_index.setdefault(normalized_name(Path(name)), []).append(name)
    overlap = []
    near = []
    for row in image_rows:
        for kind, index, value in (("bytes", byte_index, row["sha256"]),
                                   ("decoded_pixels", pixel_index, row["decoded_sha256"]),
                                   ("source_name", name_index, normalized_name(Path(row["path"])))):
            for name in index.get(value, []):
                overlap.append({"candidate": row["path"], "reference": name, "kind": kind})
        for name, _, _, h in reference_rows:
            distance = (row["dhash"] ^ h).bit_count()
            if distance <= near_distance:
                near.append({"candidate": row["path"], "reference": name,
                             "distance": distance, "scope": "KIOS"})
    for i, left in enumerate(image_rows):
        for right in image_rows[i + 1:]:
            if left["partition"] != right["partition"]:
                if left["sha256"] == right["sha256"] or left["decoded_sha256"] == right["decoded_sha256"]:
                    reasons.append("candidate_exact_overlap_between_dev_and_test")
                distance = (left["dhash"] ^ right["dhash"]).bit_count()
                if distance <= near_distance:
                    near.append({"candidate": left["path"], "reference": right["path"],
                                 "distance": distance, "scope": "dev_test"})
    if overlap:
        reasons.append("candidate_overlaps_KIOS")
    if near:
        reasons.append("near_matches_require_manual_review")
    if not any(row["partition"] == "dev" for row in image_rows) or not any(row["partition"] == "test" for row in image_rows):
        reasons.append("both_partitions_required_for_test_admission")
    return {
        "status": "blocked" if reasons else "screened_pending_provenance_ontology_rights_review",
        "candidate_manifest_sha256": digest(manifest_path),
        "reference_count": len(references), "candidate_count": len(image_rows),
        "empty_target_count": sum(row["target_count"] == 0 for row in image_rows),
        "dev_count": sum(row["partition"] == "dev" for row in image_rows),
        "test_count": sum(row["partition"] == "test" for row in image_rows),
        "reasons": sorted(set(reasons)), "exact_overlaps": overlap,
        "near_match_threshold_dhash": near_distance, "near_match_flags": near,
        "images": [{k: v for k, v in row.items() if k != "dhash"} for row in image_rows],
        "limits": "Image screening cannot prove independent capture sessions, class mapping, annotation quality or rights; no detector was run.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-root", type=Path, required=True)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--expected-reference-count", type=int, default=422)
    parser.add_argument("--near-distance", type=int, default=8)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = audit(args.reference_root, args.candidate_root, args.manifest,
                   args.expected_reference_count, args.near_distance)
    output = json.dumps(report, indent=2) + "\n"
    if args.out:
        if args.out.exists():
            raise ValueError("Refusing to overwrite an existing audit report")
        args.out.write_text(output, encoding="utf-8")
    print(output, end="")
    return 2 if report["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
