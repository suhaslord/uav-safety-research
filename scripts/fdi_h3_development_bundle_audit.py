#!/usr/bin/env python3
"""Reconcile H3 development-only PX4 evidence ZIPs without scoring detector faults.

Internal receipt / CSV consistency is not proof of physically applied motor
signals, motor mapping, sensor axes, independent dynamics or flight safety.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from zipfile import ZipFile

REQUIRED = (
    "development_receipt.json", "mission_metadata.json", "px4_h3_preflight.json",
    "px4_h3_unmapped_metadata.json", "px4_h3_unmapped.csv",
    "px4_gazebo_raw.ulg", "px4_source.env",
)
CSV_FIELDS = (
    "gyro_log_timestamp_us", "actuator_command_log_timestamp_us", "command_age_us",
    "gyro_xyz0_unmapped_radps", "gyro_xyz1_unmapped_radps",
    "gyro_xyz2_unmapped_radps", "commanded_actuator_0_unmapped",
    "commanded_actuator_1_unmapped", "commanded_actuator_2_unmapped",
    "commanded_actuator_3_unmapped",
)


def audit_bundle(path: Path) -> dict:
    errors = []

    def check(ok: bool, message: str) -> None:
        if not ok:
            errors.append(message)

    with ZipFile(path) as archive:
        missing = sorted(set(REQUIRED) - set(archive.namelist()))
        if missing:
            return {
                "status": "REJECTED",
                "errors": [f"missing {name}" for name in missing],
                "can_claim_h3_results": False,
            }
        receipt, mission, preflight, metadata = (
            json.loads(archive.read(name)) for name in REQUIRED[:4]
        )
        digest = hashlib.sha256()
        with archive.open("px4_gazebo_raw.ulg") as raw:
            for chunk in iter(lambda: raw.read(1 << 20), b""):
                digest.update(chunk)
        raw_digest = digest.hexdigest()
        check(receipt.get("raw_ulog_sha256") == raw_digest,
              "raw ULog checksum disagrees with receipt")
        for label, report in (("preflight", preflight), ("export", metadata)):
            check(report.get("input_sha256") == raw_digest,
                  f"{label} source checksum disagrees with raw ULog")
        check(receipt.get("preflight") == preflight,
              "embedded preflight differs from archived preflight")
        check(receipt.get("unmapped_trace_metadata") == metadata,
              "embedded trace metadata differs from archived metadata")
        check(metadata.get("preflight") == preflight,
              "export preflight differs from archived preflight")
        check(receipt.get("mission_metadata") == mission,
              "receipt mission differs from archived mission")
        # New development captures preserve the source-model audit as a separate
        # file. Older sealed development ZIPs remain replayable, but a claimed
        # source gate must have matching evidence and never assert H3 admission.
        if "source_motor_map_audit.json" in archive.namelist():
            source_map = json.loads(archive.read("source_motor_map_audit.json"))
            check(receipt.get("source_motor_map_audit") == source_map,
                  "source motor map receipt differs from archived source audit")
            check(source_map.get("status") == "STATIC_SOURCE_MAP_VERIFIED"
                  and source_map.get("errors") == [],
                  "pinned x500 source motor map gate did not pass")
            for flag in ("can_claim_h3_results", "physical_motor_map_verified",
                         "applied_actuation_verified", "fault_injection_verified"):
                check(source_map.get(flag) is False,
                      f"source motor map audit must explicitly refuse {flag}")
        else:
            check("source_motor_map_audit" not in receipt,
                  "source motor map receipt missing archived source audit")
        check(mission.get("completed") is True and len(mission.get("segments", [])) > 0,
              "simulator mission was not completed")
        check(receipt.get("status") == "DEVELOPMENT_EXPORT_CREATED",
              "receipt must be a completed development export")
        check(preflight.get("status") == "READY_FOR_MANUAL_SIGNAL_MAPPING"
              and preflight.get("errors") == [],
              "preflight did not accept recorded telemetry")
        check(metadata.get("status") == "DEVELOPMENT_ONLY_UNMAPPED",
              "export must remain explicitly unmapped development telemetry")
        check(receipt.get("study") == metadata.get("study") == preflight.get("study") == "FDI-H3",
              "study identity mismatch")
        check(receipt.get("px4_source_id") ==
              archive.read("px4_source.env").decode().strip(),
              "pinned source receipt mismatch")
        for label, report in (("receipt", receipt), ("preflight", preflight),
                              ("export", metadata)):
            for key in ("can_claim_h3_results", "fault_injection_verified"):
                check(report.get(key) is False,
                      f"{label} must explicitly refuse {key}")
        for label, report in (("receipt", receipt), ("export", metadata)):
            for key in ("independent_dynamics_verified", "physical_motor_map_verified"):
                check(report.get(key) is False,
                      f"{label} must explicitly refuse {key}")

        count, max_age, previous_gyro, previous_cmd = 0, -1, -1, -1
        first_gyro, last_gyro = None, None
        with archive.open("px4_h3_unmapped.csv") as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8", newline=""))
            check(tuple(reader.fieldnames or ()) == CSV_FIELDS,
                  "CSV fields must be exactly the ten unscored unmapped channels")
            for row in reader:
                count += 1
                try:
                    gyro = int(row["gyro_log_timestamp_us"])
                    cmd = int(row["actuator_command_log_timestamp_us"])
                    age = int(row["command_age_us"])
                    values = [float(row[field]) for field in CSV_FIELDS[3:]]
                except (KeyError, ValueError, TypeError) as exc:
                    errors.append(f"row {count} invalid numeric field: {exc}")
                    continue
                check(gyro > previous_gyro,
                      f"row {count} nonincreasing gyro timestamp")
                check(cmd >= previous_cmd,
                      f"row {count} decreasing actuator timestamp")
                check(0 <= age <= 100_000 and age == gyro - cmd,
                      f"row {count} future, stale or inconsistent actuator timestamp")
                check(all(math.isfinite(value) for value in values),
                      f"row {count} nonfinite channel value")
                first_gyro = gyro if first_gyro is None else first_gyro
                last_gyro, previous_gyro, previous_cmd = gyro, gyro, cmd
                max_age = max(max_age, age)
        check(count > 0 and count == metadata.get("sample_count"),
              "exported row count mismatch")
        check(count == preflight.get("topics", {}).get(
            "vehicle_angular_velocity", {}).get("overlap_samples"),
            "CSV row count differs from gyro preflight shared-window count")
        check(first_gyro == metadata.get("start_log_timestamp_us")
              and last_gyro == metadata.get("end_log_timestamp_us"),
              "CSV time bounds differ from metadata")
        check(max_age == metadata.get("max_observed_command_age_us"),
              "CSV maximum command age differs from metadata")
        check(metadata.get("max_command_age_limit_us") == 100_000,
              "unexpected maximum command age contract")
    return {
        "study": "FDI-H3",
        "status": "CONSISTENT_DEVELOPMENT_ONLY" if not errors else "REJECTED",
        "raw_ulog_sha256": raw_digest,
        "rows_checked": count,
        "max_command_age_us": max_age,
        "errors": errors,
        "can_claim_h3_results": False,
        "independent_dynamics_verified": False,
        "physical_motor_map_verified": False,
        "fault_injection_verified": False,
        "note": "Internal bundle consistency only; raw ULog to CSV numerical equivalence, motor mapping and H3 trials require further independent validation.",
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("archive", type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    result = audit_bundle(args.archive)
    body = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(body, encoding="utf-8")
    print(body, end="")
    raise SystemExit(0 if result["status"] == "CONSISTENT_DEVELOPMENT_ONLY" else 2)


if __name__ == "__main__":
    main()
