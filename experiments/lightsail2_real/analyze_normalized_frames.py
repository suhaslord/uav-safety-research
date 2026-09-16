#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path
from typing import Any


def flatten_numeric(prefix: str, value: Any, out: dict[str, float]) -> None:
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        out[prefix] = float(value)
    elif isinstance(value, dict):
        for key, child in value.items():
            name = f"{prefix}.{key}" if prefix else str(key)
            flatten_numeric(name, child, out)
    elif isinstance(value, list) and len(value) <= 8:
        for i, child in enumerate(value):
            name = f"{prefix}[{i}]"
            flatten_numeric(name, child, out)


def persistent_flags(values: list[float | None], train_fraction: float = 0.6, z: float = 3.0, persistence: int = 2) -> tuple[list[bool], float, float]:
    cut = max(3, int(len(values) * train_fraction))
    train = [x for x in values[:cut] if x is not None and math.isfinite(x)]
    if len(train) < 3:
        return [False] * len(values), float("nan"), float("nan")
    mu = statistics.fmean(train)
    sigma = statistics.pstdev(train)
    if not math.isfinite(sigma) or sigma <= 0:
        return [False] * len(values), mu, sigma
    raw = [False if x is None else abs(x - mu) / sigma > z for x in values]
    flags = [False] * len(values)
    streak = 0
    for i, is_raw in enumerate(raw):
        streak = streak + 1 if is_raw else 0
        flags[i] = streak >= persistence
    return flags, mu, sigma


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input_json", type=Path)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    data = json.loads(args.input_json.read_text(encoding="utf-8"))
    frames = data.get("frames", data if isinstance(data, list) else [])
    if not isinstance(frames, list) or not frames:
        raise SystemExit("no frames found")

    rows: list[dict[str, Any]] = []
    all_keys: set[str] = set()
    for frame in frames:
        numeric: dict[str, float] = {}
        if isinstance(frame, dict):
            flatten_numeric("", frame.get("fields", frame), numeric)
            time = frame.get("time") or frame.get("timestamp") or frame.get("datetime") or ""
        else:
            time = ""
        numeric["__frame_index"] = float(len(rows))
        row: dict[str, Any] = {"time": time, **numeric}
        rows.append(row)
        all_keys.update(numeric)

    keys = sorted(k for k in all_keys if k != "__frame_index")
    summaries: list[dict[str, Any]] = []
    anomaly_rows: list[dict[str, Any]] = []
    for key in keys:
        values = [float(r[key]) if key in r else None for r in rows]
        present = [v for v in values if v is not None and math.isfinite(v)]
        if len(present) < max(20, int(0.25 * len(rows))):
            continue
        flags, mu, sigma = persistent_flags(values)
        count = sum(flags)
        summaries.append({
            "field": key,
            "samples": len(present),
            "coverage": len(present) / len(rows),
            "train_mean": mu,
            "train_sigma": sigma,
            "persistent_z3_alert_samples": count,
            "alert_fraction": count / len(rows),
            "min": min(present),
            "max": max(present),
        })
        for i, flag in enumerate(flags):
            if flag:
                anomaly_rows.append({
                    "frame_index": i,
                    "time": rows[i].get("time", ""),
                    "field": key,
                    "value": values[i],
                    "train_mean": mu,
                    "train_sigma": sigma,
                    "z_abs": abs((values[i] - mu) / sigma) if sigma and math.isfinite(sigma) else "",
                })

    summaries.sort(key=lambda r: (-r["persistent_z3_alert_samples"], r["field"]))
    with (args.out_dir / "field_summary.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(summaries[0].keys()))
        writer.writeheader(); writer.writerows(summaries)
    with (args.out_dir / "persistent_anomalies.csv").open("w", newline="", encoding="utf-8") as fh:
        fieldnames = ["frame_index", "time", "field", "value", "train_mean", "train_sigma", "z_abs"]
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader(); writer.writerows(anomaly_rows)

    times = [str(r.get("time", "")) for r in rows if r.get("time")]
    top = summaries[:15]
    report = [
        "# LightSail 2 normalized telemetry — real-data baseline",
        "",
        f"- Frames: **{len(rows)}**",
        f"- Numeric fields with sufficient coverage: **{len(summaries)}**",
        f"- First timestamp: `{times[0] if times else 'unknown'}`",
        f"- Last timestamp: `{times[-1] if times else 'unknown'}`",
        f"- Persistent 3σ alert samples across fields: **{len(anomaly_rows)}**",
        "",
        "Method: for each sufficiently populated numeric field, fit mean/std on the first 60% of frames and flag only values beyond 3σ for at least two consecutive samples. This matches the simple Gaussian+persistence baseline used in the earlier parser smoke test; it is an exploratory anomaly screen, not a labeled fault detector.",
        "",
        "## Fields with the most persistent alerts",
        "",
        "| field | samples | alerts | alert fraction | min | max |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in top:
        report.append(f"| `{r['field']}` | {r['samples']} | {r['persistent_z3_alert_samples']} | {r['alert_fraction']:.4f} | {r['min']:.6g} | {r['max']:.6g} |")
    report += [
        "",
        "## Interpretation boundary",
        "",
        "This uses the public normalized LightSail-2 telemetry mirror in jschloemer/satellite-data-repo. It does not substitute for the Planetary Society raw beacon archive, and alerts are statistical outliers only; without ground-truth event labels they must not be called spacecraft faults.",
    ]
    (args.out_dir / "REAL_DATA_RESULTS.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print((args.out_dir / "REAL_DATA_RESULTS.md").read_text())


if __name__ == "__main__":
    main()
