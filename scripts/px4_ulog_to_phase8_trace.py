from __future__ import annotations

from pathlib import Path
import argparse
import json
import math

import numpy as np
import pandas as pd
from pyulog import ULog

from uav_safety.external_trace import validate_external_trace


def _dataset(ulog: ULog, name: str):
    matches = [d for d in ulog.data_list if d.name == name]
    if not matches:
        available = sorted({d.name for d in ulog.data_list})
        raise KeyError(f"required PX4 ULog topic {name!r} not found; available topics include {available[:40]}")
    return matches[0]


def _optional_dataset(ulog: ULog, name: str):
    matches = [d for d in ulog.data_list if d.name == name]
    return matches[0] if matches else None


def _field(data: dict, *names: str) -> np.ndarray:
    for name in names:
        if name in data:
            return np.asarray(data[name])
    raise KeyError(f"none of fields {names!r} found; available={sorted(data)[:60]}")


def _optional_field(data: dict, *names: str) -> np.ndarray | None:
    for name in names:
        if name in data:
            return np.asarray(data[name])
    return None


def _time_s(data: dict) -> np.ndarray:
    return _field(data, "timestamp").astype(float) * 1e-6


def _asof_indices(source_t: np.ndarray, target_t: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    idx = np.searchsorted(source_t, target_t, side="right") - 1
    valid = idx >= 0
    idx = np.clip(idx, 0, max(0, len(source_t) - 1))
    age = np.full(len(target_t), np.inf, dtype=float)
    if len(source_t):
        age[valid] = target_t[valid] - source_t[idx[valid]]
    return idx, age


def _finite_or_default(values: np.ndarray, default: float) -> np.ndarray:
    values = values.astype(float)
    return np.where(np.isfinite(values), values, default)


def _sigma_from_variance(data: dict, axis: int, fallback: float) -> np.ndarray:
    variance = _optional_field(data, f"position_variance[{axis}]", f"position_variance_{axis}")
    if variance is None:
        return np.full(len(_field(data, "timestamp")), fallback, dtype=float)
    variance = np.asarray(variance, dtype=float)
    sigma = np.sqrt(np.maximum(variance, 0.0))
    good = np.isfinite(sigma) & (sigma > 0.0)
    if good.any():
        replacement = float(np.median(sigma[good]))
    else:
        replacement = fallback
    return np.where(good, sigma, replacement)


def _quality_to_confidence(data: dict) -> np.ndarray:
    quality = _optional_field(data, "quality")
    if quality is None:
        raise KeyError("vehicle_visual_odometry has no quality field; refusing to invent image_confidence")
    q = np.asarray(quality, dtype=float)
    # VehicleOdometry quality is conventionally -1 unknown or 0..100. Unknown
    # samples are treated as unavailable rather than assigned synthetic confidence.
    return np.clip(q / 100.0, 0.0, 1.0)


def _json_safe_mapping(values: dict) -> dict:
    safe: dict = {}
    for key, value in values.items():
        if isinstance(value, (float, np.floating)) and not math.isfinite(float(value)):
            safe[key] = None
        elif isinstance(value, np.integer):
            safe[key] = int(value)
        elif isinstance(value, np.floating):
            safe[key] = float(value)
        else:
            safe[key] = value
    return safe


def convert_ulog(path: Path, *, rate_hz: float = 20.0) -> tuple[pd.DataFrame, dict]:
    if rate_hz <= 0:
        raise ValueError("rate_hz must be positive")

    ulog = ULog(str(path))
    truth = _dataset(ulog, "vehicle_local_position_groundtruth").data
    reference = _dataset(ulog, "vehicle_local_position").data
    vision_dataset = _optional_dataset(ulog, "vehicle_visual_odometry")
    vision = vision_dataset.data if vision_dataset is not None else None

    tt = _time_s(truth)
    rt = _time_s(reference)
    if len(tt) < 2 or len(rt) < 2:
        raise ValueError("PX4 log does not contain enough truth/reference samples")

    vision_available = vision is not None and len(_time_s(vision)) >= 2
    if vision_available:
        vt = _time_s(vision)
        start = max(float(tt[0]), float(vt[0]), float(rt[0]))
        stop = min(float(tt[-1]), float(vt[-1]), float(rt[-1]))
    else:
        vt = None
        start = max(float(tt[0]), float(rt[0]))
        stop = min(float(tt[-1]), float(rt[-1]))

    if stop - start < 2.0:
        raise ValueError(f"overlapping PX4 trace duration is too short: {stop-start:.3f}s")

    dt = 1.0 / rate_hz
    grid = np.arange(start, stop + 0.25 * dt, dt)
    ti, _truth_age = _asof_indices(tt, grid)
    ri, reference_age = _asof_indices(rt, grid)

    # PX4 local position uses NED. Phase 8 landing convention is lateral x and
    # positive-up altitude z, so use North as the lateral axis and negate NED z.
    truth_x = _field(truth, "x").astype(float)[ti]
    truth_z = -_field(truth, "z").astype(float)[ti]
    truth_vx = _field(truth, "vx").astype(float)[ti]
    truth_vz = -_field(truth, "vz").astype(float)[ti]

    if vision_available:
        assert vision is not None and vt is not None
        vi, vision_age = _asof_indices(vt, grid)
        vision_x_all = _field(vision, "position[0]", "x").astype(float)
        vision_z_all = -_field(vision, "position[2]", "z").astype(float)
        vision_vx_all = _field(vision, "velocity[0]", "vx").astype(float)
        vision_vz_all = -_field(vision, "velocity[2]", "vz").astype(float)
        vision_conf_all = _quality_to_confidence(vision)
        vision_sigma_all = _sigma_from_variance(vision, 0, fallback=0.25)
        image_x = vision_x_all[vi]
        image_z = np.maximum(vision_z_all[vi], 0.0)
        image_vx = vision_vx_all[vi]
        image_vz = vision_vz_all[vi]
        image_confidence = vision_conf_all[vi]
        image_sigma = vision_sigma_all[vi]
        image_drop = (vision_age > max(0.075, 1.5 * dt)) | (image_confidence <= 0.0)
    else:
        # Standard gz_x500 has no external-vision producer. The frozen Phase 8
        # schema still requires numeric image payload columns, so use explicit
        # zero sentinels while marking every sample dropped. Frozen Phase 8
        # feature extraction ignores these payloads whenever image_dropped=True;
        # no PX4 or Aegis measurement is invented or treated as observed vision.
        image_x = np.zeros(len(grid), dtype=float)
        image_z = np.zeros(len(grid), dtype=float)
        image_vx = np.zeros(len(grid), dtype=float)
        image_vz = np.zeros(len(grid), dtype=float)
        image_confidence = np.zeros(len(grid), dtype=float)
        image_sigma = np.zeros(len(grid), dtype=float)
        image_drop = np.ones(len(grid), dtype=bool)

    ref_x_all = _field(reference, "x").astype(float)
    ref_z_all = -_field(reference, "z").astype(float)
    ref_vx_all = _field(reference, "vx").astype(float)
    ref_vz_all = -_field(reference, "vz").astype(float)
    xy_valid = _optional_field(reference, "xy_valid")
    z_valid = _optional_field(reference, "z_valid")
    if xy_valid is None:
        xy_valid = np.ones(len(rt), dtype=bool)
    if z_valid is None:
        z_valid = np.ones(len(rt), dtype=bool)
    ref_valid_all = np.asarray(xy_valid, dtype=bool) & np.asarray(z_valid, dtype=bool)
    reference_available = (reference_age <= max(0.15, 3.0 * dt)) & ref_valid_all[ri]
    reference_fresh = np.r_[True, ri[1:] != ri[:-1]] & reference_available

    eph = _optional_field(reference, "eph")
    epv = _optional_field(reference, "epv")
    if eph is None:
        eph = np.full(len(rt), 0.35)
    if epv is None:
        epv = np.full(len(rt), 0.45)
    ref_sigma_all = np.maximum(
        _finite_or_default(np.asarray(eph), 0.35),
        _finite_or_default(np.asarray(epv), 0.45),
    )

    out = pd.DataFrame({
        "t_s": grid - grid[0],
        "truth_x_m": truth_x,
        "truth_z_m": np.maximum(truth_z, 0.0),
        "truth_vx_mps": truth_vx,
        "truth_vz_mps": truth_vz,
        "image_x_m": image_x,
        "image_z_m": image_z,
        "image_vx_mps": image_vx,
        "image_vz_mps": image_vz,
        "image_confidence": image_confidence,
        "image_sigma_pos_m": image_sigma,
        "image_dropped": image_drop,
        "reference_x_m": ref_x_all[ri],
        "reference_z_m": np.maximum(ref_z_all[ri], 0.0),
        "reference_vx_mps": ref_vx_all[ri],
        "reference_vz_mps": ref_vz_all[ri],
        "reference_sigma_pos_m": ref_sigma_all[ri],
        "reference_available": reference_available,
        "reference_fresh": reference_fresh,
    })

    # Optional timing fields are included only when PX4 logged the corresponding
    # sample timestamp. Their absence remains an explicit Phase 8 insufficiency.
    if vision_available:
        assert vision is not None and vt is not None
        vi, _vision_age = _asof_indices(vt, grid)
        vision_sample_ts = _optional_field(vision, "timestamp_sample")
        if vision_sample_ts is not None:
            vision_transport = vt - np.asarray(vision_sample_ts, dtype=float) * 1e-6
            out["image_transport_latency_s"] = np.maximum(vision_transport[vi], 0.0)
    reference_sample_ts = _optional_field(reference, "timestamp_sample")
    if reference_sample_ts is not None:
        reference_transport = rt - np.asarray(reference_sample_ts, dtype=float) * 1e-6
        out["reference_transport_latency_s"] = np.maximum(reference_transport[ri], 0.0)
    out["reference_state_age_s"] = np.maximum(reference_age, 0.0)

    normalized, report = validate_external_trace(out)
    available_topics = sorted({d.name for d in ulog.data_list})
    if vision_available:
        image_semantics = "PX4/Gazebo visual-odometry stream; not Aegis image estimator output"
        image_payload_policy = "logged PX4 vehicle_visual_odometry samples"
    else:
        image_semantics = (
            "No vehicle_visual_odometry stream was logged by standard gz_x500. "
            "Image evidence is unavailable and every Phase 8 image sample is marked dropped."
        )
        image_payload_policy = (
            "Required numeric image fields contain zero sentinels only while image_dropped=True; "
            "they are non-observations and ignored by frozen Phase 8 image-valid feature extraction."
        )

    metadata = {
        "source_format": "PX4 ULog",
        "source_file": path.name,
        "px4_ulog_start_timestamp_us": int(ulog.start_timestamp),
        "px4_ulog_last_timestamp_us": int(ulog.last_timestamp),
        "resample_rate_hz": rate_hz,
        "coordinate_mapping": "PX4 local NED: lateral=x(North), altitude=-z, lateral_velocity=vx, vertical_velocity=-vz",
        "truth_topic": "vehicle_local_position_groundtruth",
        "image_channel_available": bool(vision_available),
        "image_topic": "vehicle_visual_odometry" if vision_available else None,
        "reference_topic": "vehicle_local_position",
        "image_semantics": image_semantics,
        "image_payload_policy": image_payload_policy,
        "reference_semantics": "PX4 estimator local position; not statistically independent of all PX4 aiding sources",
        "comparison_scope": (
            "External PX4/Gazebo plant/navigation/reference evidence. Image-distribution conclusions are unavailable "
            "when vehicle_visual_odometry is absent and must not be inferred from sentinel payloads."
        ),
        "validation": _json_safe_mapping(report.to_dict()),
        "available_topics": available_topics,
    }
    return normalized, metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert a genuine PX4 SITL ULog into the frozen Phase 8 external-trace schema.")
    parser.add_argument("ulog", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--metadata-out", type=Path, required=True)
    parser.add_argument("--rate-hz", type=float, default=20.0)
    args = parser.parse_args()

    frame, metadata = convert_ulog(args.ulog, rate_hz=args.rate_hz)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.out, index=False)
    args.metadata_out.write_text(
        json.dumps(metadata, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "rows": len(frame),
        "duration_s": float(frame["t_s"].iloc[-1]),
        "image_channel_available": metadata["image_channel_available"],
        "out": str(args.out),
    }, indent=2))


if __name__ == "__main__":
    main()
