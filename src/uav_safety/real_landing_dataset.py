from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from PIL import Image

from .image_perception import SyntheticImageConfig, ThresholdPadEstimator


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


@dataclass(frozen=True)
class YoloBox:
    class_id: int
    x_center: float
    y_center: float
    width: float
    height: float

    @property
    def x0(self) -> float:
        return self.x_center - self.width / 2

    @property
    def x1(self) -> float:
        return self.x_center + self.width / 2

    @property
    def area(self) -> float:
        return self.width * self.height


@dataclass(frozen=True)
class RealLandingSample:
    image_path: Path
    label_path: Path
    boxes: tuple[YoloBox, ...]


def read_yolo_boxes(path: Path, class_id: int | None = None) -> tuple[YoloBox, ...]:
    boxes: list[YoloBox] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        parts = raw.split()
        if len(parts) < 5:
            raise ValueError(f"Malformed YOLO row in {path}: {raw!r}")
        box = YoloBox(
            class_id=int(float(parts[0])),
            x_center=float(parts[1]),
            y_center=float(parts[2]),
            width=float(parts[3]),
            height=float(parts[4]),
        )
        if class_id is None or box.class_id == class_id:
            boxes.append(box)
    return tuple(boxes)


def _label_candidates(image_path: Path, root: Path) -> Iterable[Path]:
    yield image_path.with_suffix(".txt")

    parts = list(image_path.parts)
    for index, part in enumerate(parts):
        if part.lower() == "images":
            replaced = parts.copy()
            replaced[index] = "labels"
            yield Path(*replaced).with_suffix(".txt")

    try:
        rel = image_path.relative_to(root)
    except ValueError:
        return

    rel_parts = list(rel.parts)
    for index, part in enumerate(rel_parts):
        if part.lower() == "images":
            replaced = rel_parts.copy()
            replaced[index] = "labels"
            yield root.joinpath(*replaced).with_suffix(".txt")


def discover_samples(
    root: Path,
    *,
    path_contains: str | None = None,
    class_id: int | None = None,
) -> list[RealLandingSample]:
    """Find image/YOLO-label pairs recursively.

    ``path_contains`` is useful for the KIOS dataset because the archive mixes
    simulated environments with a real-video subset. Passing ``"real"`` keeps
    the real-image benchmark separate from the synthetic domains.
    """

    root = root.resolve()
    images = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )
    if path_contains:
        needle = path_contains.lower()
        images = [path for path in images if needle in str(path.relative_to(root)).lower()]

    label_index: dict[str, list[Path]] = {}
    for label in root.rglob("*.txt"):
        label_index.setdefault(label.stem, []).append(label)

    samples: list[RealLandingSample] = []
    for image_path in images:
        label_path: Path | None = None
        for candidate in _label_candidates(image_path, root):
            if candidate.exists():
                label_path = candidate
                break
        if label_path is None:
            matches = label_index.get(image_path.stem, [])
            if len(matches) == 1:
                label_path = matches[0]
        if label_path is None:
            continue

        boxes = read_yolo_boxes(label_path, class_id=class_id)
        if not boxes:
            continue
        samples.append(RealLandingSample(image_path=image_path, label_path=label_path, boxes=boxes))

    return samples


def load_grayscale_for_estimator(
    image_path: Path,
    cfg: SyntheticImageConfig | None = None,
) -> np.ndarray:
    cfg = cfg or SyntheticImageConfig()
    with Image.open(image_path) as image:
        gray = image.convert("L").resize((cfg.image_size, cfg.image_size), Image.Resampling.BILINEAR)
        return np.asarray(gray, dtype=np.float64) / 255.0


def evaluate_transfer_baseline(
    samples: Iterable[RealLandingSample],
    *,
    estimator: ThresholdPadEstimator | None = None,
) -> pd.DataFrame:
    """Evaluate the old synthetic threshold-centroid heuristic on real images.

    This is deliberately *not* presented as object-detection performance. The
    estimator only predicts horizontal position, so the compatible real-image
    metric is horizontal landing-pad center error in normalized image units.
    """

    estimator = estimator or ThresholdPadEstimator()
    rows: list[dict] = []

    for sample in samples:
        image = load_grayscale_for_estimator(sample.image_path, estimator.cfg)
        estimate = estimator.estimate(image)
        target = max(sample.boxes, key=lambda box: box.area)

        if estimate.valid and np.isfinite(estimate.centroid_x_px):
            pred_x = estimate.centroid_x_px / max(1, image.shape[1] - 1)
            abs_error = abs(pred_x - target.x_center)
            inside = target.x0 <= pred_x <= target.x1
        else:
            pred_x = np.nan
            abs_error = np.nan
            inside = False

        rows.append(
            {
                "image": str(sample.image_path),
                "label": str(sample.label_path),
                "target_class": target.class_id,
                "gt_x_center_norm": target.x_center,
                "gt_width_norm": target.width,
                "pred_x_center_norm": pred_x,
                "x_center_abs_error_norm": abs_error,
                "pred_x_inside_gt_box": bool(inside),
                "confidence": estimate.confidence,
                "valid": estimate.valid,
                "selected_pixels": estimate.selected_pixels,
            }
        )

    return pd.DataFrame(rows)


def summarize_transfer(raw: pd.DataFrame) -> dict[str, float | int]:
    if raw.empty:
        raise ValueError("No labeled real-image samples were evaluated")

    valid = raw[raw["valid"]]
    return {
        "samples": int(len(raw)),
        "valid_rate": float(raw["valid"].mean()),
        "x_center_mae_norm": float(valid["x_center_abs_error_norm"].mean()) if not valid.empty else float("nan"),
        "x_center_p95_norm": float(valid["x_center_abs_error_norm"].quantile(0.95)) if not valid.empty else float("nan"),
        "x_inside_box_rate": float(valid["pred_x_inside_gt_box"].mean()) if not valid.empty else 0.0,
        "mean_confidence": float(raw["confidence"].mean()),
    }
