#!/usr/bin/env python3
"""Fail closed if an H3 non-fault PX4 development log lacks dense raw gyro data.

This tests what the logger *recorded*, not the gyroscope's underlying sample
rate. It does not infer source selection, calibration, physical motor mapping,
simulated faults or detector accuracy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from scripts.fdi_h3_px4_raw_gyro_inventory import inventory, timestamps

MIN_RAW_OBSERVATIONS = 200
MAX_RAW_GAP_US = 250_000
MIN_RAW_TO_PROCESSED_RATIO = 0.10


def check_density(ulog, *, source_sha256=None) -> dict:
    base = inventory(ulog, source_sha256=source_sha256)
    errors = list(base["errors"])
    observed = []
    for dataset in ulog.data_list:
        if dataset.name != "sensor_gyro":
            continue
        try:
            times = timestamps(dataset.data, "timestamp_sample")
        except ValueError as exc:
            errors.append(f"raw sensor sample clock invalid: {exc}")
            continue
        longest_gap = max((b - a for a, b in zip(times, times[1:])), default=0)
        observed.append({
            "ulog_instance": getattr(dataset, "multi_id", None),
            "logged_raw_samples": len(times),
            "max_logged_raw_gap_us": longest_gap,
            "fraction_of_processed_samples": (
                len(times) / base["processed_gyro_sample_count"]
                if base.get("processed_gyro_sample_count") else 0
            ),
        })
    if base["status"] != "RAW_GYRO_RECORDED_UNMAPPED":
        errors.append(f"raw gyro inventory not accepted: {base['status']}")
    usable = any(
        row["logged_raw_samples"] >= MIN_RAW_OBSERVATIONS
        and row["max_logged_raw_gap_us"] <= MAX_RAW_GAP_US
        and row["fraction_of_processed_samples"] >= MIN_RAW_TO_PROCESSED_RATIO
        for row in observed
    )
    if not usable:
        errors.append("no recorded sensor_gyro instance meets the frozen density gate")
    return {
        "study": "FDI-H3",
        "status": "DENSE_RAW_GYRO_OBSERVED_DEVELOPMENT_ONLY" if not errors else "REJECTED",
        "raw_ulog_sha256": source_sha256,
        "min_logged_raw_samples": MIN_RAW_OBSERVATIONS,
        "max_allowed_logged_raw_gap_us": MAX_RAW_GAP_US,
        "min_raw_to_processed_ratio": MIN_RAW_TO_PROCESSED_RATIO,
        "processed_gyro_samples": base.get("processed_gyro_sample_count"),
        "raw_instances": observed,
        "errors": errors,
        "raw_sensor_identity_verified": False,
        "gyro_axis_parity_verified": False,
        "cross_topic_clock_sync_verified": False,
        "applied_actuation_verified": False,
        "fault_injection_verified": False,
        "can_claim_h3_results": False,
        "note": "ULog recording density only; not a sample-by-sample sensor mapping or H3 test.",
    }


def check_file(path: Path) -> dict:
    from pyulog import ULog
    path = Path(path)
    if path.suffix.lower() != ".ulg":
        raise ValueError("Expected existing PX4 .ulg recording")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return check_density(ULog(str(path)), source_sha256=digest)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ulog", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = check_file(args.ulog)
    body = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    print(body, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(body, encoding="utf-8")
    raise SystemExit(0 if report["status"] == "DENSE_RAW_GYRO_OBSERVED_DEVELOPMENT_ONLY" else 2)


if __name__ == "__main__":
    main()
