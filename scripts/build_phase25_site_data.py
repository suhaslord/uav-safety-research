#!/usr/bin/env python3
"""Package published Phase 23 aggregates for the Phase 25 stress lens."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPARISON = ROOT / "results/phase23_robust_detector/robustness_comparison.csv"
ROBUST = ROOT / "results/phase23_robust_detector/robustness_metrics.csv"
OUTPUT = ROOT / "deploy/vercel/phase25-explorer-data.json"
CONDITIONS = ("clean", "blur", "low_light", "noise", "occlusion", "mixed")
TITLES = ("Clean", "Blur", "Low light", "Noise", "Occlusion", "Mixed")


def rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        result = list(csv.DictReader(handle))
    by_condition = {row["condition"]: row for row in result}
    if len(result) != len(CONDITIONS) or set(by_condition) != set(CONDITIONS):
        raise ValueError(f"Unexpected condition rows in {path}")
    return by_condition


def render() -> str:
    comparison, robust = rows(COMPARISON), rows(ROBUST)
    data = []
    for key, title in zip(CONDITIONS, TITLES, strict=True):
        left, right = comparison[key], robust[key]
        values = {
            "baseline_map50": float(left["baseline_map50"]),
            "robust_map50": float(left["phase23_map50"]),
            "baseline_recall": float(left["baseline_recall"]),
            "robust_recall": float(left["phase23_recall"]),
        }
        if any(not math.isfinite(value) or not 0 <= value <= 1 for value in values.values()):
            raise ValueError(f"Invalid published metric for {key}")
        if any(abs(values[f"robust_{metric}"] - float(right[metric])) > 1e-12
               for metric in ("map50", "recall")):
            raise ValueError(f"Phase 23 references disagree for {key}")
        image = ROOT / f"deploy/vercel/media/perception/kios_{key}.jpg"
        if not image.is_file():
            raise FileNotFoundError(image)
        data.append({"key": key, "title": title, "illustration": f"/media/perception/kios_{key}.jpg", **values})
    payload = {
        "schema_version": 1,
        "status": "published_aggregates_only",
        "source": "Phase 23 protected condition aggregates; reused in the Phase 24 audit",
        "source_sha256": {
            "comparison": hashlib.sha256(COMPARISON.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
            "robust": hashlib.sha256(ROBUST.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        },
        "illustration_note": "One KIOS frame with the source annotation drawn in blue; never a detector prediction.",
        "conditions": data,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if the packaged site data is stale")
    args = parser.parse_args()
    content = render()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != content:
            raise SystemExit("Phase 25 site aggregates are stale; rerun this script")
        print("Phase 25 site aggregates match the committed references")
    else:
        OUTPUT.write_text(content, encoding="utf-8")
        print(f"Wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
