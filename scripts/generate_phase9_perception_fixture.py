from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import argparse
import json

import numpy as np
import pandas as pd

from uav_safety.perception_trace import PHASE9_PERCEPTION_TRACE_SCHEMA, validate_perception_trace


def _write_pgm(path: Path, pixels: np.ndarray) -> str:
    pixels = np.asarray(pixels, dtype=np.uint8)
    if pixels.ndim != 2:
        raise ValueError("PGM fixture expects a 2D grayscale image")
    height, width = pixels.shape
    payload = f"P5\n{width} {height}\n255\n".encode("ascii") + pixels.tobytes()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return sha256(payload).hexdigest()


def generate_fixture(out_dir: Path, *, rows: int = 40, seed: int = 909090) -> dict:
    if rows < 20:
        raise ValueError("Phase 9 fixture requires at least 20 frames")

    rng = np.random.default_rng(seed)
    width, height = 64, 48
    frame_dir = out_dir / "frames"
    records: list[dict] = []

    for i in range(rows):
        t_s = i / 20.0
        truth_altitude = 4.0 - 2.5 * (i / max(rows - 1, 1))
        truth_lateral = 0.45 * np.sin(i / 6.0)
        visible = (i % 11) != 0
        false_positive = (not visible) and (i % 22 == 0) and i > 0
        detected = (visible and (i % 7 != 0)) or false_positive

        pixels = np.tile(np.arange(width, dtype=np.uint8), (height, 1))
        pixels = (pixels + np.uint8((i * 3) % 127)).astype(np.uint8)

        truth_center_x = None
        truth_center_y = None
        truth_area = None
        if visible:
            truth_center_x = float(width / 2 + 9.0 * np.sin(i / 8.0))
            truth_center_y = float(height / 2 + 5.0 * np.cos(i / 9.0))
            half = max(1, int(5.0 / max(truth_altitude, 1.0)))
            x0 = max(0, int(round(truth_center_x)) - half)
            x1 = min(width, int(round(truth_center_x)) + half + 1)
            y0 = max(0, int(round(truth_center_y)) - half)
            y1 = min(height, int(round(truth_center_y)) + half + 1)
            pixels[y0:y1, x0:x1] = 245
            truth_area = float((x1 - x0) * (y1 - y0))

        frame_path = Path("frames") / f"frame_{i:04d}.pgm"
        frame_hash = _write_pgm(out_dir / frame_path, pixels)

        observed_center_x = None
        observed_center_y = None
        observed_lateral = None
        observed_altitude = None
        confidence = None
        sigma_lateral = None
        sigma_altitude = None
        if detected:
            if visible:
                observed_center_x = float(truth_center_x + rng.normal(0.0, 0.8))
                observed_center_y = float(truth_center_y + rng.normal(0.0, 0.7))
                observed_lateral = float(truth_lateral + rng.normal(0.0, 0.035))
                observed_altitude = float(max(0.0, truth_altitude + rng.normal(0.0, 0.06)))
                confidence = float(np.clip(0.94 - 0.04 * truth_altitude + rng.normal(0.0, 0.015), 0.0, 1.0))
            else:
                observed_center_x = 13.0
                observed_center_y = 17.0
                observed_lateral = float(truth_lateral + 0.7)
                observed_altitude = float(truth_altitude + 0.4)
                confidence = 0.28
            sigma_lateral = 0.06
            sigma_altitude = 0.10

        records.append(
            {
                "t_s": t_s,
                "frame_index": i,
                "frame_path": frame_path.as_posix(),
                "frame_sha256": frame_hash,
                "image_width_px": width,
                "image_height_px": height,
                "truth_target_visible": visible,
                "truth_center_x_px": truth_center_x,
                "truth_center_y_px": truth_center_y,
                "truth_target_area_px2": truth_area,
                "truth_lateral_x_m": truth_lateral,
                "truth_altitude_m": truth_altitude,
                "observation_available": detected,
                "observed_center_x_px": observed_center_x,
                "observed_center_y_px": observed_center_y,
                "observed_lateral_x_m": observed_lateral,
                "observed_altitude_m": observed_altitude,
                "confidence": confidence,
                "sigma_lateral_m": sigma_lateral,
                "sigma_altitude_m": sigma_altitude,
                "frame_transport_latency_s": 0.012 + 0.002 * (i % 3),
                "camera_exposure_s": 0.004,
            }
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    trace_path = out_dir / "perception_trace.csv"
    frame = pd.DataFrame(records)
    frame.to_csv(trace_path, index=False)
    normalized, report = validate_perception_trace(
        frame,
        frame_root=out_dir,
        verify_frame_hashes=True,
    )

    metadata = {
        "schema": PHASE9_PERCEPTION_TRACE_SCHEMA,
        "run_role": "phase9_pipeline_fixture",
        "external_perception_evidence_status": "fixture_non_authoritative",
        "claim_level": "pipeline_validation_only",
        "seed": seed,
        "rows": int(len(normalized)),
        "raw_frames_preserved": True,
        "frame_hashes_verified": report.verified_frame_hashes,
        "controller_tuning_allowed": False,
        "safety_acceptance": False,
        "simulation_only": True,
        "validation": report.to_dict(),
    }
    metadata_path = out_dir / "fixture_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"trace": trace_path, "metadata": metadata_path, "validation": report.to_dict()}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic non-authoritative Phase 9 camera evidence fixtures.")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--rows", type=int, default=40)
    parser.add_argument("--seed", type=int, default=909090)
    args = parser.parse_args()
    result = generate_fixture(args.out, rows=args.rows, seed=args.seed)
    print(json.dumps({"trace": str(result["trace"]), "metadata": str(result["metadata"]), "validation": result["validation"]}, indent=2))


if __name__ == "__main__":
    main()
