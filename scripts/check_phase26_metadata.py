#!/usr/bin/env python3
"""Fast metadata-only Phase 26 preflight; NEVER an independent-data admission.

Checks the manifest's minimum counts, split/session identity, and negative-frame
inventory before the checksum-backed KIOS archive screen. Does not access pixels,
run inference, verify rights, or alter any hash-locked Phase 26 protocol code.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

REQUIRED = {"path", "partition", "session_id", "source_video_id", "target_count", "sha256"}
PARTITIONS = ("dev", "test")
SHA256_HEX = re.compile(r"^[0-9a-fA-F]{64}$")


def preflight(manifest: Path) -> dict[str, object]:
    with manifest.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
            raise ValueError("Manifest requires columns: " + ", ".join(sorted(REQUIRED)))
        rows = list(reader)

    reasons: set[str] = set()
    paths: set[str] = set()
    sessions: dict[str, set[str]] = {}
    videos: dict[str, set[str]] = {}
    hashes: dict[str, set[str]] = {}
    counts = {part: {"images": 0, "empty_target_images": 0} for part in PARTITIONS}

    for index, row in enumerate(rows, 2):
        name = (row.get("path") or "").strip().replace("\\", "/")
        rel = PurePosixPath(name)
        if not name or rel.is_absolute() or ".." in rel.parts or name in paths:
            reasons.add("invalid_or_duplicate_image_path")
        else:
            paths.add(name)

        part = (row.get("partition") or "").strip()
        if part not in PARTITIONS:
            reasons.add("invalid_partition")
            continue
        counts[part]["images"] += 1

        session = (row.get("session_id") or "").strip()
        video = (row.get("source_video_id") or "").strip()
        if not session or not video:
            reasons.add("missing_session_or_video_provenance")
        else:
            sessions.setdefault(session, set()).add(part)
            videos.setdefault(video, set()).add(part)

        target_count = (row.get("target_count") or "").strip()
        try:
            target = int(target_count)
            if target < 0:
                raise ValueError
        except ValueError:
            reasons.add("invalid_target_count")
        else:
            if target == 0:
                counts[part]["empty_target_images"] += 1

        sha = (row.get("sha256") or "").strip().lower()
        if not SHA256_HEX.fullmatch(sha):
            reasons.add("missing_or_invalid_image_sha256")
        else:
            hashes.setdefault(sha, set()).add(part)

    if len(rows) < 30:
        reasons.add("fewer_than_30_candidate_frames")
    if len(sessions) < 2:
        reasons.add("fewer_than_2_documented_sessions")
    if not all(counts[p]["images"] for p in PARTITIONS):
        reasons.add("development_and_test_partitions_required")
    if sum(counts[p]["empty_target_images"] for p in PARTITIONS) == 0:
        reasons.add("no_empty_target_frames")
    if any(len(parts) > 1 for parts in sessions.values()):
        reasons.add("session_shared_between_dev_and_test")
    if any(len(parts) > 1 for parts in videos.values()):
        reasons.add("source_video_shared_between_dev_and_test")
    if any(len(parts) > 1 for parts in hashes.values()):
        reasons.add("image_sha256_shared_between_dev_and_test")

    warnings = [
        f"no_empty_target_frames_in_{part}" for part in PARTITIONS
        if counts[part]["empty_target_images"] == 0
    ]
    return {
        "schema": "aegisland.phase26.metadata-preflight.v1",
        "status": "blocked" if reasons else "metadata_only_ready_for_archive_screen",
        "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "total_images": len(rows),
        "documented_session_ids": len(sessions),
        "counts": counts,
        "reasons": sorted(reasons),
        "warnings": warnings,
        "independent_test_admitted": False,
        "test_detector_inference_authorized": False,
        "limits": (
            "Metadata-only checks. The CSV does not authenticate camera captures, "
            "actual file hashes, independence, annotations, negative labels, rights, "
            "or KIOS duplicates. A non-blocked result is NOT a dataset admission. "
            "Run the frozen archive-backed audit and human review before any test inference."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, help="New JSON report path (never overwritten)")
    args = parser.parse_args()
    report = preflight(args.manifest)
    rendered = json.dumps(report, indent=2) + "\n"
    if args.out:
        with args.out.open("x", encoding="utf-8") as destination:
            destination.write(rendered)
    print(rendered, end="")
    return 2 if report["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
