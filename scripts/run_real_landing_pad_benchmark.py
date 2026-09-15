from __future__ import annotations

from pathlib import Path
import argparse
import json

from uav_safety.real_landing_dataset import (
    discover_samples,
    evaluate_transfer_baseline,
    summarize_transfer,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate the frozen threshold-centroid baseline on labeled real landing-pad images."
    )
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument(
        "--path-contains",
        default="real",
        help="Only use image paths containing this text. Use an empty string to scan all domains.",
    )
    parser.add_argument("--class-id", type=int, default=None)
    parser.add_argument("--limit", type=int, default=0, help="Optional deterministic sample limit; 0 = all.")
    parser.add_argument("--out", type=Path, default=Path("results/real_landing_pad"))
    args = parser.parse_args()

    samples = discover_samples(
        args.dataset_root,
        path_contains=args.path_contains or None,
        class_id=args.class_id,
    )
    if args.limit > 0:
        samples = samples[: args.limit]
    if not samples:
        raise SystemExit(
            "No labeled image/YOLO pairs found. Check --dataset-root and --path-contains. "
            "For the KIOS archive, the real-video subset should contain 'real' in its path."
        )

    raw = evaluate_transfer_baseline(samples)
    summary = summarize_transfer(raw)

    args.out.mkdir(parents=True, exist_ok=True)
    raw.to_csv(args.out / "samples.csv", index=False)
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (args.out / "summary.md").write_text(
        "# Real landing-pad transfer baseline\n\n"
        "Dataset track: KIOS Aerial Landing Pad, Unreal Engine Dataset — real-video subset only.\n\n"
        "This evaluates the *existing* threshold-centroid heuristic without retraining. "
        "Because that baseline predicts horizontal position rather than a full object box, "
        "the primary metric is normalized horizontal center error. It is not an object-detection mAP result.\n\n"
        f"- Samples: **{summary['samples']}**\n"
        f"- Valid estimate rate: **{summary['valid_rate']:.3f}**\n"
        f"- Horizontal-center MAE (normalized image width): **{summary['x_center_mae_norm']:.4f}**\n"
        f"- Horizontal-center P95 error: **{summary['x_center_p95_norm']:.4f}**\n"
        f"- Predicted x inside annotated pad box: **{summary['x_inside_box_rate']:.3f}**\n"
        f"- Mean confidence: **{summary['mean_confidence']:.3f}**\n",
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2))
    print(f"Saved results to {args.out.resolve()}")


if __name__ == "__main__":
    main()
