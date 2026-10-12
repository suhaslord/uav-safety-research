#!/usr/bin/env python3
"""Read-only raw PX4 gyroscope topic inventory for H3 development evidence.

Tests which ULog sensor_gyro streams exist, and only whether their logged
sample timestamps precede the processed vehicle_angular_velocity samples.
Does NOT infer selected sensor identity, coordinate/sign equivalence,
applied motor speeds, simulated faults, or H3 protected classification.
"""
from __future__ import annotations

import argparse
from bisect import bisect_right
import hashlib
import json
import math
import operator
from pathlib import Path

RAW = "sensor_gyro"
PROCESSED = "vehicle_angular_velocity"


def timestamps(data: dict, field: str) -> list[int]:
    values = data.get(field)
    if values is None:
        raise ValueError(f"missing {field}")
    try:
        stamps = [operator.index(value) for value in values]
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"invalid noninteger {field}") from exc
    if not stamps or stamps[0] < 0 or any(b <= a for a, b in zip(stamps, stamps[1:])):
        raise ValueError(f"empty, negative or unordered {field}")
    return stamps


def inventory(ulog, *, source_sha256=None) -> dict:
    report = {
        "study": "FDI-H3",
        "raw_ulog_sha256": source_sha256,
        "status": "INCOMPLETE",
        "raw_gyro": [],
        "errors": [],
        "can_claim_h3_results": False,
        "gyro_axis_parity_verified": False,
        "raw_sensor_identity_verified": False,
        "applied_actuation_verified": False,
        "fault_injection_verified": False,
        "note": "Causal timestamp proximity cannot prove downstream source selection, "
                "raw-to-body-frame transform or physical motor mapping.",
    }
    processed = [d for d in ulog.data_list if d.name == PROCESSED]
    if len(processed) != 1:
        report["errors"].append("processed vehicle_angular_velocity topic absent or ambiguous")
        report["status"] = "REJECTED"
        return report
    try:
        ps = timestamps(processed[0].data, "timestamp_sample")
    except ValueError as exc:
        report["errors"].append(f"processed gyro {exc}")
        report["status"] = "REJECTED"
        return report
    report["processed_gyro_sample_count"] = len(ps)
    raw_topics = [d for d in ulog.data_list if d.name == RAW]
    if not raw_topics:
        report["status"] = "RAW_GYRO_NOT_RECORDED"
        return report

    for topic in raw_topics:
        item = {
            "ulog_instance": getattr(topic, "multi_id", None),
            "status": "INCOMPLETE",
        }
        try:
            data = topic.data
            raw_samples = timestamps(data, "timestamp_sample")
            raw_published = timestamps(data, "timestamp")
            if len(raw_samples) != len(raw_published):
                raise ValueError("sample/publish row count differs")
            if any(p < s for p, s in zip(raw_published, raw_samples)):
                raise ValueError("raw sample occurs after publication")
            for axis in ("x", "y", "z"):
                data_axis = data.get(axis)
                if data_axis is None or len(data_axis) != len(raw_samples) or not all(
                    math.isfinite(float(v)) for v in data_axis
                ):
                    raise ValueError(f"missing or nonfinite raw {axis} values")
            ages = []
            for stamp in ps:
                idx = bisect_right(raw_samples, stamp) - 1
                if idx >= 0:
                    ages.append(stamp - raw_samples[idx])
            item.update({
                "status": "RECORDED_UNMAPPED",
                "raw_samples": len(raw_samples),
                "raw_published_samples": len(raw_published),
                "processed_samples_with_preceding_raw_sample": len(ages),
                "max_raw_to_processed_sample_timestamp_gap_us": max(ages) if ages else None,
                "device_ids_observed": sorted(set(int(x) for x in data.get("device_id", []))),
            })
        except (ValueError, TypeError, OverflowError) as exc:
            item["status"] = "REJECTED"
            item["error"] = str(exc)
            report["errors"].append(f"raw gyro instance {item['ulog_instance']}: {exc}")
        report["raw_gyro"].append(item)
    report["status"] = "RAW_GYRO_RECORDED_UNMAPPED" if not report["errors"] else "REJECTED"
    return report


def inventory_file(path: Path):
    from pyulog import ULog
    if Path(path).suffix.lower() != ".ulg":
        raise ValueError("Expected read-only PX4 .ulg recording")
    raw = Path(path).read_bytes()
    return inventory(ULog(str(path)), source_sha256=hashlib.sha256(raw).hexdigest())


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("ulog", type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    result = inventory_file(args.ulog)
    body = json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n"
    print(body, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(body, encoding="utf-8")
    raise SystemExit(2 if result["status"] == "REJECTED" else 0)


if __name__ == "__main__":
    main()
