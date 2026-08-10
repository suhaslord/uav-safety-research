from __future__ import annotations

from pathlib import Path
import argparse
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from uav_safety.image_perception import (
    IMAGE_CONDITIONS,
    SyntheticImageConfig,
    SyntheticLandingPadRenderer,
    ThresholdPadEstimator,
)


def run_benchmark(samples_per_condition: int, seed: int, severity: float) -> pd.DataFrame:
    if samples_per_condition < 1:
        raise ValueError("samples_per_condition must be >= 1")
    if severity <= 0:
        raise ValueError("severity must be > 0")

    rng = np.random.default_rng(seed)
    renderer = SyntheticLandingPadRenderer()
    estimator = ThresholdPadEstimator()
    rows: list[dict] = []

    for condition in IMAGE_CONDITIONS:
        for sample_id in range(samples_per_condition):
            x_true = float(rng.uniform(-2.2, 2.2))
            z_true = float(rng.uniform(0.8, 5.5))
            sample_seed = int(rng.integers(0, 2**31 - 1))
            sample_rng = np.random.default_rng(sample_seed)

            image = renderer.render(
                x_offset_m=x_true,
                altitude_m=z_true,
                rng=sample_rng,
                condition=condition,
                severity=severity,
            )
            estimate = estimator.estimate(image)
            abs_error = abs(estimate.x_m - x_true) if estimate.valid else np.nan

            rows.append({
                "condition": condition,
                "sample_id": sample_id,
                "sample_seed": sample_seed,
                "x_true_m": x_true,
                "altitude_m": z_true,
                "x_est_m": estimate.x_m if estimate.valid else np.nan,
                "abs_error_m": abs_error,
                "confidence": estimate.confidence,
                "valid": estimate.valid,
                "selected_pixels": estimate.selected_pixels,
            })

    return pd.DataFrame(rows)


def summarize(raw: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for condition, group in raw.groupby("condition", sort=False):
        valid = group[group["valid"]]
        if valid.empty:
            mae = np.nan
            p95 = np.nan
            corr = np.nan
        else:
            mae = float(valid["abs_error_m"].mean())
            p95 = float(valid["abs_error_m"].quantile(0.95))
            if len(valid) >= 3 and valid["confidence"].std() > 0 and valid["abs_error_m"].std() > 0:
                corr = float(valid["confidence"].corr(valid["abs_error_m"]))
            else:
                corr = np.nan

        rows.append({
            "condition": condition,
            "samples": len(group),
            "valid_rate": float(group["valid"].mean()),
            "invalid_rate": float(1.0 - group["valid"].mean()),
            "mae_x_m": mae,
            "p95_abs_error_m": p95,
            "mean_confidence": float(group["confidence"].mean()),
            "confidence_error_pearson": corr,
        })

    return pd.DataFrame(rows)


def save_examples(out: Path, seed: int, severity: float) -> None:
    rng = np.random.default_rng(seed + 991)
    renderer = SyntheticLandingPadRenderer()
    estimator = ThresholdPadEstimator()

    fig, axes = plt.subplots(1, len(IMAGE_CONDITIONS), figsize=(15, 3.2))
    for ax, condition in zip(axes, IMAGE_CONDITIONS):
        x_true = 0.85
        z_true = 2.5
        image = renderer.render(x_true, z_true, rng, condition, severity)
        estimate = estimator.estimate(image)
        ax.imshow(image, cmap="gray", vmin=0, vmax=1)
        ax.set_title(f"{condition}\ntrue={x_true:.2f}m est={estimate.x_m:.2f}m")
        ax.axis("off")
    plt.tight_layout()
    plt.savefig(out / "example_conditions.png", dpi=180)
    plt.close()


def save(raw: pd.DataFrame, summary: pd.DataFrame, out: Path, seed: int, severity: float) -> None:
    out.mkdir(parents=True, exist_ok=True)
    raw.to_csv(out / "samples.csv", index=False)
    summary.to_csv(out / "summary.csv", index=False)
    (out / "run_metadata.json").write_text(json.dumps({
        "seed": seed,
        "severity": severity,
        "conditions": list(IMAGE_CONDITIONS),
        "renderer": "synthetic landing-pad rasterizer",
        "estimator": "interpretable threshold centroid",
        "scope": "simulation-only; not calibrated camera physics",
        "config": SyntheticImageConfig().__dict__,
    }, indent=2), encoding="utf-8")

    (out / "summary.md").write_text(
        "# Synthetic image-perception benchmark\n\n"
        "This benchmark is a simulation-only bridge from state-level perception "
        "stress models toward pixel-based experiments. It is not a real-camera "
        "validation.\n\n"
        + summary.to_markdown(index=False)
        + "\n",
        encoding="utf-8",
    )

    summary.set_index("condition")["mae_x_m"].plot(kind="bar")
    plt.ylabel("Mean absolute lateral error (m)")
    plt.xlabel("Image condition")
    plt.title("Synthetic image lateral-estimation error")
    plt.tight_layout()
    plt.savefig(out / "mae_by_condition.png", dpi=180)
    plt.close()

    summary.set_index("condition")["valid_rate"].plot(kind="bar")
    plt.ylabel("Valid estimate rate")
    plt.xlabel("Image condition")
    plt.ylim(0, 1)
    plt.title("Synthetic image estimator availability")
    plt.tight_layout()
    plt.savefig(out / "valid_rate.png", dpi=180)
    plt.close()

    save_examples(out, seed, severity)


def main() -> None:
    parser = argparse.ArgumentParser(description="Synthetic pixel-based landing-pad perception benchmark.")
    parser.add_argument("--samples", type=int, default=300, help="Samples per image condition.")
    parser.add_argument("--seed", type=int, default=606060)
    parser.add_argument("--severity", type=float, default=1.0)
    parser.add_argument("--out", type=Path, default=Path("results/image_perception"))
    args = parser.parse_args()

    raw = run_benchmark(args.samples, args.seed, args.severity)
    summary = summarize(raw)
    save(raw, summary, args.out, args.seed, args.severity)
    print(summary.to_string(index=False))
    print(f"\nSaved image-perception benchmark to {args.out.resolve()}")


if __name__ == "__main__":
    main()
