from __future__ import annotations

from pathlib import Path
import argparse
import csv
import shutil

from uav_safety.real_landing_dataset import discover_samples, write_single_class_yolo
from uav_safety.real_split import temporal_split


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a leakage-aware YOLO split from the KIOS real-video subset.")
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("data/derived/kios_real_yolo"))
    parser.add_argument("--class-id", type=int, default=0, help="Source class to keep as landing_pad")
    args = parser.parse_args()

    samples = discover_samples(args.dataset_root, path_contains="real", class_id=args.class_id)
    if not samples:
        raise SystemExit("No labeled KIOS real-video images found")

    assignments = temporal_split(samples)
    if args.out.exists():
        shutil.rmtree(args.out)

    for split in ("train", "val", "test"):
        (args.out / "images" / split).mkdir(parents=True, exist_ok=True)
        (args.out / "labels" / split).mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str | int]] = []
    counts = {"train": 0, "val": 0, "embargo": 0, "test": 0}
    written_boxes = 0
    for item in assignments:
        counts[item.split] += 1
        rows.append({
            "sequence": item.sequence,
            "frame_index": item.frame_index,
            "split": item.split,
            "image": item.sample.image_path.name,
            "label": item.sample.label_path.name,
        })
        if item.split == "embargo":
            continue

        image_target = args.out / "images" / item.split / item.sample.image_path.name
        label_target = args.out / "labels" / item.split / item.sample.label_path.name
        shutil.copy2(item.sample.image_path, image_target)
        # The source KIOS labels include another class in many files.  This
        # derived benchmark is intentionally one-class, so write only the
        # selected landing-pad boxes and remap them to class 0.
        written_boxes += write_single_class_yolo(label_target, item.sample.boxes)

    with (args.out / "split_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["sequence", "frame_index", "split", "image", "label"])
        writer.writeheader()
        writer.writerows(rows)

    data_yaml = (
        f"path: {args.out.resolve()}\n"
        "train: images/train\n"
        "val: images/val\n"
        "test: images/test\n"
        "names:\n"
        "  0: landing_pad\n"
    )
    (args.out / "data.yaml").write_text(data_yaml, encoding="utf-8")

    summary = (
        "# KIOS real-video protected split\n\n"
        "Split each source video in temporal order: first 60% train, next 15% validation, "
        "next 5% embargoed/unused, final 20% protected test. The embargo reduces direct "
        "adjacent-frame leakage into the test segment. Source labels are filtered to the "
        f"target class {args.class_id} and rewritten as a one-class landing-pad dataset.\n\n"
        f"- train: **{counts['train']}**\n"
        f"- validation: **{counts['val']}**\n"
        f"- embargo: **{counts['embargo']}**\n"
        f"- test: **{counts['test']}**\n"
        f"- total labeled real frames: **{len(assignments)}**\n"
        f"- target boxes written: **{written_boxes}**\n"
    )
    (args.out / "SPLIT.md").write_text(summary, encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()
