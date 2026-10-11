#!/usr/bin/env python3
"""Preregistered, NO-TUNING FDI-H2 scorecard for separate Webots motor stress traces."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import os
import random
import statistics
from pathlib import Path

SEEDS = (89, 97, 101, 103, 107, 109, 113, 127)
ONSETS = (9.0, 13.0)
RETENTIONS = (0.0, 0.5)
NOISE_SIGMAS = (0.0, 0.2, 1.0)
P_LIMIT = 2.0
Q_LIMIT = 0.75
STREAK = 3
ALT_LIMIT = 0.50
DETECTION_WINDOW_S = 0.70
MOTOR_BY_SIGNS = {(1, 1): 1, (1, -1): 2, (-1, -1): 3, (-1, 1): 4}
DATA_FIELDS = ("time_s","x_m","y_m","z_m","gyro_p_rps","gyro_q_rps","gyro_r_rps",
               "cmd_m1","cmd_m2","cmd_m3","cmd_m4")


def file_name(seed, onset, motor, retention):
    return f"seed{seed}_onset{int(onset)}_motor{motor}_keep{int(round(100*retention))}.csv"


def scenario_cases():
    for seed in SEEDS:
        for onset in ONSETS:
            yield seed, onset, 0, 1.0
            for retention in RETENTIONS:
                for motor in range(1, 5):
                    yield seed, onset, motor, retention


def hash_file(path):
    digest=hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda:fh.read(1024*1024),b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_trace(path, seed, onset, motor, retention):
    with path.open(newline="", encoding="utf-8") as fh:
        rows=list(csv.DictReader(fh))
    if len(rows)<220:
        raise ValueError(f"{path.name}: truncated trajectory ({len(rows)} rows)")
    prev=-math.inf
    seen_after_onset=False
    for i,row in enumerate(rows):
        try:
            t=float(row["time_s"])
            expected_label=int(motor>0 and t>=onset)
            if (int(row["seed"])!=seed or int(row["failed_motor"])!=motor
                or float(row["fault_onset_s"])!=onset
                or float(row["motor_retention"])!=retention
                or int(row["fault_active"])!=expected_label):
                raise ValueError("scenario label mismatch")
            if not math.isfinite(t) or t<=prev:
                raise ValueError("non-increasing time")
            prev=t
            if t>=onset: seen_after_onset=True
            # Only simulated interval used by the rule is validated for finite signals.
            # Late data must not influence this score.
            if t<=onset+DETECTION_WINDOW_S:
                for field in DATA_FIELDS:
                    if not math.isfinite(float(row[field])):
                        raise ValueError(f"nonfinite telemetry {field}")
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError(f"{path.name}: invalid row {i}: {exc}") from exc
    if not seen_after_onset or prev<onset+DETECTION_WINDOW_S:
        raise ValueError(f"{path.name}: did not cover early-response evaluation interval")
    return rows


def noise_rng(seed,onset,motor,retention,sigma):
    key=f"FDI-H2:20261011:{seed}:{int(onset)}:{motor}:{retention:.1f}:{sigma:.1f}"
    val=int.from_bytes(hashlib.sha256(key.encode("ascii")).digest()[:8],"big")
    return random.Random(val)


def classify(rows, onset, sigma, rng):
    streak=0
    for row in rows:
        t=float(row["time_s"])
        if t>onset+DETECTION_WINDOW_S:
            break
        z=float(row["z_m"])
        if t>=onset and z<ALT_LIMIT:
            break
        # Noise is applied offline, identically specified before any H2 result.
        p=float(row["gyro_p_rps"])
        q=float(row["gyro_q_rps"])
        if sigma:
            p+=rng.gauss(0,sigma)
            q+=rng.gauss(0,sigma)
        streak=streak+1 if abs(p)>=P_LIMIT and abs(q)>=Q_LIMIT else 0
        if streak>=STREAK:
            return {"prediction":MOTOR_BY_SIGNS[(1 if p>0 else -1,1 if q>0 else -1)],
                    "alert_time_s":t,"alert_altitude_m":z,
                    "pre_onset":t<onset}
    return {"prediction":0,"alert_time_s":None,"alert_altitude_m":None,
            "pre_onset":False}


def measure(records):
    if not records:
        raise ValueError("Empty score set")
    matrix=[[0]*5 for _ in range(5)]
    class_totals=[0]*5
    class_success=[0]*5
    valid_delays=[]
    preonset_count=0
    for record in records:
        truth=record["motor"]
        predicted=record["prediction"]
        pre=record["pre_onset"]
        class_totals[truth]+=1
        matrix[truth][predicted]+=1
        # A premature prediction matching the eventual fault class is NOT success.
        success=truth==predicted and not pre
        class_success[truth]+=int(success)
        preonset_count+=int(pre)
        if truth>0 and success and record["alert_time_s"] is not None:
            valid_delays.append(record["alert_time_s"]-record["onset"])
    if any(count==0 for count in class_totals):
        raise ValueError("Metric requires all five true classes")
    faulted=[r for r in records if r["motor"]>0]
    recalls=[s/t for s,t in zip(class_success,class_totals)]
    return {
        "traces":len(records),
        "temporal_valid_balanced_accuracy":sum(recalls)/5,
        "class_temporally_valid_recall":dict(zip(("healthy","motor_1","motor_2","motor_3","motor_4"),recalls)),
        "healthy_false_alarm_rate":1-recalls[0],
        "fault_detected_rate":sum(r["prediction"]>0 and not r["pre_onset"] for r in faulted)/len(faulted),
        "correct_motor_isolation_rate":sum(r["motor"]==r["prediction"] and not r["pre_onset"] for r in faulted)/len(faulted),
        "premature_alert_count":preonset_count,
        "median_correct_detection_latency_s":statistics.median(valid_delays) if valid_delays else None,
        "confusion_matrix_rows_truth_cols_prediction":matrix,
    }


def bootstrap(rows):
    groups={seed:[r for r in rows if r["seed"]==seed] for seed in SEEDS}
    if any(not value for value in groups.values()):
        raise ValueError("Missing paired seed for bootstrap")
    rng=random.Random(20261013)
    nums=[]
    for _ in range(2000):
        sampled=[r for __ in SEEDS for r in groups[rng.choice(SEEDS)]]
        nums.append(measure(sampled)["temporal_valid_balanced_accuracy"])
    nums.sort()
    def pct(x):
        j=x*(len(nums)-1)
        index=int(j)
        w=j-index
        return nums[index]*(1-w)+nums[min(index+1,len(nums)-1)]*w
    return {"resampling_unit":"command seed (all motors, onset and retention paired)",
            "seed_count":len(SEEDS),"bootstrap_draws":2000,"seed":20261013,
            "percentile_95_interval":[pct(.025),pct(.975)]}


def subset(rows,retention,onset=None,noise=None):
    return [r for r in rows if (r["motor"]==0 or r["retention"]==retention)
            and (onset is None or r["onset"]==onset)
            and (noise is None or r["sensor_noise_sigma_radps"]==noise)]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-dir",type=Path,required=True)
    ap.add_argument("--output-dir",type=Path,required=True)
    args=ap.parse_args()
    expected={file_name(*case) for case in scenario_cases()}
    actual={p.name for p in args.input_dir.glob("*.csv")}
    if actual!=expected:
        raise ValueError(f"Missing {sorted(expected-actual)}; extra {sorted(actual-expected)}")
    args.output_dir.mkdir(parents=True,exist_ok=True)
    decisions=[]
    manifest=[]
    for seed,onset,motor,retention in scenario_cases():
        path=args.input_dir/file_name(seed,onset,motor,retention)
        trace=load_trace(path,seed,onset,motor,retention)
        manifest.append({"file":path.name,"sha256":hash_file(path),"rows":len(trace),
                         "seed":seed,"onset":onset,"motor":motor,"retention":retention})
        for noise in NOISE_SIGMAS:
            decision=classify(trace,onset,noise,noise_rng(seed,onset,motor,retention,noise))
            decisions.append({"seed":seed,"onset":onset,"motor":motor,"retention":retention,
                              "sensor_noise_sigma_radps":noise,**decision})
    with (args.output_dir/"per_case_decisions.csv").open("w",newline="",encoding="utf-8") as fh:
        writer=csv.DictWriter(fh,fieldnames=list(decisions[0]))
        writer.writeheader()
        writer.writerows(decisions)
    groups={}
    for sigma in NOISE_SIGMAS:
        for keep in RETENTIONS:
            rows=subset(decisions,keep,noise=sigma)
            tag=f"retain_{int(keep*100)}_noise_{str(sigma).replace('.','p')}"
            groups[tag]={"metrics":measure(rows),"seed_cluster_bootstrap":bootstrap(rows),
                         "by_onset":{str(int(onset)):measure(subset(rows,keep,onset=onset))
                                     for onset in ONSETS}}
    summary={
        "status":"prospective_simulator_only",
        "fixed_H1_rule":{"gyro_p_abs":P_LIMIT,"gyro_q_abs":Q_LIMIT,
                         "consecutive_steps":STREAK,"quadrants":str(MOTOR_BY_SIGNS)},
        "pilot_test_data_used_for_tuning":False,
        "test_seeds":list(SEEDS),
        "onsets_s":list(ONSETS),
        "motor_speed_retention":list(RETENTIONS),
        "sensor_noise_sigmas_radps":list(NOISE_SIGMAS),
        "sensor_noise_is_offline_not_physical":True,
        "physical_traces":len(manifest),
        "noise_variant_decisions":len(decisions),
        "primary_endpoint":"retain_50_noise_0p0.metrics.temporal_valid_balanced_accuracy",
        "always_healthy_balanced_accuracy":.2,
        "groups":groups,
        "raw_manifest":manifest,
        "git_sha":os.environ.get("GITHUB_SHA","local-uncommitted"),
        "run_id":os.environ.get("GITHUB_RUN_ID"),
        "script_sha256":hash_file(Path(__file__)),
        "limits":[
            "Single Crazyflie Webots model, fixed commands and only two fault onset times.",
            "Half motor speed is not half motor thrust, and this does not evaluate recovery.",
            "Offline additive gyro noise does not model actual sensor or flight dynamics.",
            "Eight command seeds are paired across scenarios: 144 traces are not 144 independent physical plants.",
            "No real flight or safety claims, no post hoc detector tuning.",
        ],
    }
    (args.output_dir/"h2_results.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps({"physical_traces":len(manifest),"outcomes":len(decisions),
                      "primary_result":groups["retain_50_noise_0p0"]["metrics"],
                      "primary_seed_cluster_interval":groups["retain_50_noise_0p0"]["seed_cluster_bootstrap"]["percentile_95_interval"]},indent=2))


if __name__=="__main__":
    main()
