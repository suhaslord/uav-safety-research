#!/usr/bin/env python3
"""Inspect H3 recorded gyro sample clocks without scoring faults.

The PX4 ULog "vehicle_angular_velocity.timestamp" marks publication;
"timestamp_sample" marks the contributing sensor sample. This read-only
diagnostic keeps those clocks distinct. The actuator stream is commanded
outputs, not measured applied RPM/thrust. It never opens protected H3 data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import operator
import statistics
from bisect import bisect_right
from pathlib import Path

from scripts.fdi_h3_px4_ulog_preflight import GYRO_TOPIC, ACTUATOR_TOPIC

MAX_COMMAND_AGE_US = 100_000


def _timestamps(data, name: str, *, require: bool = True):
    values = data.get(name)
    if values is None:
        if require:
            raise ValueError(f"missing {name}")
        return None
    try:
        stamps = [operator.index(value) for value in values]
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"noninteger {name}") from exc
    if not stamps:
        raise ValueError(f"empty {name}")
    if stamps[0] < 0 or any(right <= left for left, right in zip(stamps, stamps[1:])):
        raise ValueError(f"invalid or nonmonotonic {name}")
    return stamps


def _percentile(values: list[int], fraction: float):
    """Nearest-rank percentile with explicitly declared behavior."""
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * fraction) - 1)
    return ordered[index]


def inspect(ulog, *, source_sha256=None) -> dict:
    errors: list[str] = []
    topics = {}
    for dataset in ulog.data_list:
        if dataset.name in (GYRO_TOPIC, ACTUATOR_TOPIC):
            topics.setdefault(dataset.name, []).append(dataset)
    for name in (GYRO_TOPIC, ACTUATOR_TOPIC):
        if len(topics.get(name, [])) != 1:
            errors.append(f"required topic {name} absent or ambiguous")
    if errors:
        return _report(errors, source_sha256)

    gyro = topics[GYRO_TOPIC][0].data
    commanded = topics[ACTUATOR_TOPIC][0].data
    try:
        publication = _timestamps(gyro, "timestamp")
        sample = _timestamps(gyro, "timestamp_sample")
        motor_publication = _timestamps(commanded, "timestamp")
        if len(publication) != len(sample):
            raise ValueError("gyro publication/sample arrays have different lengths")
        latency = [published - measured for published, measured in zip(publication, sample)]
        if any(delay < 0 for delay in latency):
            raise ValueError("gyro sample timestamp occurs after publication")
        # A motor command can predate this sensor sample without being proof of
        # actuator response. A motor command *after* the sample is never joined.
        paired_ages = []
        preceding_count = 0
        stale_count = 0
        for stamp in sample:
            index = bisect_right(motor_publication, stamp) - 1
            if index < 0:
                continue
            age = stamp - motor_publication[index]
            preceding_count += 1
            paired_ages.append(age)
            if age > MAX_COMMAND_AGE_US:
                stale_count += 1
        if preceding_count == 0:
            raise ValueError("no causally preceding actuator command for gyro sample clock")
    except ValueError as exc:
        return _report([str(exc)], source_sha256)

    result = _report([], source_sha256)
    result.update({
        "status": "SAMPLE_CLOCK_OBSERVED_DEVELOPMENT_ONLY",
        "gyro_rows": len(publication),
        "actuator_command_rows": len(motor_publication),
        "sample_clock": "vehicle_angular_velocity.timestamp_sample",
        "publication_clock": "vehicle_angular_velocity.timestamp",
        "command_clock": "actuator_motors.timestamp",
        "sample_publish_delay_us": {
            "median": statistics.median(latency),
            "p95_nearest_rank": _percentile(latency, 0.95),
            "maximum": max(latency),
        },
        "causal_command_at_gyro_sample": {
            "samples_with_prior_command": preceding_count,
            "samples_without_prior_command": len(sample) - preceding_count,
            "age_median_us": statistics.median(paired_ages),
            "age_p95_us_nearest_rank": _percentile(paired_ages, 0.95),
            "maximum_age_us": max(paired_ages),
            "stale_over_100ms": stale_count,
        },
    })
    return result


def _report(errors: list[str], source_sha256) -> dict:
    return {
        "study": "FDI-H3",
        "status": "REJECTED" if errors else "SAMPLE_CLOCK_OBSERVED_DEVELOPMENT_ONLY",
        "raw_ulog_sha256": source_sha256,
        "errors": errors,
        "can_claim_h3_results": False,
        "physical_motor_map_verified": False,
        "applied_actuation_verified": False,
        "gyro_axis_parity_verified": False,
        "cross_topic_clock_sync_verified": False,
        "fault_injection_verified": False,
        "note": "Publication/sample timestamp integrity and preceding command age "
                "only; sample clocks and commanded outputs cannot establish "
                "actuator physics, coordinate mapping, or H3 fault accuracy.",
    }


def inspect_file(path: Path) -> dict:
    from pyulog import ULog
    candidate = Path(path)
    if candidate.suffix.lower() != ".ulg":
        raise ValueError("Expected existing PX4 .ulg recording")
    digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
    return inspect(ULog(str(candidate)), source_sha256=digest)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ulog", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = inspect_file(args.ulog)
    body = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    print(body, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(body, encoding="utf-8")
    raise SystemExit(0 if report["status"] == "SAMPLE_CLOCK_OBSERVED_DEVELOPMENT_ONLY" else 2)


if __name__ == "__main__":
    main()
