#!/usr/bin/env python3
"""Export an offline camera reliability demo from frozen, authenticated Phase 25.

This is a retrospective demonstration on previously used images. The code
does not select a threshold, validate new data, or operate an aircraft.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

from scripts.diagnose_phase25_top_confidence import (
    TARGET_CLASS_ID, box, diagnostics, key, rows, update_top,
)

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results/phase25_failure_atlas"
OUT = ROOT / "deploy/vercel/prototype-cases.json"
CONDITIONS = ("clean", "blur", "low_light", "noise", "occlusion", "mixed")
MODELS = ("baseline", "phase23")


def build(results: Path = RESULTS) -> bytes:
    # The existing auditor checks all four original table hashes and reconciles
    # all 1032 rows against frozen predictions, annotations and original metrics.
    detail, summary = diagnostics(results)
    if (summary["status"] != "retrospective_descriptive_only"
            or summary["threshold_selected"] is not False
            or summary["independent_phase26_test_set_used"] is not False
            or len(detail) != 1032 or summary["source_sequences"] != 2):
        raise ValueError("Prototype refuses incomplete or non-retrospective input")

    best = {}
    for row in rows(results / "prediction_boxes.csv"):
        if int(row["class_id"]) == TARGET_CLASS_ID:
            k = key(row)
            best[k] = update_top(best.get(k), {
                "index": int(row["prediction_index"]),
                "confidence": float(row["confidence"]),
                "box": box(row, allow_degenerate=True),
            })
    truth = defaultdict(list)
    for row in rows(results / "ground_truth_targets.csv"):
        if int(row["class_id"]) == TARGET_CLASS_ID:
            truth[key(row)].append(box(row))

    cases = []
    for row in detail:
        k = row["frame_id"], row["condition"], row["model"]
        chosen = best.get(k)
        if ((chosen is None) != (row["top_index"] == "")
                or chosen is not None and (
                    chosen["index"] != row["top_index"]
                    or not math.isclose(chosen["confidence"], row["top_confidence"], abs_tol=1e-12))):
            raise ValueError(f"Top prediction differs from frozen diagnostic: {k}")
        if not truth[k]:
            raise ValueError(f"Missing annotated target: {k}")
        cases.append({
            "frame": row["frame_id"], "condition": row["condition"],
            "model": row["model"], "sequence": row["sequence"],
            "score": row["top_confidence"],
            "top_box": list(chosen["box"]) if chosen else None,
            "top_index": chosen["index"] if chosen else None,
            "truth_boxes": [list(x) for x in truth[k]],
            "top_correct": bool(row["top_correct_iou50"]),
            "top_iou": row["top_best_iou"],
            "any_match_success": bool(row["any_match_frame_success"]),
        })

    counts = {(m, c): [0, 0, 0] for m in MODELS for c in CONDITIONS}
    disagreements = 0
    for item in cases:
        pair = item["model"], item["condition"]
        if pair not in counts:
            raise ValueError(f"Unknown model/condition: {pair}")
        counts[pair][0] += 1
        counts[pair][1] += int(item["any_match_success"])
        counts[pair][2] += int(item["top_correct"])
        disagreements += int(item["any_match_success"] and not item["top_correct"])
    if (disagreements != 135 or any(a[0] != 86 for a in counts.values())
            or counts["phase23", "occlusion"] != [86, 43, 23]
            or counts["phase23", "mixed"] != [86, 44, 22]):
        raise ValueError("Frozen top-prediction results do not reconcile")

    document = {
        "schema": "aegisland.phase25.retrospective-demo.v1",
        "status": "previously_tested_demo_only",
        "new_holdout": False,
        "threshold_selected": False,
        "flight_safety_validated": False,
        "source_frames": 86,
        "source_videos": 2,
        "cases_total": len(cases),
        "any_correct_top_wrong_count": disagreements,
        "source_sha256": summary["input_table_sha256"],
        "models": list(MODELS),
        "conditions": list(CONDITIONS),
        "cases": cases,
    }
    return (json.dumps(document, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=RESULTS)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    generated = build(args.results_dir)
    if args.check:
        if not args.out.is_file() or args.out.read_bytes() != generated:
            parser.error("Demo data missing/stale; reconstruct from frozen inputs")
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(generated)
    print(f"Authenticated demonstration: 1032 cases / 86 reused frames / {len(generated)} bytes")


if __name__ == "__main__":
    main()
