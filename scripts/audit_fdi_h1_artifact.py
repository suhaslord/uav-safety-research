#!/usr/bin/env python3
"""Independently audit a downloaded AegisLand FDI-H1 artifact ZIP.

Uses only Python's standard library; recomputes early alerts directly from raw
gyro measurements, validates SHA256 provenance and compares saved predictions.
Does not train a model or modify the frozen threshold/holdout split.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import math
import statistics
import zipfile

PROTECTED = (53, 59, 61, 67, 71, 73, 79, 83)
SOURCE = (11, 23, 29, 31)
DEVELOPMENT = (41, 47)
SEEDS = SOURCE + DEVELOPMENT + PROTECTED
QUADRANTS = {(1, 1): 1, (1, -1): 2, (-1, -1): 3, (-1, 1): 4}


def decision(rows):
    streak = 0
    for row in rows:
        time = float(row["time_s"])
        altitude = float(row["z_m"])
        if time > 10.70 or (time >= 10.0 and altitude < 0.50):
            break
        p = float(row["gyro_p_rps"])
        q = float(row["gyro_q_rps"])
        streak = streak + 1 if abs(p) >= 2.0 and abs(q) >= 0.75 else 0
        if streak >= 3:
            return QUADRANTS[(1 if p > 0 else -1, 1 if q > 0 else -1)], time, altitude
    return 0, None, None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_zip", help="ZIP uploaded by GitHub Actions FDI early pre-contact validation")
    args = parser.parse_args()
    with zipfile.ZipFile(args.artifact_zip) as z:
        report = json.loads(z.read("report/heldout_results.json"))
        saved_rows = list(csv.DictReader(io.StringIO(z.read("report/trajectory_decisions.csv").decode())))
        manifest = report["input_manifest"]
        expected = {f"seed{s}_motor{m}.csv" for s in SEEDS for m in range(5)}
        assert len(manifest) == len(expected) == 70
        assert len(saved_rows) == 70
        assert {entry["file"] for entry in manifest} == expected
        assert {name[4:] for name in z.namelist() if name.startswith("raw/") and name.endswith(".csv")} == expected
        assert tuple(report["protected_test_seeds"]) == PROTECTED
        assert tuple(report["source_development_seeds"]) == SOURCE
        assert tuple(report["development_seeds"]) == DEVELOPMENT
        indexed = {(int(row["seed"]), int(row["motor"])): row for row in saved_rows}
        assert len(indexed) == 70
        confusion = [[0] * 5 for _ in range(5)]
        successful_fault_alerts = []
        checked = 0
        for entry in manifest:
            name = entry["file"]
            contents = z.read("raw/" + name)
            assert hashlib.sha256(contents).hexdigest() == entry["sha256"], name
            seed = int(name.split("_")[0][4:])
            motor = int(name.split("_")[1][5:-4])
            rows = list(csv.DictReader(io.StringIO(contents.decode())))
            assert len(rows) == int(entry["rows"]) >= 700
            times = [float(row["time_s"]) for row in rows]
            assert all(math.isfinite(t) for t in times)
            assert all(b > a for a, b in zip(times, times[1:]))
            assert times[-1] >= 22
            for row in rows:
                t = float(row["time_s"])
                assert int(row["seed"]) == seed
                assert int(row["failed_motor"]) == motor
                assert int(row["fault_active"]) == int(motor > 0 and t >= 10.0)
                assert all(math.isfinite(float(row[key])) for key in ("z_m", "gyro_p_rps", "gyro_q_rps"))
            pred, timestamp, altitude = decision(rows)
            saved = indexed[(seed, motor)]
            assert int(saved["prediction"]) == pred
            if timestamp is None:
                assert not saved["alert_time_s"] and not saved["alert_altitude_m"]
            else:
                assert math.isclose(float(saved["alert_time_s"]), timestamp, abs_tol=1e-10)
                assert math.isclose(float(saved["alert_altitude_m"]), altitude, abs_tol=1e-10)
            if seed in PROTECTED:
                confusion[motor][pred] += 1
                if motor > 0 and pred == motor:
                    successful_fault_alerts.append((timestamp, altitude))
            checked += 1
        recalls = [confusion[k][k] / sum(confusion[k]) for k in range(5)]
        balanced_accuracy = sum(recalls) / 5.0
        assert math.isclose(balanced_accuracy, report["protected_result"]["balanced_accuracy"])
        assert confusion == report["protected_result"]["confusion_matrix_rows_true_cols_predicted"]
        assert len(successful_fault_alerts) == 32
        assert report["protected_result"]["trajectories"] == 40
        lower_bound = 0.025 ** (1 / len(PROTECTED)) if confusion == [[8 if i == j else 0 for j in range(5)] for i in range(5)] else None
        summary = {
            "status": "independently_replayed",
            "files_checked": checked,
            "protected_trajectories": 40,
            "confusion_matrix": confusion,
            "balanced_accuracy": balanced_accuracy,
            "healthy_false_alarms": sum(confusion[0][1:]),
            "correct_fault_isolations": len(successful_fault_alerts),
            "median_correct_fault_detection_latency_seconds": statistics.median(t - 10.0 for t, _ in successful_fault_alerts),
            "detection_altitude_range_m": [min(h for _, h in successful_fault_alerts), max(h for _, h in successful_fault_alerts)],
            "eight_cluster_all_success_exact_binomial_lower_95pct_if_iid": lower_bound,
            "interpretation": "single simulator, full motor shutdown, fixed onset; not real-world or safety validation"
        }
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
