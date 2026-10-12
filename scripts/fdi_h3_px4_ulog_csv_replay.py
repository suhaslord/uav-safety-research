#!/usr/bin/env python3
"""Replay H3 development CSV directly from immutable PX4 ULog observations.

This checks logged data identity, NOT physical motor identity, actuator thrust,
fault labels, independent dynamics or flight safety.
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

from scripts.fdi_h3_px4_development_trace import FIELDS, MAX_COMMAND_AGE_US
from scripts.fdi_h3_px4_ulog_preflight import ACTUATOR_TOPIC, GYRO_TOPIC


def replay(ulog, csv_text: str) -> dict:
    datasets = {}
    for dataset in ulog.data_list:
        if dataset.name in (GYRO_TOPIC, ACTUATOR_TOPIC):
            datasets.setdefault(dataset.name, []).append(dataset)
    errors = []
    if any(len(datasets.get(name, [])) != 1 for name in (GYRO_TOPIC, ACTUATOR_TOPIC)):
        return {"status": "REJECTED", "errors": ["ambiguous or absent required PX4 ULog topic"],
                "rows_checked": 0, "can_claim_h3_results": False}
    gyro = datasets[GYRO_TOPIC][0].data
    motors = datasets[ACTUATOR_TOPIC][0].data
    try:
        gt = [int(x) for x in gyro["timestamp"]]
        mt = [int(x) for x in motors["timestamp"]]
    except (KeyError, ValueError, TypeError, OverflowError):
        return {"status": "REJECTED", "errors": ["invalid ULog timestamps"],
                "rows_checked": 0, "can_claim_h3_results": False}
    if not gt or not mt:
        return {"status": "REJECTED", "errors": ["empty required ULog topic"],
                "rows_checked": 0, "can_claim_h3_results": False}
    if any(b <= a for times in (gt, mt) for a, b in zip(times, times[1:])):
        return {"status": "REJECTED", "errors": ["nonincreasing ULog timestamps"],
                "rows_checked": 0, "can_claim_h3_results": False}
    start, end = max(gt[0], mt[0]), min(gt[-1], mt[-1])
    if start > end or not any(start <= stamp <= end for stamp in gt):
        return {"status": "REJECTED", "errors": ["no shared gyro/actuator samples"],
                "rows_checked": 0, "can_claim_h3_results": False}
    reader = csv.DictReader(io.StringIO(csv_text))
    if reader.fieldnames != FIELDS:
        return {"status": "REJECTED", "errors": ["unexpected CSV schema"],
                "rows_checked": 0, "can_claim_h3_results": False}
    motor_idx = 0
    count = 0
    for gyro_idx, stamp in enumerate(gt):
        if stamp < start or stamp > end:
            continue
        while motor_idx + 1 < len(mt) and mt[motor_idx + 1] <= stamp:
            motor_idx += 1
        count += 1
        row = next(reader, None)
        if row is None:
            errors.append(f"missing CSV row {count}")
            break
        age = stamp - mt[motor_idx]
        expected_ints = {
            "gyro_log_timestamp_us": stamp,
            "actuator_command_log_timestamp_us": mt[motor_idx],
            "command_age_us": age,
        }
        expected_floats = {
            **{f"gyro_xyz{i}_unmapped_radps": gyro[f"xyz[{i}]"][gyro_idx] for i in range(3)},
            **{f"commanded_actuator_{i}_unmapped": motors[f"control[{i}]"][motor_idx] for i in range(4)},
        }
        if age < 0 or age > MAX_COMMAND_AGE_US:
            errors.append(f"ULog command age outside declared bound at row {count}")
            break
        try:
            for key, value in expected_ints.items():
                if int(row[key]) != value:
                    errors.append(f"row {count} {key} differs from ULog")
            for key, value in expected_floats.items():
                number = float(row[key])
                if not math.isfinite(number) or number != float(value):
                    errors.append(f"row {count} {key} differs from ULog")
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"invalid CSV row {count}: {exc}")
        if len(errors) >= 25:
            break
    if count == 0:
        errors.append("no gyro samples replayed from the shared telemetry window")
    if next(reader, None) is not None:
        errors.append("CSV contains extra rows beyond recorded gyro window")
    return {"study": "FDI-H3", "status": "ULOG_CSV_REPLAY_MATCH" if not errors else "REJECTED",
            "rows_checked": count, "errors": errors, "can_claim_h3_results": False,
            "physical_motor_map_verified": False, "fault_injection_verified": False,
            "note": "Exact replay of ULog topic values and timestamp association only, not a motor-fault trial."}


def audit_zip(path: Path) -> dict:
    # Do not award a successful numerical replay to a bundle with a forged
    # provenance receipt, altered source hash or a rejected development gate.
    from scripts.fdi_h3_development_bundle_audit import audit_bundle
    bundle = audit_bundle(path)
    if bundle["status"] != "CONSISTENT_DEVELOPMENT_ONLY":
        return {"study": "FDI-H3", "status": "REJECTED",
                "errors": ["development evidence bundle failed independent audit",
                           *bundle["errors"]],
                "rows_checked": 0, "can_claim_h3_results": False}
    from pyulog import ULog
    from tempfile import TemporaryDirectory
    with ZipFile(path) as archive:
        raw = archive.read("px4_gazebo_raw.ulg")
        csv_text = archive.read("px4_h3_unmapped.csv").decode("utf-8")
        receipt = json.loads(archive.read("development_receipt.json"))
        raw_sha = hashlib.sha256(raw).hexdigest()
        with TemporaryDirectory() as tmp:
            ulog_path = Path(tmp) / "raw.ulg"
            ulog_path.write_bytes(raw)
            result = replay(ULog(str(ulog_path)), csv_text)
        if receipt.get("raw_ulog_sha256") != raw_sha:
            result["errors"].append("receipt ULog checksum mismatch")
            result["status"] = "REJECTED"
        result["raw_ulog_sha256"] = raw_sha
        return result


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("archive", type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    result = audit_zip(args.archive)
    body = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(body, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(body)
    raise SystemExit(0 if result["status"] == "ULOG_CSV_REPLAY_MATCH" else 2)


if __name__ == "__main__":
    main()
