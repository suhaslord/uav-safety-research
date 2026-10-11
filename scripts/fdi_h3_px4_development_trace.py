#!/usr/bin/env python3
"""Read-only PX4 H3 *development* trace export; never scores motor faults.

Preserves the raw gyroscope log timestamps and associates only previously
observed actuator commands. The output is an instrumentation diagnostic, NOT
an admitted H3 experiment, proof of applied thrust, or a flight safety tool.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from scripts.fdi_h3_px4_ulog_preflight import (
    ACTUATOR_TOPIC,
    GYRO_TOPIC,
    audit_ulog,
)

MAX_COMMAND_AGE_US = 100_000

FIELDS = [
    "gyro_log_timestamp_us",
    "actuator_command_log_timestamp_us",
    "command_age_us",
    "gyro_xyz0_unmapped_radps",
    "gyro_xyz1_unmapped_radps",
    "gyro_xyz2_unmapped_radps",
    "commanded_actuator_0_unmapped",
    "commanded_actuator_1_unmapped",
    "commanded_actuator_2_unmapped",
    "commanded_actuator_3_unmapped",
]


def make_development_trace(ulog, *, input_sha256=None):
    preflight = audit_ulog(ulog, input_sha256=input_sha256)
    if preflight["errors"]:
        raise ValueError("PX4 ULog preflight rejected: " + "; ".join(preflight["errors"]))

    # The preflight rejects repeated topic instances; the two reads here are
    # therefore unambiguous. Neither physical motor mapping nor sign is assumed.
    datasets = {dataset.name: dataset for dataset in ulog.data_list
                if dataset.name in (GYRO_TOPIC, ACTUATOR_TOPIC)}
    g, m = datasets[GYRO_TOPIC].data, datasets[ACTUATOR_TOPIC].data
    g_times = [int(t) for t in g["timestamp"]]
    m_times = [int(t) for t in m["timestamp"]]
    start_us = max(g_times[0], m_times[0])
    end_us = min(g_times[-1], m_times[-1])
    motor_index = 0
    rows = []

    for i, stamp in enumerate(g_times):
        if not start_us <= stamp <= end_us:
            continue
        while (motor_index + 1 < len(m_times)
               and m_times[motor_index + 1] <= stamp):
            motor_index += 1
        used_stamp = m_times[motor_index]
        if used_stamp > stamp:
            raise ValueError("Cannot associate a future actuator command with a gyro sample")
        age = stamp - used_stamp
        if age > MAX_COMMAND_AGE_US:
            raise ValueError(
                f"Actuator command was stale by {age}us at gyro timestamp "
                f"{stamp}us (limit {MAX_COMMAND_AGE_US}us); refusing to fill gap"
            )
        rows.append({
            "gyro_log_timestamp_us": stamp,
            "actuator_command_log_timestamp_us": used_stamp,
            "command_age_us": age,
            "gyro_xyz0_unmapped_radps": float(g["xyz[0]"][i]),
            "gyro_xyz1_unmapped_radps": float(g["xyz[1]"][i]),
            "gyro_xyz2_unmapped_radps": float(g["xyz[2]"][i]),
            **{f"commanded_actuator_{axis}_unmapped": float(
                m[f"control[{axis}]"][motor_index]
            ) for axis in range(4)},
        })
    if not rows:
        raise ValueError("No observed gyroscope samples within shared PX4 telemetry window")

    metadata = {
        "study": "FDI-H3",
        "step": "PX4_DEVELOPMENT_ONLY_UNMAPPED_EXPORT",
        "status": "DEVELOPMENT_ONLY_UNMAPPED",
        "can_claim_h3_results": False,
        "independent_dynamics_verified": False,
        "fault_injection_verified": False,
        "physical_motor_map_verified": False,
        "sample_count": len(rows),
        "input_sha256": input_sha256,
        "start_log_timestamp_us": rows[0]["gyro_log_timestamp_us"],
        "end_log_timestamp_us": rows[-1]["gyro_log_timestamp_us"],
        "max_command_age_limit_us": MAX_COMMAND_AGE_US,
        "max_observed_command_age_us": max(row["command_age_us"] for row in rows),
        "time_basis": "PX4 ULog topic timestamp (publish/log timestamp), not timestamp_sample",
        "raw_channels": {
            "gyro": "vehicle_angular_velocity.xyz[0..2], axes/sign NOT externally verified",
            "motors": "actuator_motors.control[0..3], commands NOT measured applied speed",
        },
        "preflight": preflight,
        "limitations": [
            "No event, motor identity, fault labels, or detector predictions are inferred.",
            "No calibration or coordinate transform has been applied to logged body axes.",
            "A logged actuator command is not proof of applied motor speed or fault injection.",
            "Manual simulator-source, timestamp_sample, and motor-index verification remain mandatory.",
        ],
    }
    return rows, metadata


def export_file(path: Path, csv_path: Path, metadata_path: Path):
    if path.suffix.lower() != ".ulg":
        raise ValueError("Expected existing PX4 .ulg recording")
    from pyulog import ULog  # Optional dependency, only needed for real log input.

    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    rows, metadata = make_development_trace(
        ULog(str(path)), input_sha256=digest.hexdigest()
    )
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ulog", type=Path, help="Existing PX4 ULog, never flown/modified")
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    args = parser.parse_args()
    metadata = export_file(args.ulog, args.csv, args.metadata)
    print(json.dumps({
        "status": metadata["status"],
        "rows": metadata["sample_count"],
        "source_sha256": metadata["input_sha256"],
        "can_claim_h3_results": False,
    }, indent=2))


if __name__ == "__main__":
    main()
