from __future__ import annotations

from pathlib import Path
import argparse
import json

import pandas as pd


def _metric_dict(metrics) -> dict[str, float]:
    return {
        "precision": float(metrics.box.mp),
        "recall": float(metrics.box.mr),
        "map50": float(metrics.box.map50),
        "map50_95": float(metrics.box.map),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a small YOLO detector on the protected KIOS real-video split.")
    parser.add_argument("--data", type=Path, required=True, help="YOLO data.yaml for train/val/test split")
    parser.add_argument("--stress-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("results/real_detector"))
    parser.add_argument("--model", default="yolo11n.pt")
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--imgsz", type=int, default=320)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--seed", type=int, default=20260915)
    args = parser.parse_args()

    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit("Install the real-model dependency first: pip install ultralytics") from exc

    args.out.mkdir(parents=True, exist_ok=True)
    train_project = args.out / "training"

    model = YOLO(args.model)
    train_result = model.train(
        data=str(args.data.resolve()),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device="cpu",
        workers=2,
        seed=args.seed,
        deterministic=True,
        patience=5,
        project=str(train_project.resolve()),
        name="landing_pad_yolo11n",
        exist_ok=True,
        cache=True,
        plots=False,
        verbose=False,
    )

    best_path = Path(train_result.save_dir) / "weights" / "best.pt"
    if not best_path.exists():
        raise FileNotFoundError(f"Training finished without best weights: {best_path}")
    best = YOLO(str(best_path))

    conditions = ["clean", "blur", "low_light", "noise", "occlusion", "mixed"]
    rows: list[dict[str, float | str]] = []
    for condition in conditions:
        yaml_path = args.stress_root / condition / "data.yaml"
        metrics = best.val(
            data=str(yaml_path.resolve()),
            split="test",
            imgsz=args.imgsz,
            batch=args.batch,
            device="cpu",
            workers=2,
            project=str((args.out / "validation").resolve()),
            name=condition,
            exist_ok=True,
            plots=False,
            verbose=False,
        )
        rows.append({"condition": condition, **_metric_dict(metrics)})

    frame = pd.DataFrame(rows)
    frame.to_csv(args.out / "robustness_metrics.csv", index=False)
    payload = {
        "model": args.model,
        "epochs_requested": args.epochs,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "seed": args.seed,
        "split_policy": "per-video temporal: 60% train, 15% validation, 5% embargo, 20% protected test",
        "conditions": rows,
    }
    (args.out / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    clean = frame.loc[frame.condition == "clean"].iloc[0]
    lines = [
        "# Real landing-pad detector benchmark",
        "",
        f"**Model:** `{args.model}` pretrained initialization, fine-tuned only on real-video development frames  ",
        f"**Training:** up to {args.epochs} epochs at {args.imgsz}px  ",
        "**Protected split:** temporal per source video, with a 5% embargo before the final test segment",
        "",
        "## Clean held-out result",
        "",
        f"- Precision: **{clean.precision:.3f}**",
        f"- Recall: **{clean.recall:.3f}**",
        f"- mAP50: **{clean.map50:.3f}**",
        f"- mAP50–95: **{clean.map50_95:.3f}**",
        "",
        "## Held-out robustness",
        "",
        "| Condition | Precision | Recall | mAP50 | mAP50–95 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['condition']} | {row['precision']:.3f} | {row['recall']:.3f} | {row['map50']:.3f} | {row['map50_95']:.3f} |"
        )
    lines += [
        "",
        "The stress images are deterministic transformations of the protected test frames. No stress condition is used for training in this first detector baseline.",
    ]
    (args.out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
