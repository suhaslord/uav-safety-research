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
import random
import statistics
import zipfile

PROTECTED = (53, 59, 61, 67, 71, 73, 79, 83)
SOURCE = (11, 23, 29, 31)
DEVELOPMENT = (41, 47)
SEEDS = SOURCE + DEVELOPMENT + PROTECTED
QUADRANTS = {(1, 1): 1, (1, -1): 2, (-1, -1): 3, (-1, 1): 4}



def _check_value(name, observed, reported):
    """Check a published numeric endpoint, including undefined metrics."""
    if observed is None:
        if reported is not None:
            raise ValueError(f"{name}: expected null, found {reported!r}")
    elif isinstance(reported, bool) or not isinstance(reported, (int, float)) or not math.isclose(
        observed, reported, rel_tol=1e-10, abs_tol=1e-10
    ):
        raise ValueError(f"{name}: replay gives {observed!r}, report says {reported!r}")


def verify_report_metrics(report, protected):
    """Recompute all reported test endpoints and cluster bootstrap independently.

    The records must already be checked against raw gyro trace replays.
    This routine deliberately accepts imperfect outcomes: an audit should
    expose poor performance, not fail because it assumes 100% accuracy.
    """
    by_seed = {seed: [r for r in protected if r["seed"] == seed] for seed in PROTECTED}
    if any(sorted(r["motor"] for r in rows) != list(range(5)) for rows in by_seed.values()):
        raise ValueError("Protected test must contain each motor condition exactly once per seed")

    def score(records):
        matrix = [[0] * 5 for _ in range(5)]
        for row in records:
            matrix[row["motor"]][row["prediction"]] += 1
        recalls = [matrix[i][i] / sum(matrix[i]) for i in range(5)]
        return sum(recalls) / 5

    confusion = [[0] * 5 for _ in range(5)]
    for row in protected:
        confusion[row["motor"]][row["prediction"]] += 1
    recalls = [confusion[i][i] / sum(confusion[i]) for i in range(5)]
    faults = [r for r in protected if r["motor"] != 0]
    latencies = [r["alert_time_s"] - 10.0 for r in faults
                 if r["prediction"] == r["motor"] and r["alert_time_s"] is not None
                 and r["alert_time_s"] >= 10.0]
    recalculated = {
        "trajectories": len(protected),
        "balanced_accuracy": sum(recalls) / 5,
        "healthy_false_alarm_rate": 1 - recalls[0],
        "fault_detection_rate": sum(r["prediction"] != 0 for r in faults) / len(faults),
        "correct_fault_isolation_rate": sum(r["prediction"] == r["motor"] for r in faults) / len(faults),
        "median_correct_detection_latency_s": statistics.median(latencies) if latencies else None,
    }
    published = report["protected_result"]
    for key, value in recalculated.items():
        _check_value(key, value, published.get(key))
    if published.get("confusion_matrix_rows_true_cols_predicted") != confusion:
        raise ValueError("Published protected confusion matrix disagrees with raw replay")
    for name, recall in zip(("healthy", "motor_1", "motor_2", "motor_3", "motor_4"), recalls):
        _check_value("class_recall." + name, recall, published["class_recall"].get(name))

    # Identical RNG and paired command-seed cluster sampling to frozen
    # evaluator, but independently implemented here.
    bootstrap = report["protected_seed_cluster_bootstrap"]
    if bootstrap.get("random_seed") != 20261012 or bootstrap.get("bootstrap_draws") != 2000:
        raise ValueError("Bootstrap provenance differs from frozen protocol")
    rng = random.Random(20261012)
    draws = []
    for _ in range(2000):
        draw = []
        for __ in PROTECTED:
            draw.extend(by_seed[rng.choice(PROTECTED)])
        draws.append(score(draw))
    draws.sort()

    def percentile(p):
        index = p * (len(draws) - 1)
        low = int(index)
        fraction = index - low
        return draws[low] * (1 - fraction) + draws[min(low + 1, len(draws) - 1)] * fraction

    interval = bootstrap.get("percentile_95_interval")
    if not isinstance(interval, list) or len(interval) != 2:
        raise ValueError("Missing or malformed seed-cluster bootstrap interval")
    for i, expected in enumerate((percentile(.025), percentile(.975))):
        _check_value(f"seed_cluster_bootstrap[{i}]", expected, interval[i])
    _check_value("always_healthy_balanced_accuracy", 0.2,
                 report.get("always_healthy_balanced_accuracy"))
    return confusion, latencies

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
    # Most verification below uses assertions. Never silently skip the evidence
    # checks when invoked using Python's optimized (-O) mode.
    if not __debug__:
        raise RuntimeError("Artifact audit requires assertions enabled; do not use python -O")
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
        assert report.get("protected_test_trajectories") == 40
        assert tuple(report["protected_test_seeds"]) == PROTECTED
        assert tuple(report["source_development_seeds"]) == SOURCE
        assert tuple(report["development_seeds"]) == DEVELOPMENT
        indexed = {(int(row["seed"]), int(row["motor"])): row for row in saved_rows}
        assert len(indexed) == 70
        if len(z.namelist()) != len(set(z.namelist())):
            raise ValueError("Duplicate ZIP members make evidence ambiguous")
        confusion = [[0] * 5 for _ in range(5)]
        successful_fault_alerts = []
        protected_records = []
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
            expected_split = ("protected_test" if seed in PROTECTED else
                              "development" if seed in DEVELOPMENT else
                              "source_development")
            if entry.get("split") != expected_split or saved.get("split") != expected_split:
                raise ValueError(f"Split metadata inconsistent with seed {seed}")
            if saved.get("false_alert_before_onset") != str(timestamp is not None and timestamp < 10.0):
                raise ValueError(f"Pre-onset alert flag disagrees with trace {name}")
            assert int(saved["prediction"]) == pred
            if timestamp is None:
                assert not saved["alert_time_s"] and not saved["alert_altitude_m"]
            else:
                assert math.isclose(float(saved["alert_time_s"]), timestamp, abs_tol=1e-10)
                assert math.isclose(float(saved["alert_altitude_m"]), altitude, abs_tol=1e-10)
            if seed in PROTECTED:
                protected_records.append({"seed": seed, "motor": motor, "prediction": pred,
                                          "alert_time_s": timestamp})
                confusion[motor][pred] += 1
                if motor > 0 and pred == motor:
                    successful_fault_alerts.append((timestamp, altitude))
            checked += 1
        verified_confusion, latencies = verify_report_metrics(report, protected_records)
        assert verified_confusion == confusion
        balanced_accuracy = sum(confusion[k][k] / sum(confusion[k]) for k in range(5)) / 5.0
        lower_bound = 0.025 ** (1 / len(PROTECTED)) if confusion == [[8 if i == j else 0 for j in range(5)] for i in range(5)] else None
        summary = {
            "status": "independently_replayed",
            "files_checked": checked,
            "protected_trajectories": 40,
            "confusion_matrix": confusion,
            "balanced_accuracy": balanced_accuracy,
            "healthy_false_alarms": sum(confusion[0][1:]),
            "correct_fault_isolations": len(successful_fault_alerts),
            "median_correct_fault_detection_latency_seconds": statistics.median(latencies) if latencies else None,
            "detection_altitude_range_m": [min(h for _, h in successful_fault_alerts), max(h for _, h in successful_fault_alerts)] if successful_fault_alerts else None,
            "eight_cluster_all_success_exact_binomial_lower_95pct_if_iid": lower_bound,
            "interpretation": "single simulator, full motor shutdown, fixed onset; not real-world or safety validation"
        }
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
