#!/usr/bin/env python3
"""Independent standard-library audit of an archived AegisLand FDI-H2 result.

This script does NOT import the production H2 evaluator. It repeats the frozen
pre-registered inference on raw sensor traces and checks saved predictions,
sha256 provenance, 144 scenario coverage and published primary/secondary scores.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import random
import statistics
import zipfile
from pathlib import Path

SEEDS=(89,97,101,103,107,109,113,127)
ONSETS=(9.0,13.0)
KEEPS=(0.0,.5)
NOISES=(0.0,.2,1.0)
FIELDS=("time_s","x_m","y_m","z_m","gyro_p_rps","gyro_q_rps","gyro_r_rps","cmd_m1","cmd_m2","cmd_m3","cmd_m4")
QUADS={(1,1):1,(1,-1):2,(-1,-1):3,(-1,1):4}
TRACE_HEADERS=FIELDS+("failed_motor","fault_active","seed","fault_onset_s","motor_retention")
DECISION_HEADERS=("seed","onset","motor","retention","sensor_noise_sigma_radps",
                  "prediction","alert_time_s","alert_altitude_m","pre_onset")


def validate_archive_members(names):
    """ZIP members must be unique; set() by itself hides ambiguous duplicates."""
    if len(names)!=len(set(names)):
        raise ValueError("Duplicate ZIP members make the archived evidence ambiguous")
    return set(names)


def validate_csv_headers(headers,expected,tag):
    """Reject duplicate/missing/reordered CSV headers before DictReader masks them."""
    if tuple(headers or ())!=tuple(expected):
        raise ValueError(f"{tag}: CSV schema differs from recorded protocol")


def read_bool_exact(value,tag):
    """Never silently interpret a corrupted pre-onset marker as False."""
    if value not in ("True","False"):
        raise ValueError(f"{tag}: pre_onset must be True or False")
    return value=="True"


def verify_archive_sha256(path,expected):
    """Optional check against a fingerprint recorded separately from the ZIP."""
    if (not isinstance(expected,str) or len(expected)!=64 or
            any(char not in "0123456789abcdef" for char in expected.lower())):
        raise ValueError("Archive SHA-256 must have exactly 64 hexadecimal characters")
    digest=hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda:source.read(1024*1024),b""):
            digest.update(chunk)
    if digest.hexdigest()!=expected.lower():
        raise ValueError("Evidence ZIP differs from externally recorded SHA-256")
    return True


def cases():
    for seed in SEEDS:
        for onset in ONSETS:
            yield seed,onset,0,1.0
            for keep in KEEPS:
                for motor in (1,2,3,4):
                    yield seed,onset,motor,keep

def name(case):
    seed,onset,motor,keep=case
    return f"seed{seed}_onset{int(onset)}_motor{motor}_keep{round(keep*100)}.csv"

def seeded_rng(seed,onset,motor,keep,noise):
    salt=f"FDI-H2:20261011:{seed}:{int(onset)}:{motor}:{keep:.1f}:{noise:.1f}"
    return random.Random(int.from_bytes(hashlib.sha256(salt.encode()).digest()[:8],"big"))

def float_checked(row,key,identity):
    try:
        v=float(row[key])
    except (KeyError,TypeError,ValueError) as exc:
        raise ValueError(f"{identity}: malformed number {key}") from exc
    if not math.isfinite(v):
        raise ValueError(f"{identity}: nonfinite value {key}")
    return v

def check_trace(rows,case,identity):
    seed,onset,motor,keep=case
    if len(rows)<220:
        raise ValueError(f"{identity}: fewer than 220 rows")
    last=-math.inf
    for row in rows:
        t=float_checked(row,"time_s",identity)
        if t<=last:
            raise ValueError(f"{identity}: nonincreasing time")
        if (int(row["seed"])!=seed or int(row["failed_motor"])!=motor or
            float_checked(row,"fault_onset_s",identity)!=onset or
            float_checked(row,"motor_retention",identity)!=keep or
            int(row["fault_active"])!=int(motor>0 and t>=onset)):
            raise ValueError(f"{identity}: scenario metadata changed")
        if t<=onset+.7+1e-9:
            for k in FIELDS:
                float_checked(row,k,identity)
        last=t
    if last<onset+.7:
        raise ValueError(f"{identity}: trace incomplete before scoring ends")

def replay(rows,case,sigma):
    seed,onset,motor,keep=case
    rng=seeded_rng(seed,onset,motor,keep,sigma)
    streak=0
    for row in rows:
        t=float(row["time_s"])
        if t>onset+.7 or (t>=onset and float(row["z_m"])<.5):
            break
        p=float(row["gyro_p_rps"])
        q=float(row["gyro_q_rps"])
        if sigma:
            p+=rng.gauss(0,sigma)
            q+=rng.gauss(0,sigma)
        streak=streak+1 if abs(p)>=2.0 and abs(q)>=.75 else 0
        if streak==3:
            return QUADS[(1 if p>0 else -1,1 if q>0 else -1)],t,float(row["z_m"]),t<onset
    return 0,None,None,False

def near(actual,claimed,atol=1e-9):
    if actual is None:
        return claimed is None
    return isinstance(claimed,(float,int)) and not isinstance(claimed,bool) and math.isclose(
        actual,claimed,abs_tol=atol,rel_tol=1e-10)

def rows_metrics(rows):
    matrix=[[0]*5 for _ in range(5)]
    totals=[0]*5
    correct=[0]*5
    pre=0
    latency=[]
    faults=[]
    for r in rows:
        truth,pred=r["motor"],r["prediction"]
        matrix[truth][pred]+=1
        totals[truth]+=1
        valid=truth==pred and not r["pre_onset"]
        correct[truth]+=int(valid)
        pre+=int(r["pre_onset"])
        if truth:
            faults.append(r)
            if valid and r["alert_time_s"] is not None:
                latency.append(r["alert_time_s"]-r["onset"])
    if any(x==0 for x in totals):
        raise ValueError("All five classes required")
    recall=[correct[i]/totals[i] for i in range(5)]
    return dict(
        traces=len(rows),
        temporal_valid_balanced_accuracy=sum(recall)/5,
        class_temporally_valid_recall=dict(zip(("healthy","motor_1","motor_2","motor_3","motor_4"),recall)),
        healthy_false_alarm_rate=1-recall[0],
        fault_detected_rate=sum(r["prediction"]>0 and not r["pre_onset"] for r in faults)/len(faults),
        correct_motor_isolation_rate=sum(r["motor"]==r["prediction"] and not r["pre_onset"] for r in faults)/len(faults),
        premature_alert_count=pre,
        median_correct_detection_latency_s=statistics.median(latency) if latency else None,
        confusion_matrix_rows_truth_cols_prediction=matrix
    )

def check_metric(actual,claimed,tag):
    for k,v in actual.items():
        out=claimed.get(k)
        if isinstance(v,dict):
            if set(v)!=set(out or {}):
                raise ValueError(f"{tag}.{k}: class keys mismatch")
            for sub,x in v.items():
                if not near(x,out[sub]):
                    raise ValueError(f"{tag}.{k}.{sub} mismatch: {x!r} vs {out[sub]!r}")
        elif isinstance(v,list):
            if v!=out:
                raise ValueError(f"{tag}.{k}: confusion matrix mismatch")
        elif not near(v,out):
            raise ValueError(f"{tag}.{k} mismatch: {v!r} vs {out!r}")

def audit(artifact,source=None,expected_archive_sha256=None):
    external_zip_verified=(verify_archive_sha256(artifact,expected_archive_sha256)
                           if expected_archive_sha256 is not None else False)
    with zipfile.ZipFile(artifact) as zipf:
        files=validate_archive_members(zipf.namelist())
        required={"report/h2_results.json","report/per_case_decisions.csv","git_sha.txt","docker_image_digest.json"}
        if not required.issubset(files):
            raise ValueError("Missing required report or provenance")
        result=json.loads(zipf.read("report/h2_results.json"))
        if result.get("git_sha")!=zipf.read("git_sha.txt").decode().strip():
            raise ValueError("Git commit identity mismatch")
        digest=json.loads(zipf.read("docker_image_digest.json"))
        if not isinstance(digest,list) or not any(
            isinstance(s,str) and s.startswith("cyberbotics/webots@sha256:") for s in digest):
            raise ValueError("Invalid Webots digest provenance")
        if source:
            digest=hashlib.sha256(Path(source).read_bytes()).hexdigest()
            if digest!=result.get("script_sha256"):
                raise ValueError("Frozen evaluator SHA-256 mismatch")
        if (result.get("test_seeds")!=list(SEEDS) or result.get("onsets_s")!=list(ONSETS) or
            result.get("motor_speed_retention")!=list(KEEPS) or
            result.get("sensor_noise_sigmas_radps")!=list(NOISES) or
            result.get("physical_traces")!=144 or result.get("noise_variant_decisions")!=432):
            raise ValueError("Protocol metadata mismatch")
        if result.get("primary_endpoint")!="retain_50_noise_0p0.metrics.temporal_valid_balanced_accuracy":
            raise ValueError("Primary endpoint was changed")
        csv_reader=csv.DictReader(io.StringIO(zipf.read("report/per_case_decisions.csv").decode()))
        validate_csv_headers(csv_reader.fieldnames,DECISION_HEADERS,"H2 decisions")
        rows=list(csv_reader)
        if len(rows)!=432:
            raise ValueError("Expected 432 decisions")
        output={}
        for row in rows:
            case=(int(row["seed"]),float(row["onset"]),int(row["motor"]),float(row["retention"]))
            sigma=float(row["sensor_noise_sigma_radps"])
            key=case+(sigma,)
            if key in output:
                raise ValueError("Duplicate score record")
            if case not in set(cases()) or sigma not in NOISES:
                raise ValueError("Unregistered score case")
            alert=row["alert_time_s"] or None
            z=row["alert_altitude_m"] or None
            output[key]={"seed":case[0],"onset":case[1],"motor":case[2],"retention":case[3],
                         "sensor_noise_sigma_radps":sigma,
                         "prediction":int(row["prediction"]),
                         "alert_time_s":float(alert) if alert else None,
                         "alert_altitude_m":float(z) if z else None,
                         "pre_onset":read_bool_exact(row["pre_onset"],"H2 decisions")}
        if len(output)!=len(list(cases()))*len(NOISES):
            raise ValueError("Case/noise coverage incomplete")
        manifests=result.get("raw_manifest",[])
        manifest_map={m["file"]:m for m in manifests}
        if len(manifests)!=144 or len(manifest_map)!=144:
            raise ValueError("Manifest must have exactly 144 unique trace entries")
        expected_manifest={name(c) for c in cases()}
        if set(manifest_map)!=expected_manifest:
            raise ValueError("Raw manifest case inventory differs from registered scenarios")
        raw_names={f for f in files if f.startswith("raw/") and f.endswith(".csv")}
        if raw_names!={"raw/"+name(c) for c in cases()}:
            raise ValueError("Incorrect raw trace inventory")
        for case in cases():
            fname=name(case)
            entry=manifest_map[fname]
            sourcebytes=zipf.read("raw/"+fname)
            if hashlib.sha256(sourcebytes).hexdigest()!=entry["sha256"]:
                raise ValueError(f"{fname}: raw SHA-256 mismatch")
            if any(entry[k]!=v for k,v in zip(("seed","onset","motor","retention"),case)):
                raise ValueError(f"{fname}: manifest metadata mismatch")
            trace_reader=csv.DictReader(io.StringIO(sourcebytes.decode()))
            validate_csv_headers(trace_reader.fieldnames,TRACE_HEADERS,fname)
            source_rows=list(trace_reader)
            if entry["rows"]!=len(source_rows):
                raise ValueError(f"{fname}: row count mismatch")
            check_trace(source_rows,case,fname)
            for sigma in NOISES:
                pred,t,z,pre=replay(source_rows,case,sigma)
                saved=output[case+(sigma,)]
                if pred!=saved["prediction"] or pre!=saved["pre_onset"] or not near(t,saved["alert_time_s"]) or not near(z,saved["alert_altitude_m"]):
                    raise ValueError(f"{fname} sigma={sigma}: saved decision differs from raw replay")
        for sigma in NOISES:
            for keep in KEEPS:
                group=[x for x in output.values() if x["sensor_noise_sigma_radps"]==sigma
                       and (x["motor"]==0 or x["retention"]==keep)]
                tag=f"retain_{round(keep*100)}_noise_{str(sigma).replace('.','p')}"
                claimed=result["groups"][tag]
                check_metric(rows_metrics(group),claimed["metrics"],tag)
                for onset in ONSETS:
                    slice_=[x for x in group if x["onset"]==onset]
                    check_metric(rows_metrics(slice_),claimed["by_onset"][str(int(onset))],f"{tag}.onset{onset}")
                # Independent paired-seed resampling, same locked 2,000 draws.
                rng=random.Random(20261013)
                groups={seed:[x for x in group if x["seed"]==seed] for seed in SEEDS}
                estimates=[]
                for _ in range(2000):
                    resample=[y for __ in SEEDS for y in groups[rng.choice(SEEDS)]]
                    estimates.append(rows_metrics(resample)["temporal_valid_balanced_accuracy"])
                estimates.sort()
                def perc(v):
                    idx=v*(len(estimates)-1)
                    i=int(idx)
                    a=idx-i
                    return estimates[i]*(1-a)+estimates[min(i+1,len(estimates)-1)]*a
                interval=claimed["seed_cluster_bootstrap"]["percentile_95_interval"]
                if len(interval)!=2 or not all(near(x,y) for x,y in zip((perc(.025),perc(.975)),interval)):
                    raise ValueError(f"{tag}: paired seed bootstrap interval mismatch")
        return {"ok":True,"raw_traces":144,"noise_variant_decisions":432,
                "external_zip_checksum_verified":external_zip_verified,
                "primary_balanced_accuracy":result["groups"]["retain_50_noise_0p0"]["metrics"]["temporal_valid_balanced_accuracy"],
                "complete_loss_balanced_accuracy":result["groups"]["retain_0_noise_0p0"]["metrics"]["temporal_valid_balanced_accuracy"]}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("artifact_zip",type=Path)
    parser.add_argument("--evaluator-source",type=Path)
    parser.add_argument("--expected-archive-sha256",
                        help="Optional externally retained SHA-256 for exact evidence ZIP bytes")
    args=parser.parse_args()
    print(json.dumps(audit(args.artifact_zip,args.evaluator_source,args.expected_archive_sha256),indent=2))

if __name__=="__main__":
    main()
