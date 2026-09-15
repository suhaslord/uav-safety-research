from pathlib import Path

import numpy as np
from PIL import Image

from uav_safety.real_landing_dataset import (
    YoloBox,
    discover_samples,
    evaluate_transfer_baseline,
    read_yolo_boxes,
    summarize_transfer,
    write_single_class_yolo,
)


def _write_fixture(root: Path) -> None:
    image_dir = root / "Real Video" / "images"
    label_dir = root / "Real Video" / "labels"
    image_dir.mkdir(parents=True)
    label_dir.mkdir(parents=True)

    image = np.zeros((96, 96), dtype=np.uint8) + 20
    image[32:64, 38:58] = 235
    Image.fromarray(image, mode="L").save(image_dir / "frame001.png")
    # class x_center y_center width height
    (label_dir / "frame001.txt").write_text("0 0.5 0.5 0.30 0.40\n", encoding="utf-8")


def test_read_yolo_boxes(tmp_path: Path) -> None:
    label = tmp_path / "label.txt"
    label.write_text("0 0.5 0.4 0.2 0.3\n1 0.2 0.2 0.1 0.1\n", encoding="utf-8")
    boxes = read_yolo_boxes(label, class_id=0)
    assert len(boxes) == 1
    assert boxes[0].x_center == 0.5
    assert boxes[0].x0 == 0.4
    assert boxes[0].x1 == 0.6


def test_write_single_class_yolo_drops_source_class_ids(tmp_path: Path) -> None:
    label = tmp_path / "derived.txt"
    boxes = (
        YoloBox(0, 0.5, 0.4, 0.2, 0.3),
        YoloBox(7, 0.25, 0.3, 0.1, 0.2),
    )
    assert write_single_class_yolo(label, boxes) == 2
    rows = label.read_text(encoding="utf-8").splitlines()
    assert len(rows) == 2
    assert all(row.startswith("0 ") for row in rows)
    assert read_yolo_boxes(label)[0].x_center == 0.5


def test_discover_and_evaluate_real_subset(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    samples = discover_samples(tmp_path, path_contains="real", class_id=0)
    assert len(samples) == 1

    raw = evaluate_transfer_baseline(samples)
    assert len(raw) == 1
    assert bool(raw.iloc[0]["valid"])
    assert float(raw.iloc[0]["x_center_abs_error_norm"]) < 0.08
    assert bool(raw.iloc[0]["pred_x_inside_gt_box"])

    summary = summarize_transfer(raw)
    assert summary["samples"] == 1
    assert summary["valid_rate"] == 1.0
    assert summary["x_inside_box_rate"] == 1.0
