#!/usr/bin/env python3
"""Freeze, then evaluate a new paired representation study; never run old treatments."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import importlib.metadata
import io
import json
import math
from pathlib import Path
import platform
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
from PIL import features
import numpy as np
from scipy.stats import binomtest, spearmanr
from phase22_representation_transform import REPRESENTATIONS, QUALITIES, encode, atomic_write, image_difference
from phase25_lib import (BASELINE_CHECKPOINT_SHA256, PROTECTED_MANIFEST_SHA256, Box,
                         box_from_yolo, frame_metrics, read_protected_manifest, sha256_file)
from phase25_reconstruction_lock import load_lock, verify_archive
from uav_safety.real_landing_dataset import read_yolo_boxes

PROTECTED = ROOT / "results/phase25_failure_atlas/protected_test_manifest.csv"
SETTINGS = {"imgsz": 320, "conf": .001, "iou": .7, "max_det": 300, "batch": 16,
            "workers": 2, "device": "cpu", "split": "test"}
METHODS = ("scripts/phase22_representation_transform.py", "scripts/run_phase22_representation_study.py",
           "scripts/phase25_lib.py", "scripts/phase25_reconstruction_lock.py",
           "src/uav_safety/real_landing_dataset.py")
REFERENCE = {"precision": .7959713659654185, "recall": .38372093023255816,
             "map50": .42662686781189296, "map50_95": .2723431563204893}


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def write_json(path: Path, value: object) -> None:
    content = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    atomic_write(path, content, digest(content))


def csv_bytes(rows: list[dict]) -> bytes:
    if not rows:
        raise ValueError("Empty output table")
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue().encode()


def write_csv(path: Path, rows: list[dict]) -> None:
    content = csv_bytes(rows)
    atomic_write(path, content, digest(content))


def runtime() -> dict:
    import ultralytics
    from ultralytics.models.yolo.detect import val
    return {"python": platform.python_version(), "platform": platform.platform(),
            "packages": {name: importlib.metadata.version(name) for name in
                         ("torch", "torchvision", "ultralytics", "numpy", "Pillow", "opencv-python", "scipy")},
            "jpeg": features.version_codec("jpg"),
            "libjpeg_turbo": features.version_feature("libjpeg_turbo"),
            "official_validator_sha256": sha256_file(Path(val.__file__)),
            "ultralytics_path_recorded": Path(ultralytics.__file__).name}


def verify_population(source: Path, weights: Path, archive: Path) -> list[dict]:
    if sha256_file(weights) != BASELINE_CHECKPOINT_SHA256:
        raise ValueError("Checkpoint SHA lock failed")
    if sha256_file(PROTECTED) != PROTECTED_MANIFEST_SHA256:
        raise ValueError("Protected manifest SHA lock failed")
    frames = read_protected_manifest(PROTECTED)
    if len(frames) != 86 or Counter(f["sequence"] for f in frames) != {"land_pad": 66, "land_pad2": 20}:
        raise ValueError("Exact 86-frame population lock failed")
    lock = load_lock()
    verify_archive(archive, lock)
    if set(f["image"] for f in frames) != set(lock["protected_test_files"]):
        raise ValueError("Protected IDs changed")
    for folder, key in (("images", "image"), ("labels", "label")):
        directory = source / folder / "test"
        if {p.name for p in directory.iterdir() if p.is_file()} != {f[key] for f in frames}:
            raise ValueError(f"Unexpected protected {folder} population")
    for frame in frames:
        frozen = lock["protected_test_files"][frame["image"]]
        if (sha256_file(source / "images/test" / frame["image"]) != frozen["image_sha256"]
                or sha256_file(source / "labels/test" / frame["label"]) != frozen["label_sha256"]):
            raise ValueError(f"Protected bytes changed: {frame['image']}")
    return frames


def unique_population(rows: list[dict], representations=REPRESENTATIONS) -> None:
    frames = read_protected_manifest(PROTECTED)
    expected = {(f["image"], r) for f in frames for r in representations}
    observed = [(r["frame_id"], r["representation"]) for r in rows]
    if len(observed) != len(set(observed)) or set(observed) != expected:
        raise ValueError("Duplicate or incomplete frame/representation population")


def prepare(args) -> None:
    if args.out.exists() and any(args.out.iterdir()):
        raise ValueError("Use a new output directory; original artifacts must remain untouched")
    frames = verify_population(args.source, args.weights, args.archive)
    rows = []
    q95_inventory = hashlib.sha256()
    for frame in frames:
        source = (args.source / "images/test" / frame["image"]).read_bytes()
        label = (args.source / "labels/test" / frame["label"]).read_bytes()
        for rep in REPRESENTATIONS:
            content = encode(source, rep)
            if content != encode(source, rep):
                raise ValueError("Representation transform is nondeterministic")
            filename = Path(frame["image"]).with_suffix(".png").name if rep == "LOSSLESS_PNG" else frame["image"]
            path = args.work / rep / "images/test" / filename
            atomic_write(path, content, digest(content), image=True)
            atomic_write(args.work / rep / "labels/test" / frame["label"], label, digest(label))
            row = {"frame_id": frame["image"], "sequence": frame["sequence"], "representation": rep,
                   "source_sha256": digest(source), "derived_sha256": digest(content),
                   "label_sha256": digest(label), "quality": QUALITIES.get(rep), "filename": filename,
                   **image_difference(source, content)}
            rows.append(row)
            if rep == "HISTORICAL_Q95":
                q95_inventory.update(f"{frame['image']}:{digest(content)}\n".encode())
    unique_population(rows)
    expected_inventory = load_lock()["condition_image_inventory_sha256"]["clean"]
    if q95_inventory.hexdigest() != expected_inventory:
        raise ValueError("Q95 bytes differ from frozen historical clean inventory")
    args.out.mkdir(parents=True, exist_ok=True)
    write_csv(args.out / "representation_manifest.csv", rows)
    protocol = {"schema_version": 1, "study": "Phase 22 Input Representation Sensitivity Study v1",
                "new_followup_experiment": True, "original_sweep": {
                    "status": "INCONCLUSIVE — CLEAN CONTROL GATE FAILED — NO TREATMENT INFERENCE RUN",
                    "evidence": "user-supplied assignment; original protocol/result unavailable in fetched repository",
                    "reported_raw_map50": .423908, "tolerance": .001},
                "source_manifest_sha256": PROTECTED_MANIFEST_SHA256,
                "reconstruction_lock_sha256": sha256_file(ROOT / "docs/phase25_reconstruction_lock.json"),
                "checkpoint_sha256": BASELINE_CHECKPOINT_SHA256,
                "source_archive_sha256": sha256_file(args.archive), "settings": SETTINGS,
                "runtime": runtime(), "representations": list(REPRESENTATIONS),
                "transform": "Pillow decode, convert RGB; JPEG save quality=95/90/100 with all other defaults; PNG compress_level=6 optimize=False; raw exact bytes",
                "transformation_sha256": sha256_file(ROOT / METHODS[0]),
                "method_sha256": {p: sha256_file(ROOT / p) for p in METHODS},
                "q95_inventory_sha256": expected_inventory,
                "representation_manifest_sha256": sha256_file(args.out / "representation_manifest.csv"),
                "clean_reference": REFERENCE, "q95_tolerance": .001,
                "raw_reference_map50": .423908, "raw_tolerance": .000005,
                "determinism_verified_cases": len(rows), "population": {"frames": 86, "variants": 5, "cases": 430},
                "primary_comparison": ["RAW_SOURCE", "HISTORICAL_Q95"],
                "frame_matching": "class-aware confidence-ranked one-to-one IoU >= 0.5; all GT matched defines success; no FP restriction",
                "prediction_export": "capture scaled NMS outputs from the same official validation pass; normalized xyxy; no second prediction pass",
                "aggregate_matching": "unchanged official Ultralytics validation evaluator; aggregate P/R use evaluator F1 operating point; frame metrics use frozen 0.001 floor",
                "statistics": {"bootstrap_unit": "source frame paired across representations", "replicates": 10000,
                    "seed": 20260930, "interval": "percentile 95%", "binary_test": "exact two-sided McNemar/binomial on discordant pairs",
                    "continuous": "paired mean differences in best IoU and best-any confidence; matched confidence on both-pass subset only",
                    "pixel_association": "descriptive Spearman pixel RMSE vs absolute prediction difference; no mechanism inference",
                    "scope": "retrospective diagnostic; exploratory tests; frame uncertainty conditional on two videos, not session generalization"},
                "stage_b_gate": "all 86 Q95 and raw cases complete, deterministic bytes, stable Q95 hashes, all four Q95 aggregates <=0.001 from reference, raw mAP50 within 0.000005; otherwise STOP",
                "limitations": ["two temporally dependent source videos", "86 protected frames already inspected",
                    "codec and runtime sensitivity", "static detector", "synthetic masks have no direct flight-safety equivalence"]}
    write_json(args.out / "protocol.json", protocol)
    print("Frozen protocol SHA:", sha256_file(args.out / "protocol.json"), flush=True)


def validate_protocol(protocol: dict, expected_sha: str, path: Path) -> None:
    if sha256_file(path) != expected_sha:
        raise ValueError("Protocol SHA changed")
    if protocol["checkpoint_sha256"] != BASELINE_CHECKPOINT_SHA256 or protocol["settings"] != SETTINGS:
        raise ValueError("Checkpoint or historical settings lock failed")
    if protocol["runtime"] != runtime():
        raise ValueError("Runtime differs from the pre-inference freeze")
    if protocol["representations"] != list(REPRESENTATIONS):
        raise ValueError("Representation population changed")
    for name, expected in protocol["method_sha256"].items():
        if sha256_file(ROOT / name) != expected:
            raise ValueError(f"Implementation changed after freeze: {name}")


def evaluate(weights: Path, directory: Path, frames: list[dict], representation: str) -> tuple[dict, list, list]:
    from ultralytics import YOLO
    from ultralytics.models.yolo.detect.val import DetectionValidator
    from ultralytics.utils import ops
    metrics_rows, predictions_rows = [], []
    by_stem = {Path(f["image"]).stem: f for f in frames}

    class ExportValidator(DetectionValidator):
        def update_metrics(self, preds, batch):
            super().update_metrics(preds, batch)
            for index, prediction in enumerate(preds):
                prepared = self._prepare_batch(index, batch)
                frame = by_stem[Path(prepared["im_file"]).stem]
                scaled = self.scale_preds(prediction, prepared)
                h, w = prepared["ori_shape"]
                boxes = []
                for coords, cls, conf in zip(scaled["bboxes"].cpu().tolist(), scaled["cls"].cpu().tolist(), scaled["conf"].cpu().tolist(), strict=True):
                    x0, y0, x1, y1 = coords
                    boxes.append(Box(int(cls), max(0., min(1., x0/w)), max(0., min(1., y0/h)),
                                     max(0., min(1., x1/w)), max(0., min(1., y1/h)), float(conf)))
                labels = read_yolo_boxes(directory / "labels/test" / frame["label"], class_id=0)
                truth = [box_from_yolo(b.class_id, b.x_center, b.y_center, b.width, b.height) for b in labels]
                values, raw = frame_metrics(truth, boxes, iou_threshold=.5)
                metrics_rows.append({"frame_id": frame["image"], "sequence": frame["sequence"],
                    "representation": representation, "success": values["frame_success"], "TP": values["tp"],
                    "FP": values["fp"], "FN": values["fn"], "gt_count": values["gt_count"],
                    "best_iou": values["best_iou"], "matched_confidence": values["best_confidence_tp"],
                    "best_confidence_any": values["best_confidence_any"], "prediction_count": len(boxes)})
                predictions_rows.extend({"frame_id": frame["image"], "representation": representation, **row} for row in raw)
    with tempfile.TemporaryDirectory(prefix="phase22-representation-validation-") as temp:
        yaml = Path(temp) / "data.yaml"
        yaml.write_text(f"path: {directory.resolve()}\ntrain: images/test\nval: images/test\ntest: images/test\nnames:\n  0: landing_pad\n")
        model = YOLO(str(weights))
        output = model.val(validator=ExportValidator, data=str(yaml), **SETTINGS,
                           plots=False, verbose=False, project=temp, name="evaluation", exist_ok=True)
        aggregates = {"precision": float(output.box.mp), "recall": float(output.box.mr),
                      "map50": float(output.box.map50), "map50_95": float(output.box.map)}
    if any(not math.isfinite(x) or not 0 <= x <= 1 for x in aggregates.values()):
        raise ValueError("Invalid aggregate output")
    unique_population(metrics_rows, (representation,))
    return aggregates, metrics_rows, predictions_rows


def paired_analysis(rows: list[dict], manifest: list[dict], seed=20260930, replicates=10000) -> dict:
    unique_population(rows)
    by_key = {(r["frame_id"], r["representation"]): r for r in rows}
    ids = sorted({r["frame_id"] for r in rows})
    left = [by_key[(f, "RAW_SOURCE")] for f in ids]
    right = [by_key[(f, "HISTORICAL_Q95")] for f in ids]
    transitions = Counter("both_pass" if a["success"] and b["success"] else
        "raw_pass_q95_fail" if a["success"] else "raw_fail_q95_pass" if b["success"] else "both_fail"
        for a, b in zip(left, right, strict=True))
    transitions = {key: transitions[key] for key in ("raw_fail_q95_pass", "raw_pass_q95_fail", "both_pass", "both_fail")}
    discordant = transitions["raw_fail_q95_pass"] + transitions["raw_pass_q95_fail"]
    rng = np.random.default_rng(seed)
    sample = rng.integers(0, len(ids), size=(replicates, len(ids)))
    statistics = {}
    for name in ("success", "best_iou", "best_confidence_any", "TP", "FP", "FN"):
        # Missing any-confidence means no predictions: defined as 0 only for this unconditional summary.
        differences = np.array([float(b[name] or 0) - float(a[name] or 0) for a, b in zip(left, right, strict=True)])
        lower, upper = np.quantile(differences[sample].mean(axis=1), [.025, .975])
        statistics[name] = {"mean_q95_minus_raw": float(differences.mean()), "ci95": [float(lower), float(upper)], "n": len(ids)}
    matched = np.array([b["matched_confidence"] - a["matched_confidence"] for a, b in zip(left, right, strict=True)
                        if a["success"] and b["success"]])
    if len(matched):
        draw = rng.integers(0, len(matched), size=(replicates, len(matched)))
        statistics["matched_confidence_both_pass"] = {"n": len(matched), "mean_q95_minus_raw": float(matched.mean()),
            "ci95": [float(x) for x in np.quantile(matched[draw].mean(axis=1), [.025, .975])]}
    else:
        statistics["matched_confidence_both_pass"] = {"n": 0, "mean_q95_minus_raw": None, "ci95": None}
    q95 = {r["frame_id"]: r for r in manifest if r["representation"] == "HISTORICAL_Q95"}
    rmse = [float(q95[f]["pixel_rmse"]) for f in ids]
    correlations = {}
    for name in ("best_iou", "best_confidence_any"):
        delta = [abs(float(b[name] or 0) - float(a[name] or 0)) for a, b in zip(left, right, strict=True)]
        rho = float(spearmanr(rmse, delta).statistic) if len(set(rmse)) > 1 and len(set(delta)) > 1 else None
        correlations[name] = rho
    return {"primary_comparison": "RAW_SOURCE vs HISTORICAL_Q95", "source_frames": 86,
        "transitions": transitions, "exact_mcnemar_p": float(binomtest(transitions["raw_fail_q95_pass"], discordant).pvalue) if discordant else 1.,
        "statistics": statistics, "seed": seed, "replicates": replicates,
        "count_transitions": {name: dict(Counter(f"{a[name]}->{b[name]}" for a, b in zip(left, right, strict=True))) for name in ("TP", "FP", "FN")},
        "descriptive_rmse_spearman_abs_change": correlations,
        "uncertainty_limit": "source-frame paired bootstrap conditional on two videos; temporal dependence not resolved; no independent-session population inference",
        "confidence_missingness": "matched confidence compared only on both-pass frames; missing best-any confidence assigned 0 for unconditional summary"}


def stage_a_gate(aggregates: dict, *, complete: bool, deterministic: bool, hashes_verified: bool) -> dict:
    checks = {"complete_86_frames_per_representation": complete, "deterministic_transform": deterministic,
              "stable_derived_hashes": hashes_verified}
    q95 = aggregates.get("HISTORICAL_Q95", {})
    raw = aggregates.get("RAW_SOURCE", {})
    checks["q95_baseline"] = all(isinstance(q95.get(k), (int, float)) and math.isfinite(q95[k]) and abs(q95[k]-v) <= .001 for k, v in REFERENCE.items())
    checks["raw_diagnostic_reproduced"] = isinstance(raw.get("map50"), (int, float)) and math.isfinite(raw["map50"]) and abs(raw["map50"]-.423908) <= .000005
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def require_treatment_gates(stage_a: dict, zero_dose: dict) -> None:
    if stage_a.get("status") != "PASS" or not stage_a.get("checks") or not all(stage_a["checks"].values()):
        raise ValueError("Stage A failed: treatment inference prohibited")
    if zero_dose.get("status") != "PASS" or not zero_dose.get("checks") or not all(zero_dose["checks"].values()):
        raise ValueError("Stage B zero-dose gate failed: treatment inference prohibited")


def run(args) -> None:
    protocol_path = args.out / "protocol.json"
    protocol = json.loads(protocol_path.read_text())
    validate_protocol(protocol, args.protocol_sha, protocol_path)
    if (args.out / "aggregate_metrics.json").exists():
        raise ValueError("Inference already completed; do not overwrite")
    frames = verify_population(args.source, args.weights, args.archive)
    manifest_path = args.out / "representation_manifest.csv"
    if sha256_file(manifest_path) != protocol["representation_manifest_sha256"]:
        raise ValueError("Frozen representation manifest changed")
    with manifest_path.open(newline="") as handle:
        manifest = list(csv.DictReader(handle))
    unique_population(manifest)
    for row in manifest:
        path = args.work / row["representation"] / "images/test" / row["filename"]
        if sha256_file(path) != row["derived_sha256"]:
            raise ValueError("Derived representation SHA changed")
        source = (args.source / "images/test" / row["frame_id"]).read_bytes()
        if encode(source, row["representation"]) != path.read_bytes():
            raise ValueError("Derived transform no longer deterministic")
        label = args.work / row["representation"] / "labels/test" / Path(row["frame_id"]).with_suffix(".txt").name
        if sha256_file(label) != row["label_sha256"]:
            raise ValueError("Derived label changed")
    aggregates, frame_rows, predictions = {}, [], []
    for rep in REPRESENTATIONS:
        aggregate, per_frame, boxes = evaluate(args.weights, args.work / rep, frames, rep)
        aggregates[rep] = aggregate
        frame_rows.extend(per_frame)
        predictions.extend(boxes)
        print(rep, aggregate, flush=True)
    unique_population(frame_rows)
    frame_rows.sort(key=lambda r: (r["representation"], r["frame_id"]))
    predictions.sort(key=lambda r: (r["representation"], r["frame_id"], r["prediction_index"]))
    write_csv(args.out / "frame_metrics.csv", frame_rows)
    write_csv(args.out / "raw_predictions.csv", predictions)
    write_json(args.out / "aggregate_metrics.json", aggregates)
    analysis = paired_analysis(frame_rows, manifest)
    write_json(args.out / "paired_representation_analysis.json", analysis)
    gate = stage_a_gate(aggregates, complete=True, deterministic=True, hashes_verified=True)
    write_json(args.out / "stage_a_gate.json", gate)
    write_json(args.out / "run_manifest.json", {"protocol_sha256": args.protocol_sha, "stage_a": gate,
        "frame_rows": len(frame_rows), "prediction_rows": len(predictions), "runtime": runtime(),
        "output_sha256": {name: sha256_file(args.out / name) for name in (
            "representation_manifest.csv", "frame_metrics.csv", "raw_predictions.csv", "aggregate_metrics.json",
            "paired_representation_analysis.json", "stage_a_gate.json")},
        "treatment_inference": "NOT RUN", "original_artifacts_modified": False})
    print("Stage A:", gate["status"], flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run"))
    for name in ("archive", "source", "weights", "work", "out"):
        parser.add_argument("--"+name, type=Path, required=True)
    parser.add_argument("--protocol-sha")
    args = parser.parse_args()
    if args.command == "run" and not args.protocol_sha:
        parser.error("run requires the pre-inference --protocol-sha")
    (prepare if args.command == "prepare" else run)(args)


if __name__ == "__main__":
    main()
