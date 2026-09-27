#!/usr/bin/env python3
"""Freeze a Phase 26 rule from development outcomes only, without opening test outcomes.

The input table is a reviewed evaluation export with path,score,correct columns.
This records a development choice; it is never a test result or admission decision.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from scripts.phase26_reliability import select_development_threshold


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze(manifest_path: Path, screen_path: Path, outcomes_path: Path) -> dict[str, object]:
    screen = json.loads(screen_path.read_text(encoding="utf-8"))
    if screen.get("status") != "screened_pending_provenance_ontology_rights_review":
        raise ValueError("The image screen is blocked or does not have the expected status")
    if screen.get("reference_archive_sha256") != "9d27a3e9616c188fb72a727633705735da5df168ce47efeed389dcb3455fdbdb":
        raise ValueError("Official KIOS reference archive has not been verified")
    if screen.get("candidate_manifest_sha256") != digest(manifest_path):
        raise ValueError("Candidate manifest changed since the image screen")

    with manifest_path.open(newline="", encoding="utf-8") as handle:
        manifest = list(csv.DictReader(handle))
    with outcomes_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if set(reader.fieldnames or ()) != {"path", "score", "correct"}:
            raise ValueError("Development outcome columns must be path,score,correct")
        outcomes = list(reader)
    indexed = {row["path"]: row for row in manifest}
    dev_paths = {row["path"] for row in manifest if row["partition"] == "dev"}
    if len(indexed) != len(manifest) or not dev_paths or not outcomes:
        raise ValueError("Manifest must identify unique development images")
    if len({row["path"] for row in outcomes}) != len(outcomes) or {row["path"] for row in outcomes} != dev_paths:
        raise ValueError("Outcome rows must match development images exactly; test rows are forbidden")

    labeled_scores: list[tuple[float, bool]] = []
    sessions: set[str] = set()
    negative_count = 0
    for row in outcomes:
        source = indexed[row["path"]]
        score = float(row["score"])
        if row["correct"] not in {"0", "1"}:
            raise ValueError("Correctness must be 0 or 1")
        correct = row["correct"] == "1"
        negative = int(source["target_count"]) == 0
        if negative and correct or score == 0 and correct:
            raise ValueError("A negative frame or zero-score miss cannot be a correct localization")
        labeled_scores.append((score, correct))
        sessions.add(source["session_id"])
        negative_count += negative
    choice = select_development_threshold(labeled_scores)
    return {
        "status": "development_only_pending_test_admission",
        "rule": "max_score_of_post_nms_landing_target_boxes_or_zero",
        "primary_outcome": "top_prediction_iou_at_least_0.50",
        "selection": choice,
        "development_images": len(outcomes),
        "development_sessions": len(sessions),
        "development_empty_target_images": negative_count,
        "candidate_manifest_sha256": digest(manifest_path),
        "admission_screen_sha256": digest(screen_path),
        "development_outcomes_sha256": digest(outcomes_path),
        "rule_source_sha256": digest(Path(__file__).with_name("phase26_reliability.py")),
        "test_outcomes_read": False,
        "limits": "This lock records a development choice, not test admission or external reliability. Human provenance, ontology and rights review remain pending.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--screen", type=Path, required=True)
    parser.add_argument("--dev-outcomes", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError("Refusing to overwrite a frozen development choice")
    result = freeze(args.manifest, args.screen, args.dev_outcomes)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote development-only rule lock: {args.out}")


if __name__ == "__main__":
    main()
