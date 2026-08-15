from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def generate(out_dir: Path, *, seed: int = 101010, frames: int = 72) -> None:
    rng = np.random.default_rng(seed)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    details = []
    dt = 0.33
    for i in range(frames):
        t = i * dt
        x = 1.15 * np.sin(0.22 * t) - 0.02 * t
        z = 2.8 - 0.018 * i + 0.08 * np.sin(0.13 * t)
        visible = 6 <= i <= frames - 6
        observation = visible and (i % 11 != 0)
        kind = None
        ox = np.nan
        oz = np.nan
        reproj = np.nan
        area = np.nan
        if observation:
            if i in {18, 31, 45, 58}:
                kind = "quad_fallback"
                ox = x + rng.choice([-1.0, 1.0]) * rng.uniform(2.5, 5.5)
                oz = z + rng.uniform(3.0, 7.0)
                reproj = rng.uniform(0.05, 0.35)
                area = rng.uniform(700.0, 2400.0)
            else:
                kind = "aruco"
                ox = x + rng.normal(0.0, 0.035)
                oz = z + rng.normal(0.0, 0.04)
                reproj = abs(rng.normal(0.22, 0.10))
                area = rng.uniform(12000.0, 90000.0)

        rows.append({
            "t_s": round(t, 6), "frame_index": i, "frame_path": f"fixture_{i:04d}.raw",
            "frame_sha256": "0" * 64, "image_width_px": 640, "image_height_px": 480,
            "truth_target_visible": visible, "truth_center_x_px": 320.0 if visible else np.nan,
            "truth_center_y_px": 240.0 if visible else np.nan,
            "truth_target_area_px2": 25000.0 if visible else np.nan,
            "truth_lateral_x_m": x, "truth_altitude_m": z,
            "observation_available": observation,
            "observed_center_x_px": 320.0 if observation else np.nan,
            "observed_center_y_px": 240.0 if observation else np.nan,
            "observed_lateral_x_m": ox, "observed_altitude_m": oz,
            "confidence": 0.90 if kind == "aruco" else (0.30 if kind else 0.0),
            "sigma_lateral_m": 0.04 if kind == "aruco" else (0.12 if kind else np.nan),
            "sigma_altitude_m": 0.04 if kind == "aruco" else (0.18 if kind else np.nan),
        })
        details.append({
            "frame_index": i, "capture_frame_index": i, "camera_pose_name": "fixture::camera_link",
            "truth_visible": visible, "detector_kind": kind,
            "aruco_dictionary": "DICT_4X4_50" if kind == "aruco" else None,
            "marker_id": 0 if kind == "aruco" else np.nan,
            "reprojection_rms_px": reproj, "detected_area_px2": area,
        })

    pd.DataFrame(rows).to_csv(out_dir / "perception_trace.csv", index=False)
    pd.DataFrame(details).to_csv(out_dir / "detection_details.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic non-authoritative Phase 10 CI fixture.")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=101010)
    parser.add_argument("--frames", type=int, default=72)
    args = parser.parse_args()
    generate(args.out, seed=args.seed, frames=args.frames)


if __name__ == "__main__":
    main()
