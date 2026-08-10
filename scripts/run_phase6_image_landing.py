from __future__ import annotations

from pathlib import Path
import argparse
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from uav_safety.image_perception import IMAGE_CONDITIONS, SyntheticLandingPadRenderer
from uav_safety.image_temporal import Phase6PadEstimator, fit_synthetic_calibrator
from uav_safety.simulator_image_v3 import run_image_episode


ARCHITECTURES = ("image_temporal", "image_aegis_v3")


def _episode_seeds(seed: int, condition_index: int, episodes: int) -> list[int]:
    rng = np.random.default_rng(np.random.SeedSequence([seed, condition_index, 6060]))
    return [int(rng.integers(0, 2**31 - 1)) for _ in range(episodes)]


def run_comparison(
    *,
    episodes: int,
    seed: int,
    calibration_seed: int,
    calibration_samples: int,
    severity: float,
):
    calibrator = fit_synthetic_calibrator(
        seed=calibration_seed,
        samples_per_condition=calibration_samples,
    )

    rows: list[dict] = []
    for condition_index, condition in enumerate(IMAGE_CONDITIONS):
        for episode_seed in _episode_seeds(seed, condition_index, episodes):
            for architecture in ARCHITECTURES:
                result = run_image_episode(
                    episode_seed,
                    condition,
                    calibrator,
                    architecture=architecture,
                    severity=severity,
                )
                rows.append(result.to_dict())

    return pd.DataFrame(rows), calibrator


def summarize(raw: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for (condition, architecture), group in raw.groupby(["condition", "architecture"], sort=True):
        rows.append({
            "condition": condition,
            "architecture": architecture,
            "episodes": len(group),
            "success_rate": float(group["success"].mean()),
            "unsafe_touchdown_rate": float(group["unsafe_touchdown"].mean()),
            "abort_rate": float(group["aborted"].mean()),
            "timeout_rate": float((group["outcome"] == "timeout").mean()),
            "mean_image_abstention_rate": float(group["image_abstention_rate"].mean()),
            "mean_calibrated_confidence": float(group["mean_calibrated_confidence"].mean()),
            "mean_image_x_error_m": float(group["mean_image_x_error_m"].mean()),
            "p95_episode_image_x_error_m": float(group["p95_image_x_error_m"].quantile(0.95)),
            "mean_interventions": float(group["interventions"].mean()),
            "mean_final_x_error": float(group["final_x_error"].mean()),
        })
    return pd.DataFrame(rows)


def paired_effects(raw: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for condition, group in raw.groupby("condition", sort=True):
        temporal = group[group["architecture"] == "image_temporal"].set_index("seed")
        aegis = group[group["architecture"] == "image_aegis_v3"].set_index("seed")
        common = temporal.index.intersection(aegis.index)
        temporal = temporal.loc[common]
        aegis = aegis.loc[common]
        rows.append({
            "condition": condition,
            "paired_episodes": len(common),
            "aegis_minus_temporal_success_pp": 100 * float(aegis["success"].mean() - temporal["success"].mean()),
            "aegis_minus_temporal_unsafe_pp": 100 * float(aegis["unsafe_touchdown"].mean() - temporal["unsafe_touchdown"].mean()),
            "temporal_unsafe_rescued_to_aegis_success": int((temporal["unsafe_touchdown"] & aegis["success"]).sum()),
            "temporal_success_became_aegis_unsafe": int((temporal["success"] & aegis["unsafe_touchdown"]).sum()),
        })
    return pd.DataFrame(rows)


def calibration_audit(calibrator, *, seed: int, samples_per_condition: int = 120) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    renderer = SyntheticLandingPadRenderer()
    estimator = Phase6PadEstimator()
    rows: list[dict] = []

    for condition in IMAGE_CONDITIONS:
        for _ in range(samples_per_condition):
            x_true = float(rng.uniform(-2.1, 2.1))
            z_true = float(rng.uniform(0.8, 5.3))
            severity = float(rng.uniform(0.75, 1.35))
            frame_seed = int(rng.integers(0, 2**31 - 1))
            image = renderer.render(
                x_true,
                z_true,
                np.random.default_rng(frame_seed),
                condition,
                severity,
            )
            m = estimator.estimate(image)
            calibrated = calibrator.calibrate(m.raw_confidence) if m.valid else 0.0
            xerr = abs(m.x_m - x_true) if m.valid else 3.0
            zerr = abs(m.z_m - z_true) if m.valid else 4.0
            good = bool(m.valid and xerr <= calibrator.tolerance_x_m and zerr <= calibrator.tolerance_z_m)
            rows.append({
                "condition": condition,
                "raw_confidence": m.raw_confidence,
                "calibrated_confidence": calibrated,
                "good": good,
                "abs_x_error_m": xerr,
                "abs_z_error_m": zerr,
            })

    audit = pd.DataFrame(rows)
    bins = pd.cut(audit["calibrated_confidence"], bins=np.linspace(0, 1, 6), include_lowest=True)
    reliability = (
        audit.assign(conf_bin=bins)
        .groupby("conf_bin", observed=True)
        .agg(
            samples=("good", "size"),
            mean_confidence=("calibrated_confidence", "mean"),
            observed_good_rate=("good", "mean"),
            mean_x_error_m=("abs_x_error_m", "mean"),
            mean_z_error_m=("abs_z_error_m", "mean"),
        )
        .reset_index()
    )
    reliability["absolute_calibration_gap"] = (
        reliability["mean_confidence"] - reliability["observed_good_rate"]
    ).abs()
    return reliability


def save_results(raw, summary, paired, reliability, calibrator, out: Path, args) -> None:
    out.mkdir(parents=True, exist_ok=True)
    raw.to_csv(out / "episodes.csv", index=False)
    summary.to_csv(out / "summary.csv", index=False)
    paired.to_csv(out / "paired_effects.csv", index=False)
    reliability.to_csv(out / "calibration_reliability.csv", index=False)
    (out / "calibrator.json").write_text(json.dumps(calibrator.to_dict(), indent=2), encoding="utf-8")
    (out / "run_metadata.json").write_text(json.dumps({
        "evaluation_seed": args.seed,
        "calibration_seed": args.calibration_seed,
        "episodes_per_condition_architecture": args.episodes,
        "calibration_samples_per_condition": args.calibration_samples,
        "severity": args.severity,
        "conditions": list(IMAGE_CONDITIONS),
        "architectures": list(ARCHITECTURES),
        "paired_episode_seeds": True,
        "image_rng_isolated": True,
        "reference_rng_isolated": True,
        "scope": "simulation-only synthetic image sequences",
    }, indent=2), encoding="utf-8")

    (out / "summary.md").write_text(
        "# Phase 6: pixel-sequence landing comparison\n\n"
        "The calibration set and evaluation episode seeds are separate. Runtime "
        "Aegis receives image-derived observations plus the same intentionally "
        "imperfect independent reference estimator used by V3.\n\n"
        + summary.to_markdown(index=False)
        + "\n\n## Paired effects\n\n"
        + paired.to_markdown(index=False)
        + "\n\n## Calibration reliability\n\n"
        + reliability.to_markdown(index=False)
        + "\n",
        encoding="utf-8",
    )

    for metric, ylabel, filename in (
        ("success_rate", "Success rate", "success_rate.png"),
        ("unsafe_touchdown_rate", "Unsafe touchdown rate", "unsafe_rate.png"),
        ("mean_image_abstention_rate", "Mean image abstention rate", "abstention_rate.png"),
    ):
        plot = summary.pivot(index="condition", columns="architecture", values=metric)
        plot.plot(kind="bar")
        plt.ylabel(ylabel)
        plt.xlabel("Image condition")
        plt.ylim(0, 1)
        plt.title(f"Phase 6 {ylabel.lower()}")
        plt.tight_layout()
        plt.savefig(out / filename, dpi=180)
        plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Connect calibrated temporal synthetic-image perception to Aegis V3.")
    parser.add_argument("--episodes", type=int, default=50)
    parser.add_argument("--seed", type=int, default=626262)
    parser.add_argument("--calibration-seed", type=int, default=616161)
    parser.add_argument("--calibration-samples", type=int, default=180)
    parser.add_argument("--severity", type=float, default=1.0)
    parser.add_argument("--out", type=Path, default=Path("results/phase6_image_landing"))
    args = parser.parse_args()

    if args.episodes < 1:
        raise ValueError("episodes must be >= 1")
    if args.seed == args.calibration_seed:
        raise ValueError("evaluation and calibration seeds must differ")

    raw, calibrator = run_comparison(
        episodes=args.episodes,
        seed=args.seed,
        calibration_seed=args.calibration_seed,
        calibration_samples=args.calibration_samples,
        severity=args.severity,
    )
    summary = summarize(raw)
    paired = paired_effects(raw)
    reliability = calibration_audit(calibrator, seed=args.seed + 9090)
    save_results(raw, summary, paired, reliability, calibrator, args.out, args)

    print(summary.to_string(index=False))
    print("\nPaired effects:")
    print(paired.to_string(index=False))
    print("\nCalibration reliability:")
    print(reliability.to_string(index=False))
    print(f"\nSaved Phase 6 results to {args.out.resolve()}")


if __name__ == "__main__":
    main()
