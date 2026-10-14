#!/usr/bin/env python3
"""Paired development-only YOLO training. No protected test inference."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from scripts.prepare_detector_robustness_augmentation import digest, verify_split


def verify_candidate(source_root: Path, candidate_root: Path) -> dict:
    train, val, sha = verify_split(source_root)
    receipt = json.loads((candidate_root / "receipt.json").read_text(encoding="utf-8"))
    if (receipt.get("schema") != "aegisland.detector_robustness.development-only-aug.v1"
            or receipt.get("locked_split_sha256") != sha
            or receipt.get("protected_test_read") is not False
            or receipt.get("derived_val") != 0
            or receipt.get("original_train") != len(train)
            or receipt.get("original_val") != len(val)):
        raise ValueError("Candidate receipt fails locked split policy")
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
    for item in receipt["inventory"]:
        if digest(candidate_root / item["image"]) != item["image_sha256"]:
            raise ValueError("Candidate image hash differs from receipt")
    if (candidate_root / "images/test").exists() or (candidate_root / "labels/test").exists():
        raise ValueError("No protected test allowed in candidate")
    if "test:" in (candidate_root / "data.yaml").read_text(encoding="utf-8"):
        raise ValueError("Candidate data YAML must omit test")
    return receipt


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
        summaries[label] = {"weights_sha256": digest(best),
                            "weights_path": str(best.resolve()),
                            "metrics_val_only": values, "training_settings": settings}
    diff = {
        key: summaries["candidate"]["metrics_val_only"][key] - summaries["baseline"]["metrics_val_only"][key]
        for key in summaries["baseline"]["metrics_val_only"]
    }
    report = {"schema": "aegisland.detector_robustness.development-comparison.v1",
              "status": "development_comparison_only",
              "initialization": initialization,
              "candidate_receipt_sha256": digest(candidate_root / "receipt.json"),
              "seed": seed, "epochs": epochs, "models": summaries,
              "candidate_minus_baseline": diff,
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
