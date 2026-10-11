#!/usr/bin/env python3
"""Independently replay an H3 PX4 ULog-to-CSV export, without scoring faults.

This read-only check compares *every* exported value and causal timestamp
association to the raw ULog. Passing is evidence of file-level numeric
fidelity, not sensor calibration, physical rotor mapping, or H3 admission.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

GYRO = "vehicle_angular_velocity"
MOTORS = "actuator_motors"
FIELDS = (
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
)
GYRO_FIELDS = tuple(f"xyz[{i}]" for i in range(3))
MOTOR_FIELDS = tuple(f"control[{i}]" for i in range(4))
MAX_COMMAND_AGE_US = 100_000
MAX_ERRORS = 30


def audit_replay(ulog, rows, metadata, *, raw_sha256=None):
    errors = []

    def reject(message):
        if len(errors) < MAX_ERRORS:
            errors.append(message)

    def report(checked=0, max_age=None):
        return {
            "study": "FDI-H3",
            "step": "RAW_ULOG_NUMERICAL_REPLAY",
            "status": "MATCHED_DEVELOPMENT_ONLY" if not errors else "REJECTED",
            "rows_checked": checked,
            "max_observed_command_age_us": max_age,
            "raw_ulog_sha256": raw_sha256,
            "errors": errors,
            "can_claim_h3_results": False,
            "independent_dynamics_verified": False,
            "physical_motor_map_verified": False,
            "fault_injection_verified": False,
            "note": "File-level channel/timestamp agreement only; physical sensor and motor validity not established.",
        }

    if not isinstance(metadata, dict):
        reject("export metadata must be a JSON object")
        return report()
    if metadata.get("status") != "DEVELOPMENT_ONLY_UNMAPPED":
        reject("export is not marked development-only unmapped")
    for field in ("can_claim_h3_results", "independent_dynamics_verified",
                  "physical_motor_map_verified", "fault_injection_verified"):
        if metadata.get(field) is not False:
            reject(f"metadata must explicitly keep {field} false")
    if raw_sha256 is not None and metadata.get("input_sha256") != raw_sha256:
        reject("raw ULog checksum differs from export metadata")

    found = {name: [] for name in (GYRO, MOTORS)}
    for dataset in getattr(ulog, "data_list", ()):
        if dataset.name in found:
            found[dataset.name].append(dataset)
    if any(len(found[name]) != 1 for name in found):
        reject("each required ULog topic must occur exactly once")
        return report()
    g, m = (found[name][0].data for name in (GYRO, MOTORS))
    if any(field not in g for field in ("timestamp", *GYRO_FIELDS)) or any(
        field not in m for field in ("timestamp", *MOTOR_FIELDS)
    ):
        reject("raw ULog lacks required gyro or actuator fields")
        return report()

    try:
        gyro_times = [int(x) for x in g["timestamp"]]
        motor_times = [int(x) for x in m["timestamp"]]
        if not gyro_times or not motor_times:
            raise ValueError("missing timestamp observations")
        for values, converted in ((g["timestamp"], gyro_times),
                                  (m["timestamp"], motor_times)):
            if any(float(x) != t or not math.isfinite(float(x))
                   for x, t in zip(values, converted)):
                raise ValueError("non-integral/nonfinite timestamps")
            if any(a >= b for a, b in zip(converted, converted[1:])):
                raise ValueError("non-monotone raw timestamps")
        for data, names, count in ((g, GYRO_FIELDS, len(gyro_times)),
                                   (m, MOTOR_FIELDS, len(motor_times))):
            for field in names:
                if len(data[field]) != count or not all(
                    math.isfinite(float(value)) for value in data[field]
                ):
                    raise ValueError(f"nonfinite or short raw channel {field}")
    except (TypeError, ValueError, OverflowError) as exc:
        reject(f"invalid source telemetry: {exc}")
        return report()

    if not isinstance(rows, list):
        reject("CSV records must be a list")
        return report()
    if rows and tuple(rows[0]) != FIELDS:
        reject("CSV columns changed from frozen unmapped export")
        return report()
    first = max(gyro_times[0], motor_times[0])
    last = min(gyro_times[-1], motor_times[-1])
    selected = [idx for idx, t in enumerate(gyro_times) if first <= t <= last]
    if not selected:
        reject("no shared raw ULog telemetry window")
        return report()
    if len(rows) != len(selected) or metadata.get("sample_count") != len(selected):
        reject("CSV row count does not match raw gyro shared-window samples")
        return report()
    if (metadata.get("start_log_timestamp_us") != gyro_times[selected[0]]
        or metadata.get("end_log_timestamp_us") != gyro_times[selected[-1]]):
        reject("export time boundaries do not match raw gyro samples")
    if metadata.get("max_command_age_limit_us") != MAX_COMMAND_AGE_US:
        reject("export maximum age contract differs")

    motor_index = 0
    max_age = 0
    checked = 0
    for row, gyro_index in zip(rows, selected):
        sample_time = gyro_times[gyro_index]
        while motor_index + 1 < len(motor_times) and motor_times[motor_index + 1] <= sample_time:
            motor_index += 1
        used_time = motor_times[motor_index]
        age = sample_time - used_time
        if not (0 <= age <= MAX_COMMAND_AGE_US):
            reject(f"row {checked + 1}: raw actuator command is future or stale")
        expected = (
            sample_time, used_time, age,
            *(float(g[name][gyro_index]) for name in GYRO_FIELDS),
            *(float(m[name][motor_index]) for name in MOTOR_FIELDS),
        )
        for column, value in zip(FIELDS, expected):
            try:
                actual = int(row[column]) if column in FIELDS[:3] else float(row[column])
                if not math.isfinite(float(actual)) or actual != value:
                    reject(f"row {checked + 1}: {column} differs from original ULog")
            except (ValueError, TypeError, KeyError, OverflowError) as exc:
                reject(f"row {checked + 1}: invalid {column}: {exc}")
        max_age = max(max_age, age)
        checked += 1
    if metadata.get("max_observed_command_age_us") != max_age:
        reject("recorded maximum command age does not match original ULog")
    return report(checked, max_age)


def audit_files(ulog_path: Path, csv_path: Path, metadata_path: Path):
    from pyulog import ULog  # optional dependency, only for real .ulg files
    if ulog_path.suffix.lower() != ".ulg":
        raise ValueError("input must be an existing .ulg file")
    digest = hashlib.sha256()
    with ulog_path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    with csv_path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError("CSV schema is not the ten raw unmapped H3 columns")
        rows = list(reader)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    return audit_replay(ULog(str(ulog_path)), rows, metadata,
                        raw_sha256=digest.hexdigest())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ulog", type=Path)
    ap.add_argument("--csv", required=True, type=Path)
    ap.add_argument("--metadata", required=True, type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    result = audit_files(args.ulog, args.csv, args.metadata)
    body = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(body, encoding="utf-8")
    print(body, end="")
    raise SystemExit(0 if result["status"] == "MATCHED_DEVELOPMENT_ONLY" else 2)


if __name__ == "__main__":
    main()
