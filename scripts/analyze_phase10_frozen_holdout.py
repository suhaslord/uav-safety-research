#!/usr/bin/env python3
"""Read-only forensic analysis for the frozen Phase 10 holdout.

This script intentionally contains no tuning, fitting, detector configuration,
or model-selection path. It verifies the frozen evidence hashes and emits
descriptive truth-visible-frame geometry only.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math
from pathlib import Path

EXPECTED = {
    "phase10/per_frame.csv": "bac965f30dd249d271fb7faf3f8c2fc68bd6598957811ebe08eb51714af11486",
    "phase10/result.json": "4a8c3cecc505e136260e9652a6fe937881b6cda1504cf2379d8fa7dc4aad94d6",
    "phase10/result_manifest.json": "6549c3aa5b5da147775b1fc2916c219370b4c15b0a59c715f372ecc3fcffe2c7",
    "analysis/detection_details.csv": "b6cb34f65b75bca54845fee70918db062381bbb4f86b9fa2cca829837ad07283",
    "analysis/perception_trace.csv": "4a65b0c0ea50375213cd113b303d8745f8bb62200fcdafc85bfa3608a4162786",
    "capture/capture_frames.csv": "9b259fb35100c64e7ea8ab8a800cd311450317e2bf032d42b7e95e1bdd829f8a",
    "px4_gazebo_raw.ulg": "e919444c087aa68d2d307b5ef18b78d2af73c2500886c65b0a627be21c0db3ce",
    "px4_mission_metadata.json": "f107ae18bdc9efe0ae0c1e76f2e3c1176583bed4087f1570e2d9254a18cfc09c",
}

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def as_bool(value: str) -> bool:
    return value.strip().lower() in {"true", "1", "yes"}

def category(edge_ratio: float, altitude_m: float) -> str:
    if edge_ratio < 1.0:
        return "truth footprint likely intersects image boundary"
    if edge_ratio < 1.25:
        return "near-boundary geometry"
    if altitude_m < 0.4:
        return "very-near target / extreme scale"
    return "no single geometric boundary flag from trace"

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("artifact_dir", type=Path)
    ap.add_argument("--output", type=Path, default=Path("phase10r_visible_frames.csv"))
    args = ap.parse_args()

    root = args.artifact_dir
    for rel, expected in EXPECTED.items():
        got = sha256(root / rel)
        if got != expected:
            raise SystemExit(f"hash mismatch: {rel}\nexpected {expected}\n     got {got}")

    rows = []
    with (root / "phase10/per_frame.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if not as_bool(row["truth_target_visible"]):
                continue
            width = float(row["image_width_px"])
            height = float(row["image_height_px"])
            cx = float(row["truth_center_x_px"])
            cy = float(row["truth_center_y_px"])
            area = float(row["truth_target_area_px2"])
            altitude = float(row["truth_altitude_m"])
            edge_margin = min(cx, width - cx, cy, height - cy)
            halfside = math.sqrt(area) / 2.0
            ratio = edge_margin / halfside if halfside else math.inf
            rows.append({
                "frame_index": int(row["frame_index"]),
                "t_s": float(row["t_s"]),
                "frame_sha256": row["frame_sha256"],
                "observation_available": as_bool(row["observation_available"]),
                "truth_center_x_px": cx,
                "truth_center_y_px": cy,
                "truth_target_area_px2": area,
                "truth_altitude_m": altitude,
                "edge_margin_px": edge_margin,
                "equiv_halfside_px": halfside,
                "edge_margin_ratio": ratio,
                "descriptive_category": category(ratio, altitude),
            })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    with args.output.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    misses = [r for r in rows if not r["observation_available"]]
    print(json.dumps({
        "evidence_role": "phase10_holdout_seen_forensics",
        "truth_visible_rows": len(rows),
        "visible_misses": len(misses),
        "miss_frame_indices": [r["frame_index"] for r in misses],
        "misses_with_edge_margin_ratio_lt_1": sum(r["edge_margin_ratio"] < 1 for r in misses),
        "model_tuning_performed": False,
    }, indent=2))

if __name__ == "__main__":
    main()
