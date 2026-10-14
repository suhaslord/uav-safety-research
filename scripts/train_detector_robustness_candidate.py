#!/usr/bin/env python3
"""Paired development-only YOLO training. No protected test inference."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import shutil

from PIL import Image

from scripts.prepare_detector_robustness_augmentation import (
    CONDITIONS, augment, digest, rng_for, validate_label, verify_split,
)


def verify_candidate(source_root: Path, candidate_root: Path) -> dict:
    train, val, sha = verify_split(source_root)
    receipt = json.loads((candidate_root / "receipt.json").read_text(encoding="utf-8"))
    if (receipt.get("schema") != "aegisland.detector_robustness.development-only-aug.v1"
            or receipt.get("locked_split_sha256") != sha
            or receipt.get("protected_test_read") is not False
            or receipt.get("derived_val") != 0
            or receipt.get("original_train") != len(train)
            or receipt.get("original_val") != len(val)
            or receipt.get("mode") != "matched"
            or receipt.get("derived_train") != 0
            or receipt.get("training_image_count") != len(train)
            or receipt.get("transformed_train", 0) < 1):

        raise ValueError("Candidate receipt fails locked split policy")
    # Same training set size and image/label identities gives the same number of
    # SGD minibatch steps at equal batch size and epochs, unlike the old pilot.
    expected_train = {p.name for p in train}
    actual_train = {p.name for p in (candidate_root / "images/train").iterdir() if p.is_file()}
    expected_labels = {p.with_suffix(".txt").name for p in train}
    actual_labels = {p.name for p in (candidate_root / "labels/train").iterdir() if p.is_file()}
    if actual_train != expected_train or actual_labels != expected_labels:
        raise ValueError("Matched training must preserve exact original image and label names")
    for original in train:
        label = original.with_suffix(".txt").name
        if digest(source_root / "labels/train" / label) != digest(candidate_root / "labels/train" / label):
            raise ValueError("Candidate training label was changed")
    for original in val:
        new_image = candidate_root / "images/val" / original.name
        if digest(original) != digest(new_image):
            raise ValueError("Candidate validation images differ from originals")
        label = original.with_suffix(".txt").name
        if digest(source_root / "labels/val" / label) != digest(candidate_root / "labels/val" / label):
            raise ValueError("Candidate validation labels differ from originals")
    listed = {Path(entry["image"]).name for entry in receipt["inventory"] if entry["split"] == "val"}
    present = {p.name for p in (candidate_root / "images/val").iterdir() if p.is_file()}
    if listed != present or listed != {p.name for p in val}:
        raise ValueError("Candidate validation inventory altered")
    expected_inventory = {
        f"images/{split}/{path.name}" for split, paths in (("train", train), ("val", val))
        for path in paths
    }
    reported = {entry["image"] for entry in receipt["inventory"]}
    if reported != expected_inventory or len(receipt["inventory"]) != len(reported):
        raise ValueError("Matched receipt must list one entry per development image")
    for item in receipt["inventory"]:
        rel = Path(item["image"])
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError("Candidate inventory path escapes root")
        if digest(candidate_root / rel) != item["image_sha256"]:
            raise ValueError("Candidate image hash differs from receipt")
    if (candidate_root / "images/test").exists() or (candidate_root / "labels/test").exists():
        raise ValueError("No protected test allowed in candidate")
    if "test:" in (candidate_root / "data.yaml").read_text(encoding="utf-8"):
        raise ValueError("Candidate data YAML must omit test")
    return receipt



def prepare_development_stress(source_root: Path, work_dir: Path, seed: int) -> dict[str, Path]:
    """Read val images only; create identical deterministic inputs for both arms.

    These are correlated views of development-validation frames, NOT separate
    capture sessions, protected test results or calibration data.
    """
    _, val, _ = verify_split(source_root)
    if work_dir.exists():
        raise FileExistsError("Refusing to overwrite the development stress inventory")
    data: dict[str, Path] = {}
    for condition in CONDITIONS:
        root = work_dir / condition
        (root / "images/val").mkdir(parents=True)
        (root / "labels/val").mkdir(parents=True)
        for original in val:
            label = source_root / "labels/val" / (original.stem + ".txt")
            boxes = validate_label(label)
            with Image.open(original) as image:
                transformed, _ = augment(image, boxes, condition,
                                         rng_for(seed + 331, original.name, CONDITIONS.index(condition)))
                output = root / "images/val" / original.name
                if output.suffix.lower() in {".jpg", ".jpeg"}:
                    transformed.save(output, format="JPEG", quality=95, subsampling=0)
                else:
                    transformed.save(output)
            shutil.copyfile(label, root / "labels/val" / label.name)
        yaml = root / "data.yaml"
        yaml.write_text(f"path: {root.resolve()}\nval: images/val\nnames:\n  0: landing_pad\n",
                        encoding="utf-8")
        data[condition] = yaml
    return data


def parameters(*, data_yaml: Path, project: Path, name: str, epochs: int,
               imgsz: int, batch: int, seed: int, device: str) -> dict:
    if epochs < 1 or imgsz < 64 or batch < 1 or name not in {"baseline", "candidate"}:
        raise ValueError("Invalid training setup")
    return dict(data=str(data_yaml.resolve()), epochs=epochs, imgsz=imgsz, batch=batch,
                device=device, workers=0, seed=seed, deterministic=True, patience=epochs,
                optimizer="SGD", cos_lr=False, cache=False, plots=False, verbose=False,
                degrees=0.0, translate=0.0, scale=0.0, shear=0.0, perspective=0.0,
                flipud=0.0, fliplr=0.0, mosaic=0.0, mixup=0.0, erasing=0.0,
                hsv_h=0.0, hsv_s=0.0, hsv_v=0.0,
                project=str(project.resolve()), name=name, exist_ok=False)


def train_pair(source_root: Path, candidate_root: Path, out: Path,
               *, initialization: str = "yolo11n.pt", epochs: int = 12,
               imgsz: int = 320, batch: int = 16, seed: int = 20261013,
               device: str = "cpu", model_factory=None) -> dict:
    if out.exists():
        raise FileExistsError("Refusing to overwrite a previous model comparison")
    verify_candidate(source_root, candidate_root)
    if model_factory is None:
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError("Install ultralytics to train the candidate") from exc
        model_factory = YOLO
    out.mkdir(parents=True)
    baseline_yaml = out / "baseline-dev-only.yaml"
    baseline_yaml.write_text(
        f"path: {source_root.resolve()}\ntrain: images/train\nval: images/val\nnames:\n  0: landing_pad\n",
        encoding="utf-8")
    stress = prepare_development_stress(source_root, out / "development-stress", seed)
    summaries = {}
    for label, yaml in (("baseline", baseline_yaml), ("candidate", candidate_root / "data.yaml")):
        model = model_factory(initialization)
        settings = parameters(data_yaml=yaml, project=out / "training", name=label,
                              epochs=epochs, imgsz=imgsz, batch=batch, seed=seed, device=device)
        result = model.train(**settings)
        best = Path(result.save_dir) / "weights" / "best.pt"
        if not best.is_file():
            raise FileNotFoundError(f"Missing {label} weights: {best}")
        evaluator = model_factory(str(best))
        metrics = evaluator.val(data=str(yaml.resolve()), split="val", imgsz=imgsz,
                                device=device, verbose=False, plots=False,
                                project=str((out / "validation").resolve()),
                                name=label, exist_ok=False)
        values = {"precision": float(metrics.box.mp), "recall": float(metrics.box.mr),
                  "map50": float(metrics.box.map50), "map50_95": float(metrics.box.map)}
        if any(not math.isfinite(value) for value in values.values()):
            raise ValueError("Nonfinite development metric")
        condition_metrics = {"clean": values}
        for condition, data in stress.items():
            degraded = evaluator.val(data=str(data.resolve()), split="val", imgsz=imgsz,
                                     device=device, verbose=False, plots=False,
                                     project=str((out / "validation").resolve()),
                                     name=f"{label}-{condition}", exist_ok=False)
            metrics_row = {"precision": float(degraded.box.mp),
                           "recall": float(degraded.box.mr),
                           "map50": float(degraded.box.map50),
                           "map50_95": float(degraded.box.map)}
            if any(not math.isfinite(value) for value in metrics_row.values()):
                raise ValueError("Nonfinite development stress metric")
            condition_metrics[condition] = metrics_row
        summaries[label] = {"weights_sha256": digest(best),
                            "weights_path": str(best.resolve()),
                            "metrics_val_only": values,
                            "development_validation_by_condition": condition_metrics,
                            "training_settings": settings}
    diff = {
        key: summaries["candidate"]["metrics_val_only"][key] - summaries["baseline"]["metrics_val_only"][key]
        for key in summaries["baseline"]["metrics_val_only"]
    }
    stress_diff = {
        condition: {metric: summaries["candidate"]["development_validation_by_condition"][condition][metric]
                    - summaries["baseline"]["development_validation_by_condition"][condition][metric]
                    for metric in diff}
        for condition in ("clean", *CONDITIONS)
    }
    report = {"schema": "aegisland.detector_robustness.development-comparison.v2",
              "status": "development_comparison_only",
              "initialization": initialization,
              "candidate_receipt_sha256": digest(candidate_root / "receipt.json"),
              "seed": seed, "epochs": epochs, "models": summaries,
              "matched_train_images_per_arm": len(list((candidate_root / "images/train").iterdir())),
              "matched_optimizer_step_budget": True,
              "validation_conditions": ["clean", *CONDITIONS],
              "candidate_minus_baseline": diff,
              "candidate_minus_baseline_by_condition": stress_diff,
              "protected_test_evaluated": False, "independent_validation": False,
              "model_improvement_established": False,
              "limits": "Validation shares the original KIOS sessions. No independent test or safe-flight claim."}
    (out / "comparison.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n",
                                         encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--candidate-root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--initialization", default="yolo11n.pt")
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--imgsz", type=int, default=320)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--seed", type=int, default=20261013)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    result = train_pair(args.source_root, args.candidate_root, args.out,
                        initialization=args.initialization, epochs=args.epochs,
                        imgsz=args.imgsz, batch=args.batch, seed=args.seed,
                        device=args.device)
    print(json.dumps({"status": result["status"],
                      "candidate_minus_baseline": result["candidate_minus_baseline"],
                      "independent_validation": False}, indent=2))


if __name__ == "__main__":
    main()
