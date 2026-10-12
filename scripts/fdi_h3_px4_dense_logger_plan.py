#!/usr/bin/env python3
"""Freeze a development-only PX4 SITL logger override for H3 sensor observability.

The pinned PX4 logger replaces (not augments) its default topic profile when
etc/logging/logger_topics.txt is present. The list below deliberately preserves
the channels needed for non-fault sensor/control comparison. It does not
implement motor faults, H3 inference, or a protected test.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

# Topic, minimum log interval in milliseconds. No tuning of the H1/H2 rule.
# sensor_gyro is the raw topic that was only recorded ~once per second in the
# default pinned PX4 logger configuration.
TOPICS = (
    ("sensor_gyro", 10),
    ("vehicle_angular_velocity", 10),
    ("actuator_motors", 20),
    ("sensor_selection", 50),
    ("vehicle_imu", 20),
    ("sensor_combined", 20),
    ("vehicle_attitude", 20),
    ("vehicle_local_position", 20),
    ("vehicle_local_position_groundtruth", 20),
    ("vehicle_angular_velocity_groundtruth", 20),
    ("vehicle_status", 100),
    ("vehicle_land_detected", 100),
    ("vehicle_rates_setpoint", 20),
    ("vehicle_torque_setpoint", 20),
    ("vehicle_thrust_setpoint", 20),
    ("vehicle_control_mode", 100),
)

REQUIRED = {"sensor_gyro", "vehicle_angular_velocity", "actuator_motors",
            "sensor_selection", "vehicle_imu", "vehicle_local_position",
            "vehicle_status", "vehicle_land_detected"}


def plan_text() -> str:
    return (
        "# Development-only H3 sensor observability; replaces PX4 default logger topics.\n"
        "# Frozen PX4 v1.17.0 SITL. Interval units are milliseconds.\n"
        + "".join(f"{topic} {interval}\n" for topic, interval in TOPICS)
    )


def validate_plan(body: str) -> list[str]:
    errors: list[str] = []
    seen: dict[str, int] = {}
    for line in body.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2:
            errors.append(f"invalid logging topic format: {line!r}")
            continue
        topic, interval_text = parts
        try:
            interval = int(interval_text)
            if str(interval) != interval_text or not 0 <= interval <= 100:
                raise ValueError
        except ValueError:
            errors.append(f"invalid log interval for {topic}")
            continue
        if topic in seen:
            errors.append(f"duplicate logged topic: {topic}")
        seen[topic] = interval
    if set(seen) != {name for name, _ in TOPICS}:
        errors.append("missing or unexpected logger topic in frozen development plan")
    if not REQUIRED.issubset(seen):
        errors.append("missing mandatory H3 observability topic")
    if seen.get("sensor_gyro", 10**9) > 10:
        errors.append("raw gyro logging interval must be <=10 ms")
    if seen.get("vehicle_angular_velocity", 10**9) > 10:
        errors.append("processed gyro logging interval must be <=10 ms")
    if seen.get("actuator_motors", 10**9) > 20:
        errors.append("motor command logging interval must be <=20 ms")
    return errors


def write_plan(path: Path, receipt_path: Path) -> dict:
    body = plan_text()
    errors = validate_plan(body)
    if errors:
        raise ValueError("; ".join(errors))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    content = path.read_bytes()
    receipt = {
        "study": "FDI-H3",
        "status": "FROZEN_DEVELOPMENT_LOGGER_PLAN",
        "logger_topic_file_sha256": hashlib.sha256(content).hexdigest(),
        "topic_intervals_ms": dict(TOPICS),
        "replaces_default_px4_topic_profile": True,
        "raw_gyro_coverage_verified": False,
        "can_claim_h3_results": False,
        "fault_injection_verified": False,
        "note": "Source-logging plan only; actual ULog coverage must pass a separate check.",
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    return receipt


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(write_plan(args.output, args.receipt), indent=2))


if __name__ == "__main__":
    main()
