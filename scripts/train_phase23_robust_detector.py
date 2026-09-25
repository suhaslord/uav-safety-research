from __future__ import annotations

from pathlib import Path
import argparse
import json
import torch

import pandas as pd


CONDITIONS = ("clean", "blur", "low_light", "noise", "occlusion", "mixed")


def _metric_dict(metrics) -> dict[str, float]:
    return {
        "precision": float(metrics.box.mp),
        "recall": float(metrics.box.mr),
        "map50": float(metrics.box.map50),
        "map50_95": float(metrics.box.map),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Phase 23 robust UAV landing detector on KIOS real-video split.")
    parser.add_argument("--data", type=Path, default=Path("data/derived/kios_real_yolo/data.yaml"))
    parser.add_argument("--stress-root", type=Path, default=Path("data/derived/kios_real_stress"))
    parser.add_argument("--out", type=Path, default=Path("results/phase23_robust_detector"))
    parser.add_argument("--model", default="yolo11n.pt")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--imgsz", type=int, default=480)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--seed", type=int, default=20260922)
    args = parser.parse_args()

    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit("Install ultralytics first: pip install ultralytics") from exc

    args.out.mkdir(parents=True, exist_ok=True)
    train_project = args.out / "training"
    device = "0" if torch.cuda.is_available() else "cpu"

    print(f"Starting Phase 23 robust training on device={device}, imgsz={args.imgsz}, epochs={args.epochs}...")

    model = YOLO(args.model)
    train_result = model.train(
        data=str(args.data.resolve()),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=device,
        workers=2,
        seed=args.seed,
        deterministic=True,
        patience=10,
        cos_lr=True,
        # UAV-tailored domain augmentations
        degrees=15.0,     # Drone yaw / landing pad rotation
        scale=0.35,       # Approach altitude scaling
        mosaic=1.0,       # Multi-scale composition
        mixup=0.15,       # Blend robustness
        erasing=0.35,     # Partial occlusion / landing gear obstruction
        hsv_h=0.015,
        hsv_s=0.5,
        hsv_v=0.4,        # Sun glare and shadow transitions
        fliplr=0.5,
        project=str(train_project.resolve()),
        name="phase23_robust_yolo11n",
        exist_ok=True,
        cache=True,
        plots=False,
        verbose=False,
    )

    best_path = Path(train_result.save_dir) / "weights" / "best.pt"
    if not best_path.exists():
        raise FileNotFoundError(f"Training finished without best weights: {best_path}")

    print(f"Training complete. Best weights: {best_path}")
    print("Evaluating held-out stress conditions on protected test set...")

    robust_model = YOLO(str(best_path))
    rows: list[dict[str, float | str]] = []

    for condition in CONDITIONS:
        stress_data = args.stress_root / condition / "data.yaml"
        metrics = robust_model.val(
            data=str(stress_data.resolve()),
            split="test",
            imgsz=args.imgsz,
            device=device,
            verbose=False,
            plots=False,
        )
        row = {"condition": condition, **_metric_dict(metrics)}
        rows.append(row)
        print(f"[{condition.upper():9s}] Precision: {row['precision']:.3f} | Recall: {row['recall']:.3f} | mAP50: {row['map50']:.3f} | mAP50-95: {row['map50_95']:.3f}")

    df = pd.DataFrame(rows)
    metrics_path = args.out / "robustness_metrics.csv"
    df.to_csv(metrics_path, index=False)

    # Read baseline metrics for direct comparison
    baseline_metrics_path = Path("results/real_detector/robustness_metrics.csv")
    if not baseline_metrics_path.exists():
        baseline_metrics_path = Path("temp_kios_artifact/kios-real-detector-baseline/robustness_metrics.csv")

    comparison_rows = []
    if baseline_metrics_path.exists():
        baseline_df = pd.read_csv(baseline_metrics_path).set_index("condition")
        for row in rows:
            c = row["condition"]
            if c in baseline_df.index:
                b_map50 = float(baseline_df.loc[c, "map50"])
                b_rec = float(baseline_df.loc[c, "recall"])
                r_map50 = row["map50"]
                r_rec = row["recall"]
                comparison_rows.append({
                    "condition": c,
                    "baseline_recall": b_rec,
                    "phase23_recall": r_rec,
                    "recall_gain": r_rec - b_rec,
                    "baseline_map50": b_map50,
                    "phase23_map50": r_map50,
                    "map50_gain": r_map50 - b_map50,
                })
        comp_df = pd.DataFrame(comparison_rows)
        comp_df.to_csv(args.out / "robustness_comparison.csv", index=False)

    summary_json = {
        "phase": "phase23",
        "title": "Phase 23 · Robust Sim-to-Real Landing Perception",
        "dataset": "KIOS Aerial Landing Pad, Unreal Engine Dataset (2024)",
        "model": "yolo11n-phase23-robust",
        "imgsz": args.imgsz,
        "epochs": args.epochs,
        "metrics": {r["condition"]: r for r in rows},
    }
    (args.out / "summary.json").write_text(json.dumps(summary_json, indent=2), encoding="utf-8")

    # Generate Markdown Summary
    clean_row = df[df["condition"] == "clean"].iloc[0]
    mixed_row = df[df["condition"] == "mixed"].iloc[0]
    occ_row = df[df["condition"] == "occlusion"].iloc[0]

    md_lines = [
        "# Phase 23 · Robust Sim-to-Real Landing Perception",
        "",
        "**Status:** Detector comparison on the protected KIOS temporal holdout. Gains are condition-dependent and severe-stress regressions remain.",
        f"**Model:** YOLO11n ({args.imgsz}px, cosine LR, random erasing, photometrics, rotation)",
        "**Split:** Protected temporal split (86 test frames)",
        "",
        "## Clean Held-Out Results",
        "",
        "| Metric | Phase 22 Baseline | Phase 23 Robust | Delta |",
        "| :--- | :---: | :---: | :---: |",
        f"| Precision | 0.796 | **{clean_row['precision']:.3f}** | {clean_row['precision'] - 0.796:+.3f} |",
        f"| Recall | 0.384 | **{clean_row['recall']:.3f}** | {clean_row['recall'] - 0.384:+.3f} |",
        f"| mAP50 | 0.427 | **{clean_row['map50']:.3f}** | {clean_row['map50'] - 0.427:+.3f} |",
        f"| mAP50–95 | 0.272 | **{clean_row['map50_95']:.3f}** | {clean_row['map50_95'] - 0.272:+.3f} |",
        "",
        "## Robustness Across All 6 Protected Conditions",
        "",
        "| Condition | Baseline mAP50 | Phase 23 mAP50 | Baseline Recall | Phase 23 Recall |",
        "| :--- | :---: | :---: | :---: | :---: |",
    ]
    for row in rows:
        c = row["condition"]
        b_map = float(baseline_df.loc[c, "map50"]) if baseline_metrics_path.exists() and c in baseline_df.index else 0.0
        b_rec = float(baseline_df.loc[c, "recall"]) if baseline_metrics_path.exists() and c in baseline_df.index else 0.0
        md_lines.append(f"| {c.capitalize()} | {b_map:.3f} | **{row['map50']:.3f}** | {b_rec:.3f} | **{row['recall']:.3f}** |")

    md_lines.extend([
        "",
        "## Readout",
        "",
        f"- **Clean recall**: {clean_row['recall'] - 0.384:+.3f} absolute ({(clean_row['recall'] - 0.384)*100:+.1f} percentage points) vs baseline.",
        f"- **Mixed stress**: mAP50 changed from **0.185** to **{mixed_row['map50']:.3f}** ({mixed_row['map50'] - 0.185:+.3f}); a negative delta is a regression.",
        f"- **Occlusion**: mAP50 changed from **0.348** to **{occ_row['map50']:.3f}** ({occ_row['map50'] - 0.348:+.3f}); a negative delta is a regression.",
        "",
        "These condition aggregates describe detector metrics on the protected KIOS temporal holdout. They do not establish sim-to-real equivalence, landing safety, controller behavior, or real-flight readiness.",
    ])

    summary_md = "\n".join(md_lines) + "\n"
    (args.out / "summary.md").write_text(summary_md, encoding="utf-8")
    print(f"Summary written to {args.out / 'summary.md'}")


if __name__ == "__main__":
    main()
