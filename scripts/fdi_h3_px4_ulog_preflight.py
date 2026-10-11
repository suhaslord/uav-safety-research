#!/usr/bin/env python3
"""Read-only PX4 ULog topic preflight for AegisLand H3 (NOT an FDI trial).

Inspects whether a candidate *recorded log* contains gyro p/q and commanded
actuator channels. Does not verify applied motor speed, physical fault
injection, axis mapping, cross-simulator independence, or flight safety.
No camera, controllers, or simulation settings are changed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path

GYRO_TOPIC = "vehicle_angular_velocity"
ACTUATOR_TOPIC = "actuator_motors"
REQUIRED = {
    GYRO_TOPIC: ("xyz[0]", "xyz[1]", "xyz[2]"),
    ACTUATOR_TOPIC: ("control[0]", "control[1]", "control[2]", "control[3]"),
}
MIN_ROWS = 50
MIN_OVERLAP_S = 2.0


def _series(d, field):
    values = d.get(field)
    if values is None:
        raise ValueError(f"missing field {field}")
    return values


def _topic_summary(dataset, required_fields):
    data = dataset.data
    t = _series(data, "timestamp")
    n = len(t)
    result = {
        "topic": dataset.name,
        "instance": getattr(dataset, "multi_id", 0),
        "samples": n,
        "fields_checked": list(required_fields),
        "missing_fields": [f for f in required_fields if f not in data],
        "valid_timestamps": False,
        "finite_required_channels": False,
        "time_span_s": None,
        "median_period_s": None,
        "start_s": None,
        "end_s": None,
    }
    if n < 2:
        return result
    try:
        seconds = [float(x) * 1e-6 for x in t]
        valid_timestamps = all(math.isfinite(x) for x in seconds) and all(
            later > earlier for earlier, later in zip(seconds, seconds[1:])
        )
    except (TypeError, ValueError, OverflowError):
        valid_timestamps = False
    result["valid_timestamps"] = valid_timestamps
    if valid_timestamps:
        result["start_s"] = seconds[0]
        result["end_s"] = seconds[-1]
        result["time_span_s"] = seconds[-1] - seconds[0]
        result["median_period_s"] = statistics.median(
            b - a for a, b in zip(seconds, seconds[1:])
        )
    if not result["missing_fields"]:
        try:
            result["finite_required_channels"] = all(
                len(_series(data, field)) == n and
                all(math.isfinite(float(v)) for v in _series(data, field))
                for field in required_fields
            )
        except (TypeError, ValueError, OverflowError):
            result["finite_required_channels"] = False
    return result


def audit_ulog(ulog, *, input_sha256=None):
    errors = []
    warnings = [
        "Actuator topic represents commanded outputs, NOT independently verified applied motor speed.",
        "Gyro axis sign, body frame, timing synchronization and physical fault-label mapping require external verification.",
        "These checks do not establish simulator independence, fault injection, or an H3 accuracy result.",
    ]
    by_name = {}
    for dataset in ulog.data_list:
        if dataset.name in REQUIRED:
            by_name.setdefault(dataset.name, []).append(dataset)

    topics = {}
    for name, required in REQUIRED.items():
        choices = by_name.get(name, [])
        if not choices:
            errors.append(f"missing required ULog topic {name}")
            continue
        if len(choices) > 1:
            errors.append(f"ambiguous repeated ULog topic {name}: choose and document a specific instance")
            continue
        try:
            summary = _topic_summary(choices[0], required)
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"invalid {name} topic: {exc}")
            continue
        topics[name] = summary
        if summary["samples"] < MIN_ROWS:
            errors.append(f"{name} contains fewer than {MIN_ROWS} samples")
        if summary["missing_fields"]:
            errors.append(f"{name} missing fields: {', '.join(summary['missing_fields'])}")
        if not summary["valid_timestamps"]:
            errors.append(f"{name} has invalid or nonmonotonic microsecond timestamps")
        if not summary["finite_required_channels"]:
            errors.append(f"{name} has missing or nonfinite required channel values")

    if all(name in topics and topics[name]["valid_timestamps"] for name in REQUIRED):
        a, b = (topics[name] for name in (GYRO_TOPIC, ACTUATOR_TOPIC))
        overlap = min(a["end_s"], b["end_s"]) - max(a["start_s"], b["start_s"])
        if overlap < MIN_OVERLAP_S:
            errors.append(f"gyro/actuator topic overlap {overlap:.3f}s is below {MIN_OVERLAP_S:.3f}s")
    else:
        overlap = None

    return {
        "study": "FDI-H3",
        "step": "READ_ONLY_PX4_ULOG_SIGNAL_PREFLIGHT",
        "status": "INCOMPLETE_TELEMETRY" if errors else "READY_FOR_MANUAL_SIGNAL_MAPPING",
        "can_claim_h3_results": False,
        "verified_independent_dynamics": False,
        "fault_injection_verified": False,
        "input_sha256": input_sha256,
        "gyro_actuator_time_overlap_s": overlap,
        "topics": topics,
        "errors": errors,
        "warnings": warnings,
    }


def audit_file(path):
    # pyulog is already used by PX4 Phase 8 tooling, but import lazily so
    # no ULog dependency is required for the synthetic unit tests.
    from pyulog import ULog
    candidate = Path(path)
    if candidate.suffix.lower() != ".ulg":
        raise ValueError("Expected .ulg PX4 ULog input")
    digest = hashlib.sha256()
    with candidate.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return audit_ulog(ULog(str(candidate)), input_sha256=digest.hexdigest())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ulog", type=Path, help="Local PX4 .ulg file (read-only)")
    ap.add_argument("--output", type=Path, help="Optional structured report destination")
    args = ap.parse_args()
    result = audit_file(args.ulog)
    body = json.dumps(result, indent=2, allow_nan=False) + "\n"
    print(body, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(body, encoding="utf-8")
    raise SystemExit(0 if not result["errors"] else 2)


if __name__ == "__main__":
    main()
