#!/usr/bin/env python3
"""Independent standard-library audit of the frozen H2 Webots artifact ZIP.

Recomputes all decisions from raw CSVs without importing the experiment
evaluator. Does not alter threshold, seeds or the held-out protocol.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import random
import zipfile

SEEDS = (97, 101, 103, 107, 109, 113)
ONSETS = (8., 12.)
LOSSES = (.5, 1.)
NOISE = (0., .5)
QUADRANT = {(1,1):1,(1,-1):2,(-1,-1):3,(-1,1):4}


def name(seed, onset, loss, motor):
    return f"seed{seed}_onset{int(onset)}_loss{int(loss*100):03d}_motor{motor}.csv"


def replay(rows, seed, onset, loss, motor, sigma):
    key = f"aegisland-h2-noise:v1:{seed}:{onset}:{loss}:{motor}:{sigma}"
    rng = random.Random(int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big"))
    run_length = 0
    for row in rows:
        t = float(row["time_s"])
        altitude = float(row["z_m"])
        if t > onset + .70 or (t >= onset and altitude < .50):
            break
        p = float(row["gyro_p_rps"]) + (rng.gauss(0., sigma) if sigma else 0.)
        q = float(row["gyro_q_rps"]) + (rng.gauss(0., sigma) if sigma else 0.)
        run_length = run_length + 1 if abs(p) >= 2. and abs(q) >= .75 else 0
        if run_length >= 3:
            pred = QUADRANT[(1 if p > 0 else -1, 1 if q > 0 else -1)]
            premature = motor > 0 and t < onset
            return (pred, 5 if premature else pred, t, altitude, premature)
    return (0, 0, None, None, False)


def comparison(value, stored):
    if value is None:
        assert stored == "", (value, stored)
    elif isinstance(value, bool):
        assert str(value) == stored
    elif isinstance(value, float):
        assert math.isclose(value, float(stored), abs_tol=1e-9)
    else:
        assert int(stored) == value


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("artifact_zip")
    args = ap.parse_args()
    expected = {name(s,o,0,0) for s in SEEDS for o in ONSETS}
    expected |= {name(s,o,l,m) for s in SEEDS for o in ONSETS for l in LOSSES for m in range(1,5)}
    assert len(expected) == 108
    with zipfile.ZipFile(args.artifact_zip) as z:
        results = json.loads(z.read("report/h2_results.json"))
        saved = list(csv.DictReader(io.StringIO(z.read("report/scenario_predictions.csv").decode())))
        inventory = results["input_manifest"]
        assert {item["filename"] for item in inventory} == expected
        assert len(inventory) == 108
        assert len(saved) == 240
        assert {x[4:] for x in z.namelist() if x.startswith("raw/") and x.endswith(".csv")} == expected
        assert tuple(results["fresh_command_seeds"]) == SEEDS
        assert tuple(results["onsets_s"]) == ONSETS
        assert tuple(results["fault_loss_fractions"]) == LOSSES
        assert tuple(results["offline_gyro_noise_std_rps"]) == NOISE

        rows_by_key = {}
        counts = {}
        for item in inventory:
            file_name = item["filename"]
            data = z.read("raw/" + file_name)
            assert hashlib.sha256(data).hexdigest() == item["sha256"], file_name
            parsed = list(csv.DictReader(io.StringIO(data.decode("utf-8"))))
            assert len(parsed) == item["measurements"]
            seed, onset, loss, motor = (item["seed"], item["onset_s"], item["loss_fraction"], item["motor"])
            assert name(seed, onset, loss, motor) == file_name
            prev = -1.
            for row in parsed:
                time = float(row["time_s"])
                assert math.isfinite(time) and time > prev
                assert int(row["seed"]) == seed and int(row["failed_motor"]) == motor
                assert math.isclose(float(row["fault_onset_s"]), onset, abs_tol=1e-6)
                assert math.isclose(float(row["loss_fraction"]), loss, abs_tol=1e-6)
                assert int(row["fault_active"]) == int(motor != 0 and time >= onset)
                assert all(math.isfinite(float(row[field])) for field in ("gyro_p_rps","gyro_q_rps","z_m"))
                prev = time
            assert prev >= onset + 1.4, file_name
            rows_by_key[(seed,onset,loss,motor)] = parsed
            counts[file_name] = len(parsed)

        seen = set()
        cells = {}
        for row in saved:
            s = int(row["seed"])
            o = float(row["onset_s"])
            l = float(row["loss_fraction"])
            sigma = float(row["noise_std_rps"])
            motor = int(row["truth_motor"])
            assert s in SEEDS and o in ONSETS and l in LOSSES and sigma in NOISE and motor in range(5)
            key = (s,o,l,sigma,motor)
            assert key not in seen, "duplicate scored scenario"
            seen.add(key)
            records = rows_by_key[(s,o,l if motor else 0.,motor)]
            answer = replay(records,s,o,l if motor else 0.,motor,sigma)
            for expected_value,field in zip(answer,("raw_prediction","scored_prediction","alert_time_s","alert_altitude_m","premature")):
                comparison(expected_value,row[field])
            cell=(o,l,sigma)
            if cell not in cells:
                cells[cell] = [[0]*6 for _ in range(5)]
            cells[cell][motor][answer[1]] += 1
        assert len(seen) == 240
        assert len(cells) == 8
        def balanced(matrix):
            return sum(matrix[i][i] / sum(matrix[i]) for i in range(5)) / 5

        for result in results["factorial_results"]:
            cell=(result["onset_s"],result["loss_fraction"],result["noise_std_rps"])
            assert result["confusion_matrix_rows_truth_cols_healthy_m1_m2_m3_m4_premature"] == cells[cell]
            assert math.isclose(result["balanced_accuracy"],balanced(cells[cell]),abs_tol=1e-12)
        pooled = [[sum(cells[(o,.5,.5)][i][j] for o in ONSETS) for j in range(6)] for i in range(5)]
        assert pooled == results["primary_result"]["confusion_matrix_rows_truth_cols_healthy_m1_m2_m3_m4_premature"]
        assert math.isclose(balanced(pooled),results["primary_result"]["balanced_accuracy"],abs_tol=1e-12)
        assert results["physical_simulations"] == 108
        assert results["repeated_scenario_observations"] == 240
        print(json.dumps({
            "status": "PASS",
            "raw_simulator_csv_hashes_verified": len(counts),
            "recomputed_scenario_decisions": len(seen),
            "primary_balanced_accuracy": balanced(pooled),
            "primary_confusion_matrix": pooled,
            "eight_factorial_cells": {
                f"onset={o},loss={l},noise={n}": balanced(cells[(o,l,n)])
                for o in ONSETS for l in LOSSES for n in NOISE
            },
            "scientific_scope": "within-simulator partial-loss and noisy-observation sensitivity; not real flight"
        }, indent=2))


if __name__ == "__main__":
    main()
