"""Shared, deterministic helpers for the Phase 25 frame-level audit."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence
import csv
import hashlib
import json
import math
import re

import numpy as np
from PIL import Image
from phase25_reconstruction_lock import LOCK_PATH, load_lock, verify_archive, verify_images


CONDITIONS = ("clean", "blur", "low_light", "noise", "occlusion", "mixed")
TRANSITIONS = ("recovered", "regressed", "both_succeeded", "both_failed")
PROTECTED_MANIFEST_SHA256 = "8605cf1cbf9e8769c0324bf066078f9964f232ac3128131c8bd0b689bb7b64b7"
BASELINE_CHECKPOINT_SHA256 = "3a1801b192d624f8dcdda4bc5d9a9157309000df67a4c30d62368c37901feddd"
BASELINE_ARTIFACT_ID = 10382104202
BASELINE_ARTIFACT_SHA256 = "7080c8243c1d7cb85a63f81ea0531eda34dd1f18616f7b4dfdc869a2379c9833"
INPUT_LOCK_PATH = Path(__file__).resolve().parents[1] / "docs/phase25_input_lock.json"


@dataclass(frozen=True)
class Box:
    """A normalized xyxy box and its class/score."""

    class_id: int
    x0: float
    y0: float
    x1: float
    y1: float
    confidence: float | None = None


@dataclass(frozen=True)
class BoxMatch:
    prediction_index: int
    ground_truth_index: int | None
    iou: float
    is_true_positive: bool


def box_from_yolo(class_id: int, x_center: float, y_center: float, width: float, height: float) -> Box:
    values = (x_center, y_center, width, height)
    if any(not math.isfinite(value) or not 0.0 <= value <= 1.0 for value in values) or width <= 0 or height <= 0:
        raise ValueError("YOLO boxes must be normalized to [0, 1] with positive size")
    x0, y0 = x_center - width / 2, y_center - height / 2
    x1, y1 = x_center + width / 2, y_center + height / 2
    # KIOS writes six-decimal YOLO labels; one frozen edge box ends at
    # 1.0000005 after converting its rounded center and height.
    if not -1e-6 <= x0 < x1 <= 1 + 1e-6 or not -1e-6 <= y0 < y1 <= 1 + 1e-6:
        raise ValueError("YOLO box extends outside the image")
    return Box(class_id, max(0., x0), max(0., y0), min(1., x1), min(1., y1))


def image_features(path: Path, ground_truth: Sequence[Box]) -> dict[str, float | None]:
    """Return simple descriptive image and largest-target features."""
    with Image.open(path) as image:
        gray = np.asarray(image.convert("L"), dtype=np.float64) / 255.0
    if min(gray.shape) < 2:
        raise ValueError(f"Image is too small for the sharpness measure: {path}")
    dx = np.diff(gray, axis=1)
    dy = np.diff(gray, axis=0)
    target = max(ground_truth, key=lambda box: (box.x1 - box.x0) * (box.y1 - box.y0), default=None)
    if target is None:
        area = center_x = center_y = edge_distance = None
    else:
        area = (target.x1 - target.x0) * (target.y1 - target.y0)
        center_x = (target.x0 + target.x1) / 2
        center_y = (target.y0 + target.y1) / 2
        edge_distance = min(center_x, 1 - center_x, center_y, 1 - center_y)
    return {
        "target_area_ratio": area,
        "target_center_x": center_x,
        "target_center_y": center_y,
        "target_edge_distance": edge_distance,
        "brightness_mean": float(gray.mean()),
        "contrast_std": float(gray.std()),
        "sharpness_gradient_energy": float((np.mean(dx * dx) + np.mean(dy * dy)) / 2),
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_input_lock(path: Path = INPUT_LOCK_PATH) -> dict[str, object]:
    """Load and validate the committed Phase 25 provenance lock."""
    try:
        lock = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read Phase 25 input lock: {path}") from exc
    try:
        baseline = lock["phase22_baseline"]
        phase23 = lock["phase23_robust"]
        protected_split = lock["protected_split"]
        manifest_hash = lock["protected_manifest_sha256"]
        baseline_hash = baseline["checkpoint_sha256"]
        phase23_hash = phase23["checkpoint_sha256"]
    except (KeyError, TypeError) as exc:
        raise ValueError("Phase 25 input lock is missing required provenance fields") from exc

    if baseline.get("actions_artifact_id") != BASELINE_ARTIFACT_ID:
        raise ValueError("Phase 22 Actions artifact ID differs from the recovered baseline")
    if baseline.get("artifact_sha256") != BASELINE_ARTIFACT_SHA256:
        raise ValueError("Phase 22 artifact hash differs from the recovered baseline")
    if baseline_hash != BASELINE_CHECKPOINT_SHA256:
        raise ValueError("Phase 22 checkpoint hash differs from the recovered baseline")
    if manifest_hash != PROTECTED_MANIFEST_SHA256:
        raise ValueError("Protected manifest hash differs from the frozen Phase 25 IDs")
    if not isinstance(phase23_hash, str) or re.fullmatch(r"[0-9a-fA-F]{64}", phase23_hash) is None:
        raise ValueError(
            "Exact Phase 23 checkpoint is not locked; recover the original checkpoint, "
            "record its source and SHA-256 in docs/phase25_input_lock.json, then rerun"
        )
    if not isinstance(phase23.get("checkpoint_source"), str) or not phase23["checkpoint_source"].strip():
        raise ValueError("Phase 23 checkpoint source is not documented in the input lock")
    runtime = lock.get("phase25_runtime")
    if not isinstance(runtime, dict):
        raise ValueError("Phase 25 runtime versions are missing from the input lock")
    for package in ("python_version", "ultralytics_version", "torch_version", "numpy_version", "pillow_version"):
        version = runtime.get(package)
        if not isinstance(version, str) or not version.strip():
            raise ValueError(
                "Original detector inference software versions are not locked; recover the "
                "versions from the Phase 23 checkpoint or evaluation environment, record "
                "them in docs/phase25_input_lock.json, then rerun"
            )
    inference = lock.get("inference_settings")
    required_models = {"baseline", "phase23"}
    if not isinstance(inference, dict) or set(inference) != required_models | {"metric_tolerance", "frame_match_iou"}:
        raise ValueError("Frozen Phase 25 inference settings are missing or contain unexpected sections")
    setting_fields = {"imgsz", "confidence_floor", "nms_iou", "max_det", "batch", "workers", "device"}
    for model in required_models:
        settings = inference.get(model)
        if not isinstance(settings, dict) or set(settings) != setting_fields:
            raise ValueError(f"Frozen Phase 25 settings are incomplete for {model}")
    if inference["metric_tolerance"] != 0.001 or inference["frame_match_iou"] != 0.5:
        raise ValueError("Phase 25 aggregate tolerance and frame matching rule must remain frozen")
    return lock


def read_protected_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"sequence", "frame_index", "image", "label"}
        if not required.issubset(reader.fieldnames or ()):
            raise ValueError(f"Protected manifest must contain {sorted(required)}")
        rows = list(reader)
    if not rows:
        raise ValueError("Protected manifest contains no frames")
    image_names = [row["image"] for row in rows]
    if len(set(image_names)) != len(image_names):
        raise ValueError("Protected manifest contains duplicate image names")
    return rows


def _validate_target_label(text: str, path: Path) -> int:
    """Reject malformed or non-pad labels before running either detector."""
    count = 0
    for raw in text.splitlines():
        parts = raw.split()
        if len(parts) != 5 or parts[0] != "0":
            raise ValueError(f"Expected one-class landing-pad YOLO labels in {path}: {raw!r}")
        try:
            box_from_yolo(0, *(float(value) for value in parts[1:]))
        except ValueError as exc:
            raise ValueError(f"Invalid landing-pad target in {path}: {raw!r}") from exc
        count += 1
    if not count:
        raise ValueError(f"Protected frame has no target labels: {path}")
    return count


def validate_phase25_inputs(
    *,
    archive: Path | None = None,
    source_root: Path,
    stress_root: Path,
    baseline_weights: Path,
    phase23_weights: Path,
    protected_manifest: Path,
    input_lock: Path = INPUT_LOCK_PATH,
) -> dict[str, object]:
    """Validate the frozen inputs and return a hashable inventory.

    This function intentionally does not download, regenerate, or overwrite
    any dataset files. The caller must supply the original artifacts.
    """
    lock = load_input_lock(input_lock)
    if archive is None:
        raise ValueError("The checksum-verified KIOS source archive is required for the reconstruction gate")
    expected_phase23_sha256 = str(lock["phase23_robust"]["checkpoint_sha256"]).lower()
    for name, path in (
        ("KIOS source archive", archive),
        ("source dataset", source_root),
        ("stress dataset", stress_root),
        ("baseline weights", baseline_weights),
        ("Phase 23 weights", phase23_weights),
        ("protected manifest", protected_manifest),
    ):
        if not path.exists():
            raise FileNotFoundError(f"Missing {name}: {path}")

    rows = read_protected_manifest(protected_manifest)
    manifest_bytes = protected_manifest.read_bytes()
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
    if manifest_hash != PROTECTED_MANIFEST_SHA256:
        norm_crlf = hashlib.sha256(manifest_bytes.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")).hexdigest()
        norm_lf = hashlib.sha256(manifest_bytes.replace(b"\r\n", b"\n")).hexdigest()
        if norm_crlf == PROTECTED_MANIFEST_SHA256 or norm_lf == PROTECTED_MANIFEST_SHA256:
            manifest_hash = PROTECTED_MANIFEST_SHA256
    if manifest_hash != PROTECTED_MANIFEST_SHA256:
        raise ValueError("Protected manifest hash does not match the frozen Phase 25 IDs")
    if len(rows) != 86:
        raise ValueError(f"Expected 86 protected frames, found {len(rows)}")
    sequence_counts = _count_values(row["sequence"] for row in rows)
    protected_split = lock["protected_split"]
    if len(rows) != protected_split["frame_count"]:
        raise ValueError(f"Protected manifest frame count changed: {len(rows)}")
    if sequence_counts != protected_split["sequence_counts"]:
        raise ValueError(f"Protected source-sequence counts changed: {sequence_counts}")
    baseline_hash = sha256_file(baseline_weights)
    if baseline_hash != BASELINE_CHECKPOINT_SHA256:
        raise ValueError("Baseline checkpoint hash does not match the frozen Phase 22 model")
    phase23_hash = sha256_file(phase23_weights)
    if phase23_hash != expected_phase23_sha256:
        raise ValueError("Phase 23 checkpoint hash does not match the supplied frozen hash")
    expected_images = {row["image"] for row in rows}
    expected_labels = {row["label"] for row in rows}
    source_images = source_root / "images" / "test"
    source_labels = source_root / "labels" / "test"
    for directory in (source_images, source_labels):
        if not directory.is_dir():
            raise FileNotFoundError(f"Missing protected split directory: {directory}")

    def names(directory: Path, suffixes: set[str]) -> set[str]:
        return {
            path.name
            for path in directory.iterdir()
            if path.is_file() and path.suffix.lower() in suffixes
        }

    image_suffixes = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
    source_image_names = names(source_images, image_suffixes)
    source_label_names = names(source_labels, {".txt"})
    if source_image_names != expected_images:
        raise ValueError("Source protected images do not match the frozen manifest")
    if source_label_names != expected_labels:
        raise ValueError("Source protected labels do not match the frozen manifest")

    inventory: list[dict[str, str]] = []
    condition_paths: dict[str, list[Path]] = {}
    source_label_text: dict[str, str] = {}
    for row in rows:
        label_path = source_labels / row["label"]
        text = label_path.read_text(encoding="utf-8").strip()
        _validate_target_label(text, label_path)
        source_label_text[row["image"]] = text
        inventory.append({"kind": "source_image", "path": f"source/images/test/{row['image']}", "sha256": sha256_file(source_images / row["image"])})
        inventory.append({"kind": "source_label", "path": f"source/labels/test/{row['label']}", "sha256": sha256_file(label_path)})

    for condition in CONDITIONS:
        image_dir = stress_root / condition / "images" / "test"
        label_dir = stress_root / condition / "labels" / "test"
        if not image_dir.is_dir() or not label_dir.is_dir():
            raise FileNotFoundError(f"Missing {condition} image or label directory")
        image_names = names(image_dir, image_suffixes)
        label_names = names(label_dir, {".txt"})
        if image_names != expected_images:
            raise ValueError(f"{condition} images do not match the frozen manifest")
        if label_names != expected_labels:
            raise ValueError(f"{condition} labels do not match the frozen manifest")
        paths = [image_dir / row["image"] for row in rows]
        condition_paths[condition] = paths
        for row in rows:
            label_path = label_dir / row["label"]
            if label_path.read_text(encoding="utf-8").strip() != source_label_text[row["image"]]:
                raise ValueError(f"{condition} changed labels for {row['image']}")
            inventory.append({"kind": f"{condition}_image", "path": f"stress/{condition}/images/test/{row['image']}", "sha256": sha256_file(image_dir / row["image"])})
            inventory.append({"kind": f"{condition}_label", "path": f"stress/{condition}/labels/test/{row['label']}", "sha256": sha256_file(label_path)})

    reconstruction = load_lock()
    verify_archive(archive, reconstruction)
    condition_digests = verify_images(rows, source_root, stress_root, reconstruction)

    return {
        "frame_count": len(rows),
        "condition_count": len(CONDITIONS),
        "frame_condition_count": len(rows) * len(CONDITIONS),
        "sequence_counts": sequence_counts,
        "frames": rows,
        "condition_paths": condition_paths,
        "inventory": inventory,
        "manifest_sha256": manifest_hash,
        "baseline_weights_sha256": baseline_hash,
        "phase23_weights_sha256": phase23_hash,
        "input_lock_sha256": sha256_file(input_lock),
        "reconstruction_lock_sha256": sha256_file(LOCK_PATH),
        "source_archive_sha256": reconstruction["zenodo_archive_sha256"],
        "condition_image_inventory_sha256": condition_digests,
        "baseline_actions_artifact_id": BASELINE_ARTIFACT_ID,
        "baseline_actions_artifact_sha256": BASELINE_ARTIFACT_SHA256,
        "input_lock": lock,
    }


def _count_values(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def iou_xyxy(left: Box, right: Box) -> float:
    x0 = max(left.x0, right.x0)
    y0 = max(left.y0, right.y0)
    x1 = min(left.x1, right.x1)
    y1 = min(left.y1, right.y1)
    intersection = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    left_area = max(0.0, left.x1 - left.x0) * max(0.0, left.y1 - left.y0)
    right_area = max(0.0, right.x1 - right.x0) * max(0.0, right.y1 - right.y0)
    union = left_area + right_area - intersection
    return intersection / union if union > 0 else 0.0


def match_predictions(
    ground_truth: Sequence[Box],
    predictions: Sequence[Box],
    *,
    iou_threshold: float = 0.5,
) -> list[BoxMatch]:
    """Match confidence-ranked predictions to one unmatched same-class GT.

    Predictions are processed in descending confidence order, matching the
    usual detection-evaluation interpretation. Duplicate detections become
    false positives. The returned list follows the caller's prediction order.
    """
    if not 0.0 <= iou_threshold <= 1.0:
        raise ValueError("IoU threshold must be between 0 and 1")
    for box in ground_truth:
        coords = (box.x0, box.y0, box.x1, box.y1)
        if (box.class_id < 0 or any(not math.isfinite(value) for value in coords)
                or not 0.0 <= box.x0 < box.x1 <= 1.0 or not 0.0 <= box.y0 < box.y1 <= 1.0):
            raise ValueError("Matching requires finite, normalized, positive-area ground-truth boxes")
    for box in predictions:
        coords = (box.x0, box.y0, box.x1, box.y1)
        if (box.class_id < 0 or any(not math.isfinite(value) for value in coords)
                or not 0.0 <= box.x0 <= box.x1 <= 1.0 or not 0.0 <= box.y0 <= box.y1 <= 1.0):
            raise ValueError("Matching requires finite, normalized prediction boxes")
        # A predicted box can collapse against the image edge after clipping.
        # Retain it as a false positive rather than silently changing the box count.
    if any(box.confidence is None or not math.isfinite(box.confidence) or not 0.0 <= box.confidence <= 1.0 for box in predictions):
        raise ValueError("Every prediction needs a finite confidence in [0, 1]")
    ranked = sorted(range(len(predictions)), key=lambda i: (-float(predictions[i].confidence), i))
    unmatched = set(range(len(ground_truth)))
    matches: dict[int, BoxMatch] = {}
    for pred_index in ranked:
        prediction = predictions[pred_index]
        overlaps = [
            (iou_xyxy(prediction, gt), gt_index)
            for gt_index, gt in enumerate(ground_truth)
            if (gt_index in unmatched and gt.class_id == prediction.class_id
                and prediction.x0 < prediction.x1 and prediction.y0 < prediction.y1)
        ]
        best_iou, best_gt = max(overlaps, default=(0.0, None), key=lambda pair: (pair[0], -(pair[1] or 0)))
        if best_gt is not None and best_iou >= iou_threshold:
            unmatched.remove(best_gt)
            matches[pred_index] = BoxMatch(pred_index, best_gt, best_iou, True)
        else:
            # Retain the best same-class overlap for failure analysis even
            # when it falls below the TP threshold or its GT is already used.
            all_overlaps = [
                iou_xyxy(prediction, gt)
                for gt in ground_truth
                if gt.class_id == prediction.class_id
            ]
            matches[pred_index] = BoxMatch(pred_index, None, max(all_overlaps, default=0.0), False)
    return [matches[index] for index in range(len(predictions))]


def frame_metrics(
    ground_truth: Sequence[Box],
    predictions: Sequence[Box],
    *,
    iou_threshold: float = 0.5,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    matches = match_predictions(ground_truth, predictions, iou_threshold=iou_threshold)
    tp = sum(match.is_true_positive for match in matches)
    fp = len(matches) - tp
    fn = len(ground_truth) - tp
    best_tp = max((predictions[m.prediction_index].confidence or 0.0 for m in matches if m.is_true_positive), default=None)
    frame = {
        "gt_count": len(ground_truth),
        "detection_count": len(predictions),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "frame_success": bool(ground_truth) and tp == len(ground_truth),
        "best_confidence_any": max((float(box.confidence) for box in predictions), default=None),
        "best_confidence_tp": best_tp,
        "best_iou": max((match.iou for match in matches), default=0.0),
    }
    prediction_rows = [
        {
            "prediction_index": match.prediction_index,
            "class_id": predictions[match.prediction_index].class_id,
            "x0": predictions[match.prediction_index].x0,
            "y0": predictions[match.prediction_index].y0,
            "x1": predictions[match.prediction_index].x1,
            "y1": predictions[match.prediction_index].y1,
            "confidence": predictions[match.prediction_index].confidence,
            "matched_gt_index": match.ground_truth_index,
            "match_iou": match.iou,
            "is_true_positive": match.is_true_positive,
        }
        for match in matches
    ]
    return frame, prediction_rows


def outcome_transition(baseline_success: bool, phase23_success: bool) -> str:
    if not baseline_success and phase23_success:
        return "recovered"
    if baseline_success and not phase23_success:
        return "regressed"
    return "both_succeeded" if baseline_success else "both_failed"


def calibration_summary(predictions: Sequence[Mapping[str, object]], *, bins: int = 10) -> tuple[list[dict[str, object]], dict[str, float | int | None]]:
    if bins < 1:
        raise ValueError("bins must be positive")
    rows: list[dict[str, object]] = []
    scores: list[float] = []
    outcomes: list[float] = []
    for row in predictions:
        score = float(row["confidence"])
        outcome_value = row["is_true_positive"]
        if type(outcome_value) is not bool:
            raise ValueError("Box correctness must be a boolean")
        outcome = float(outcome_value)
        if not math.isfinite(score) or not 0.0 <= score <= 1.0:
            raise ValueError("Confidence must be in [0, 1]")
        scores.append(score)
        outcomes.append(outcome)
    ece = 0.0
    for index in range(bins):
        lo, hi = index / bins, (index + 1) / bins
        selected = [i for i, score in enumerate(scores) if lo <= score < hi or (index == bins - 1 and score == 1.0)]
        mean_score = float(np.mean([scores[i] for i in selected])) if selected else None
        accuracy = float(np.mean([outcomes[i] for i in selected])) if selected else None
        count = len(selected)
        if count:
            ece += count / max(1, len(scores)) * abs(mean_score - accuracy)
        rows.append({"bin_lower": lo, "bin_upper": hi, "count": count, "mean_confidence": mean_score, "empirical_box_correctness": accuracy})
    brier = float(np.mean([(score - outcome) ** 2 for score, outcome in zip(scores, outcomes, strict=True)])) if scores else None
    return rows, {"prediction_count": len(scores), "ece": ece if scores else None, "brier_score": brier}


def clustered_bootstrap_delta(
    rows: Sequence[Mapping[str, object]],
    *,
    minimum_groups: int = 10,
    replicates: int = 2000,
    seed: int = 25025,
) -> dict[str, object] | None:
    """Paired frame-success interval, resampling independent source groups."""
    grouped: dict[str, list[Mapping[str, object]]] = {}
    for row in rows:
        grouped.setdefault(str(row["sequence"]), []).append(row)
    if len(grouped) < minimum_groups:
        return None
    group_names = sorted(grouped)

    def delta(sampled: Sequence[str]) -> float:
        sample_rows = [row for name in sampled for row in grouped[name]]
        return float(np.mean([bool(row["phase23_success"]) for row in sample_rows]) - np.mean([bool(row["baseline_success"]) for row in sample_rows]))

    point = delta(group_names)
    rng = np.random.default_rng(seed)
    estimates = [delta(rng.choice(group_names, size=len(group_names), replace=True).tolist()) for _ in range(replicates)]
    lower, upper = np.quantile(estimates, [0.025, 0.975])
    return {"groups": len(group_names), "replicates": replicates, "difference": point, "ci95_low": float(lower), "ci95_high": float(upper), "seed": seed}
