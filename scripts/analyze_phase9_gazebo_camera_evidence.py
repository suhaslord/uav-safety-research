from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from uav_safety.perception_trace import PHASE9_PERCEPTION_TRACE_SCHEMA, validate_perception_trace


RESULT_SCHEMA = "aegisland.phase9.perception-result.v1"
ARUCO_DICTIONARY_NAMES = (
    "DICT_4X4_50",
    "DICT_4X4_100",
    "DICT_4X4_250",
    "DICT_4X4_1000",
    "DICT_5X5_50",
    "DICT_5X5_100",
    "DICT_5X5_250",
    "DICT_5X5_1000",
    "DICT_6X6_50",
    "DICT_6X6_100",
    "DICT_6X6_250",
    "DICT_6X6_1000",
    "DICT_7X7_50",
    "DICT_7X7_100",
    "DICT_7X7_250",
    "DICT_7X7_1000",
    "DICT_ARUCO_ORIGINAL",
)


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rotation_matrix(qx: float, qy: float, qz: float, qw: float) -> np.ndarray:
    q = np.asarray([qw, qx, qy, qz], dtype=float)
    norm = float(np.linalg.norm(q))
    if norm < 1e-12:
        raise ValueError("camera quaternion has zero norm")
    w, x, y, z = q / norm
    return np.asarray(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ],
        dtype=float,
    )


def _project_world_point(point_world: np.ndarray, camera_position: np.ndarray, rotation_wc: np.ndarray,
                         fx: float, fy: float, cx: float, cy: float) -> tuple[float, float, float, float]:
    local = rotation_wc.T @ (point_world - camera_position)
    forward = float(local[0])
    right = float(-local[1])
    down = float(-local[2])
    if forward <= 1e-9:
        return float("nan"), float("nan"), forward, right
    u = cx + fx * right / forward
    v = cy + fy * down / forward
    return float(u), float(v), forward, right


def _polygon_area(points: np.ndarray) -> float:
    x = points[:, 0]
    y = points[:, 1]
    return float(abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))) * 0.5)


def _truth_geometry(row: pd.Series, horizontal_fov_rad: float, marker_size_m: float) -> dict:
    width = int(row["width"])
    height = int(row["height"])
    fx = width / (2.0 * math.tan(horizontal_fov_rad / 2.0))
    fy = fx
    cx = (width - 1.0) / 2.0
    cy = (height - 1.0) / 2.0
    camera_position = np.asarray([row["camera_x_m"], row["camera_y_m"], row["camera_z_m"]], dtype=float)
    rotation_wc = _rotation_matrix(
        row["camera_qx"], row["camera_qy"], row["camera_qz"], row["camera_qw"]
    )

    target_center = np.asarray([0.0, 0.0, 0.001], dtype=float)
    center_u, center_v, depth, lateral_right = _project_world_point(
        target_center, camera_position, rotation_wc, fx, fy, cx, cy
    )
    half = marker_size_m / 2.0
    corners_world = np.asarray(
        [
            [-half, half, 0.001],
            [half, half, 0.001],
            [half, -half, 0.001],
            [-half, -half, 0.001],
        ],
        dtype=float,
    )
    projected = []
    all_in_front = True
    for point in corners_world:
        u, v, corner_depth, _ = _project_world_point(point, camera_position, rotation_wc, fx, fy, cx, cy)
        if corner_depth <= 0.1 or not np.isfinite(u) or not np.isfinite(v):
            all_in_front = False
        projected.append([u, v])
    projected_array = np.asarray(projected, dtype=float)
    area = _polygon_area(projected_array) if all_in_front and np.isfinite(projected_array).all() else 0.0

    # Predeclared Phase 9 visibility means the target *center* is optically in
    # frame and the projected footprint is non-degenerate. Partial edge clips
    # may therefore remain truth-visible if the target center is still visible.
    visible = bool(
        depth > 0.1
        and np.isfinite(center_u)
        and np.isfinite(center_v)
        and 0.0 <= center_u < width
        and 0.0 <= center_v < height
        and area >= 4.0
    )
    return {
        "fx": fx,
        "fy": fy,
        "cx": cx,
        "cy": cy,
        "visible": visible,
        "center_x_px": center_u if visible else None,
        "center_y_px": center_v if visible else None,
        "area_px2": area if visible else None,
        "lateral_x_m": lateral_right,
        "altitude_m": max(0.0, depth),
    }


def _load_grayscale(path: Path, width: int, height: int, step: int) -> np.ndarray:
    raw = np.frombuffer(path.read_bytes(), dtype=np.uint8)
    if height <= 0 or width <= 0 or step <= 0:
        raise ValueError("invalid image dimensions in capture metadata")
    if raw.size != height * step:
        raise ValueError(
            f"raw frame size does not match height*step for {path.name}: {raw.size} != {height * step}"
        )
    row_data = raw.reshape(height, step)
    if step == width:
        return row_data[:, :width].copy()
    if step >= width * 3:
        channels = step // width
        if channels not in {3, 4} or channels * width != step:
            raise ValueError(f"unsupported camera row step {step} for width {width}")
        pixels = row_data[:, : width * channels].reshape(height, width, channels)
        # Marker detection only needs luminance; averaging is invariant to RGB/BGR
        # channel order and avoids silently assuming a transport color ordering.
        return np.mean(pixels[:, :, :3].astype(np.float32), axis=2).astype(np.uint8)
    raise ValueError(f"unsupported raw camera payload layout: width={width} step={step}")


def _order_quad(points: np.ndarray) -> np.ndarray:
    points = np.asarray(points, dtype=np.float32).reshape(4, 2)
    ordered = np.zeros((4, 2), dtype=np.float32)
    sums = points.sum(axis=1)
    diffs = np.diff(points, axis=1).reshape(-1)
    ordered[0] = points[np.argmin(sums)]  # top-left
    ordered[2] = points[np.argmax(sums)]  # bottom-right
    ordered[1] = points[np.argmin(diffs)]  # top-right
    ordered[3] = points[np.argmax(diffs)]  # bottom-left
    return ordered


def _quad_area(corners: np.ndarray) -> float:
    return _polygon_area(np.asarray(corners, dtype=float).reshape(4, 2))


def _fallback_quad(gray: np.ndarray):
    import cv2

    image_area = float(gray.shape[0] * gray.shape[1])
    best = None
    for invert in (False, True):
        threshold_type = cv2.THRESH_BINARY_INV if invert else cv2.THRESH_BINARY
        _, binary = cv2.threshold(gray, 0, 255, threshold_type | cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = float(abs(cv2.contourArea(contour)))
            if area < max(80.0, image_area * 0.0002) or area > image_area * 0.45:
                continue
            perimeter = float(cv2.arcLength(contour, True))
            if perimeter <= 0:
                continue
            approx = cv2.approxPolyDP(contour, 0.025 * perimeter, True)
            if len(approx) != 4 or not cv2.isContourConvex(approx):
                continue
            corners = _order_quad(approx.reshape(4, 2))
            x = corners[:, 0]
            y = corners[:, 1]
            if x.min() <= 1 or y.min() <= 1 or x.max() >= gray.shape[1] - 2 or y.max() >= gray.shape[0] - 2:
                continue
            rect = cv2.minAreaRect(corners)
            rect_area = float(rect[1][0] * rect[1][1])
            if rect_area <= 0:
                continue
            rectangularity = min(1.0, area / rect_area)
            if rectangularity < 0.7:
                continue
            score = area * rectangularity
            if best is None or score > best[0]:
                best = (score, corners)
    return None if best is None else best[1]


def _detect_marker(gray: np.ndarray, marker_size_m: float, fx: float, fy: float, cx: float, cy: float) -> dict | None:
    import cv2

    best = None
    for dictionary_name in ARUCO_DICTIONARY_NAMES:
        if not hasattr(cv2.aruco, dictionary_name):
            continue
        dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, dictionary_name))
        parameters = cv2.aruco.DetectorParameters()
        if hasattr(cv2.aruco, "ArucoDetector"):
            detector = cv2.aruco.ArucoDetector(dictionary, parameters)
            corners_list, ids, _ = detector.detectMarkers(gray)
        else:
            corners_list, ids, _ = cv2.aruco.detectMarkers(gray, dictionary, parameters=parameters)
        if ids is None:
            continue
        for corners, marker_id in zip(corners_list, ids.reshape(-1)):
            ordered = np.asarray(corners, dtype=np.float32).reshape(4, 2)
            area = _quad_area(ordered)
            if best is None or area > best[0]:
                best = (area, ordered, "aruco", dictionary_name, int(marker_id))

    if best is None:
        corners = _fallback_quad(gray)
        if corners is None:
            return None
        best = (_quad_area(corners), corners, "quad_fallback", None, None)

    area, corners, detector_kind, dictionary_name, marker_id = best
    object_points = np.asarray(
        [
            [-marker_size_m / 2.0, marker_size_m / 2.0, 0.0],
            [marker_size_m / 2.0, marker_size_m / 2.0, 0.0],
            [marker_size_m / 2.0, -marker_size_m / 2.0, 0.0],
            [-marker_size_m / 2.0, -marker_size_m / 2.0, 0.0],
        ],
        dtype=np.float32,
    )
    camera_matrix = np.asarray([[fx, 0.0, cx], [0.0, fy, cy], [0.0, 0.0, 1.0]], dtype=np.float64)
    distortion = np.zeros((5, 1), dtype=np.float64)
    flags = getattr(cv2, "SOLVEPNP_IPPE_SQUARE", cv2.SOLVEPNP_ITERATIVE)
    ok, rvec, tvec = cv2.solvePnP(object_points, corners.astype(np.float32), camera_matrix, distortion, flags=flags)
    if not ok:
        return None
    projected, _ = cv2.projectPoints(object_points, rvec, tvec, camera_matrix, distortion)
    reprojection = np.linalg.norm(projected.reshape(4, 2) - corners, axis=1)
    reprojection_rms = float(np.sqrt(np.mean(reprojection ** 2)))
    side_lengths = [
        float(np.linalg.norm(corners[(i + 1) % 4] - corners[i])) for i in range(4)
    ]
    side_px = max(1.0, float(np.mean(side_lengths)))
    tvec = np.asarray(tvec, dtype=float).reshape(3)
    observed_lateral = float(tvec[0])
    observed_altitude = float(tvec[2])
    if not np.isfinite(observed_lateral) or not np.isfinite(observed_altitude) or observed_altitude <= 0:
        return None

    center = np.mean(corners, axis=0)
    footprint_score = min(1.0, math.sqrt(max(area, 0.0)) / 90.0)
    reprojection_score = math.exp(-reprojection_rms / 3.0)
    detector_multiplier = 1.0 if detector_kind == "aruco" else 0.65
    confidence = float(np.clip(detector_multiplier * footprint_score * reprojection_score, 0.0, 0.99))
    pixel_sigma = max(0.5, reprojection_rms)
    sigma_altitude = max(1e-4, observed_altitude * pixel_sigma / side_px)
    sigma_lateral = max(
        1e-4,
        observed_altitude * pixel_sigma / max(fx, 1.0)
        + abs(observed_lateral / observed_altitude) * sigma_altitude,
    )
    return {
        "center_x_px": float(center[0]),
        "center_y_px": float(center[1]),
        "lateral_x_m": observed_lateral,
        "altitude_m": observed_altitude,
        "confidence": confidence,
        "sigma_lateral_m": float(sigma_lateral),
        "sigma_altitude_m": float(sigma_altitude),
        "detector_kind": detector_kind,
        "dictionary": dictionary_name,
        "marker_id": marker_id,
        "reprojection_rms_px": reprojection_rms,
        "detected_area_px2": float(area),
    }


def _pearson(a: np.ndarray, b: np.ndarray) -> float | None:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    finite = np.isfinite(a) & np.isfinite(b)
    a = a[finite]
    b = b[finite]
    if len(a) < 3 or float(np.std(a)) < 1e-12 or float(np.std(b)) < 1e-12:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def _run_lengths(mask: np.ndarray) -> list[int]:
    runs: list[int] = []
    current = 0
    for value in np.asarray(mask, dtype=bool):
        if value:
            current += 1
        elif current:
            runs.append(current)
            current = 0
    if current:
        runs.append(current)
    return runs


def _write_manifest(out_dir: Path, names: list[str]) -> dict:
    files = {}
    for name in names:
        path = out_dir / name
        files[name] = {"sha256": _sha256_file(path), "bytes": path.stat().st_size}
    manifest = {"schema": RESULT_SCHEMA, "files": files}
    (out_dir / "result_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def analyze(args: argparse.Namespace) -> dict:
    capture = pd.read_csv(args.capture_csv)
    required = {
        "frame_index", "image_stamp_s", "receive_elapsed_s", "width", "height", "step", "data_size",
        "frame_path", "camera_pose_valid", "camera_pose_name", "camera_x_m", "camera_y_m", "camera_z_m",
        "camera_qx", "camera_qy", "camera_qz", "camera_qw",
    }
    missing = sorted(required - set(capture.columns))
    if missing:
        raise ValueError(f"capture metadata missing columns: {missing}")
    capture["camera_pose_valid"] = capture["camera_pose_valid"].astype(str).str.lower().isin({"true", "1", "yes"})
    capture = capture[capture["camera_pose_valid"]].copy()
    if len(capture) < 10:
        raise ValueError(f"too few camera frames with synchronized camera pose: {len(capture)}")

    stamp = pd.to_numeric(capture["image_stamp_s"], errors="coerce").to_numpy(dtype=float)
    if np.isfinite(stamp).all() and np.all(stamp >= 0) and np.all(np.diff(stamp) > 0):
        times = stamp - stamp[0]
        time_source = "gazebo_image_header_stamp"
    else:
        receive = pd.to_numeric(capture["receive_elapsed_s"], errors="raise").to_numpy(dtype=float)
        if np.any(np.diff(receive) <= 0):
            raise ValueError("camera receive timestamps are not strictly increasing")
        times = receive - receive[0]
        time_source = "collector_steady_receive_time"

    args.out.mkdir(parents=True, exist_ok=True)
    records = []
    details = []
    detector_counts: Counter[str] = Counter()
    dictionary_counts: Counter[str] = Counter()

    for local_index, (_, row) in enumerate(capture.iterrows()):
        frame_path = args.frame_root / str(row["frame_path"])
        if not frame_path.is_file():
            raise ValueError(f"captured raw frame missing: {frame_path}")
        width = int(row["width"])
        height = int(row["height"])
        step = int(row["step"])
        gray = _load_grayscale(frame_path, width, height, step)
        truth = _truth_geometry(row, args.horizontal_fov_rad, args.marker_size_m)
        detection = _detect_marker(
            gray,
            args.marker_size_m,
            truth["fx"],
            truth["fy"],
            truth["cx"],
            truth["cy"],
        )
        observed = detection is not None
        if detection:
            detector_counts[detection["detector_kind"]] += 1
            if detection["dictionary"]:
                dictionary_counts[detection["dictionary"]] += 1

        records.append(
            {
                "t_s": float(times[local_index]),
                "frame_index": local_index,
                "frame_path": str(row["frame_path"]),
                "frame_sha256": _sha256_file(frame_path),
                "image_width_px": width,
                "image_height_px": height,
                "truth_target_visible": truth["visible"],
                "truth_center_x_px": truth["center_x_px"],
                "truth_center_y_px": truth["center_y_px"],
                "truth_target_area_px2": truth["area_px2"],
                "truth_lateral_x_m": truth["lateral_x_m"],
                "truth_altitude_m": truth["altitude_m"],
                "observation_available": observed,
                "observed_center_x_px": detection["center_x_px"] if detection else None,
                "observed_center_y_px": detection["center_y_px"] if detection else None,
                "observed_lateral_x_m": detection["lateral_x_m"] if detection else None,
                "observed_altitude_m": detection["altitude_m"] if detection else None,
                "confidence": detection["confidence"] if detection else None,
                "sigma_lateral_m": detection["sigma_lateral_m"] if detection else None,
                "sigma_altitude_m": detection["sigma_altitude_m"] if detection else None,
            }
        )
        details.append(
            {
                "frame_index": local_index,
                "capture_frame_index": int(row["frame_index"]),
                "camera_pose_name": row["camera_pose_name"],
                "truth_visible": truth["visible"],
                "detector_kind": detection["detector_kind"] if detection else None,
                "aruco_dictionary": detection["dictionary"] if detection else None,
                "marker_id": detection["marker_id"] if detection else None,
                "reprojection_rms_px": detection["reprojection_rms_px"] if detection else None,
                "detected_area_px2": detection["detected_area_px2"] if detection else None,
            }
        )

    trace = pd.DataFrame(records)
    normalized, validation = validate_perception_trace(
        trace,
        frame_root=args.frame_root,
        verify_frame_hashes=True,
    )
    trace_path = args.out / "perception_trace.csv"
    normalized.to_csv(trace_path, index=False)
    pd.DataFrame(details).to_csv(args.out / "detection_details.csv", index=False)

    visible = normalized["truth_target_visible"].to_numpy(dtype=bool)
    observed = normalized["observation_available"].to_numpy(dtype=bool)
    paired = visible & observed
    pixel_errors = np.asarray([], dtype=float)
    lateral_errors = np.asarray([], dtype=float)
    altitude_errors = np.asarray([], dtype=float)
    normalized_pixel_errors = np.asarray([], dtype=float)
    footprint_pixel_errors = np.asarray([], dtype=float)
    if paired.any():
        dx = (
            normalized.loc[paired, "observed_center_x_px"].to_numpy(dtype=float)
            - normalized.loc[paired, "truth_center_x_px"].to_numpy(dtype=float)
        )
        dy = (
            normalized.loc[paired, "observed_center_y_px"].to_numpy(dtype=float)
            - normalized.loc[paired, "truth_center_y_px"].to_numpy(dtype=float)
        )
        pixel_errors = np.hypot(dx, dy)
        diagonal = np.hypot(
            normalized.loc[paired, "image_width_px"].to_numpy(dtype=float),
            normalized.loc[paired, "image_height_px"].to_numpy(dtype=float),
        )
        normalized_pixel_errors = pixel_errors / diagonal
        footprint_pixel_errors = pixel_errors / np.sqrt(
            normalized.loc[paired, "truth_target_area_px2"].to_numpy(dtype=float)
        )
        lateral_errors = (
            normalized.loc[paired, "observed_lateral_x_m"].to_numpy(dtype=float)
            - normalized.loc[paired, "truth_lateral_x_m"].to_numpy(dtype=float)
        )
        altitude_errors = (
            normalized.loc[paired, "observed_altitude_m"].to_numpy(dtype=float)
            - normalized.loc[paired, "truth_altitude_m"].to_numpy(dtype=float)
        )

    confidence = normalized.loc[paired, "confidence"].to_numpy(dtype=float) if paired.any() else np.asarray([])
    sigma_lateral = normalized.loc[paired, "sigma_lateral_m"].to_numpy(dtype=float) if paired.any() else np.asarray([])
    sigma_altitude = normalized.loc[paired, "sigma_altitude_m"].to_numpy(dtype=float) if paired.any() else np.asarray([])
    dt = np.diff(normalized["t_s"].to_numpy(dtype=float))
    missed_runs = _run_lengths(visible & ~observed)

    phase7_comparison = {
        "status": "insufficient_axis_definition",
        "reason": (
            "Phase 9 lateral error is defined in the external camera optical-horizontal axis, while the frozen "
            "Phase 7 image_x_m series is a state-level lateral coordinate. Direct KS/Wasserstein comparison would "
            "conflate coordinate definitions, so it is intentionally not computed for this first seen trace."
        ),
    }
    if args.surrogate_trace is not None:
        phase7_comparison["surrogate_trace_sha256"] = _sha256_file(args.surrogate_trace)

    metrics = {
        "target_visible_rate": validation.target_visible_rate,
        "observation_available_rate": validation.observation_available_rate,
        "missed_detection_rate_when_visible": validation.missed_detection_rate_when_visible,
        "false_positive_rate_when_not_visible": validation.false_positive_rate_when_not_visible,
        "paired_observation_samples": validation.paired_observation_samples,
        "pixel_center_mae_px": float(np.mean(pixel_errors)) if pixel_errors.size else None,
        "pixel_center_p95_px": float(np.quantile(pixel_errors, 0.95)) if pixel_errors.size else None,
        "normalized_pixel_center_mae": float(np.mean(normalized_pixel_errors)) if normalized_pixel_errors.size else None,
        "footprint_normalized_center_mae": float(np.mean(footprint_pixel_errors)) if footprint_pixel_errors.size else None,
        "lateral_mae_m": validation.lateral_mae_m,
        "lateral_p95_abs_error_m": float(np.quantile(np.abs(lateral_errors), 0.95)) if lateral_errors.size else None,
        "altitude_mae_m": validation.altitude_mae_m,
        "altitude_p95_abs_error_m": float(np.quantile(np.abs(altitude_errors), 0.95)) if altitude_errors.size else None,
        "confidence_vs_abs_lateral_error_pearson": _pearson(confidence, np.abs(lateral_errors)),
        "median_abs_lateral_residual_over_sigma": (
            float(np.median(np.abs(lateral_errors) / sigma_lateral)) if lateral_errors.size else None
        ),
        "median_abs_altitude_residual_over_sigma": (
            float(np.median(np.abs(altitude_errors) / sigma_altitude)) if altitude_errors.size else None
        ),
        "frame_interval_mean_s": float(np.mean(dt)) if dt.size else None,
        "frame_interval_std_s": float(np.std(dt)) if dt.size else None,
        "frame_interval_p95_s": float(np.quantile(dt, 0.95)) if dt.size else None,
        "missed_detection_burst_lengths_frames": missed_runs,
        "max_missed_detection_burst_frames": max(missed_runs, default=0),
        "lag1_lateral_error_correlation": _pearson(lateral_errors[:-1], lateral_errors[1:]) if len(lateral_errors) >= 3 else None,
        "abs_lateral_error_vs_altitude_pearson": (
            _pearson(np.abs(lateral_errors), normalized.loc[paired, "truth_altitude_m"].to_numpy(dtype=float))
            if paired.any() else None
        ),
        "pixel_error_vs_target_area_pearson": (
            _pearson(pixel_errors, normalized.loc[paired, "truth_target_area_px2"].to_numpy(dtype=float))
            if paired.any() else None
        ),
        "phase7_distribution_comparison": phase7_comparison,
    }

    source = {
        "px4_release": args.px4_release,
        "px4_git_sha": args.px4_git_sha_file.read_text(encoding="utf-8").strip(),
        "simulator_model": args.simulator_model,
        "simulator_world": args.simulator_world,
        "camera_topic": args.camera_topic_file.read_text(encoding="utf-8").strip(),
        "pose_topic": args.pose_topic_file.read_text(encoding="utf-8").strip(),
        "horizontal_fov_rad": args.horizontal_fov_rad,
        "marker_size_m": args.marker_size_m,
        "time_source": time_source,
        "raw_capture_metadata_sha256": _sha256_file(args.capture_csv),
        "raw_frame_count": int(len(normalized)),
        "verified_raw_frame_hashes": validation.verified_frame_hashes,
    }
    result = {
        "schema": RESULT_SCHEMA,
        "trace_schema": PHASE9_PERCEPTION_TRACE_SCHEMA,
        "git_sha": args.git_sha,
        "external_perception_evidence_status": "external_perception_seen",
        "claim_level": "descriptive_external_perception_seen",
        "classification_thresholds_declared": False,
        "resemblance_verdict": None,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "simulation_only": True,
        "source": source,
        "validation": validation.to_dict(),
        "metrics": metrics,
        "detector_counts": dict(detector_counts),
        "aruco_dictionary_counts": dict(dictionary_counts),
        "limitations": [
            "This is a seen development trace, not held-out evidence.",
            "The external perception estimator is a pre-run fiducial/quad detector used to characterize captured Gazebo imagery; it is not proof of end-to-end Aegis controller safety.",
            "Reported geometric sigmas are image/reprojection-derived uncertainty proxies, not calibrated probabilistic guarantees.",
            "Phase 7 KS/Wasserstein comparison is withheld where coordinate definitions are not directly compatible.",
            "Simulation-only evidence does not establish physical-flight or real-world performance.",
        ],
    }
    result_path = args.out / "scientific_result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    summary_lines = [
        "# Phase 9 genuine Gazebo camera evidence — seen development result",
        "",
        f"- Evidence status: `external_perception_seen`",
        f"- Captured/validated raw frames: {len(normalized)}",
        f"- Verified raw-frame hashes: {validation.verified_frame_hashes}",
        f"- Target-visible rate: {validation.target_visible_rate:.4f}",
        f"- Observation-available rate: {validation.observation_available_rate:.4f}",
        f"- Missed-detection rate when visible: {validation.missed_detection_rate_when_visible:.4f}",
        f"- False-positive rate when not visible: {validation.false_positive_rate_when_not_visible:.4f}",
        f"- Paired visible+observed frames: {validation.paired_observation_samples}",
        f"- Lateral MAE (camera optical-horizontal): {validation.lateral_mae_m if validation.lateral_mae_m is not None else 'insufficient'}",
        f"- Altitude/depth MAE: {validation.altitude_mae_m if validation.altitude_mae_m is not None else 'insufficient'}",
        "",
        "No Phase 9 resemblance threshold or safety gate was applied. This is descriptive seen evidence only.",
        "The frozen Phase 8 mismatch and historical controller/gate settings were not changed.",
    ]
    (args.out / "summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    manifest = _write_manifest(
        args.out,
        ["perception_trace.csv", "detection_details.csv", "scientific_result.json", "summary.md"],
    )
    return {"result": result, "manifest": manifest}


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze genuine Phase 9 Gazebo camera evidence without retuning frozen phases.")
    parser.add_argument("capture_csv", type=Path)
    parser.add_argument("--frame-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--camera-topic-file", type=Path, required=True)
    parser.add_argument("--pose-topic-file", type=Path, required=True)
    parser.add_argument("--px4-git-sha-file", type=Path, required=True)
    parser.add_argument("--px4-release", default="v1.17.0")
    parser.add_argument("--simulator-model", default="gz_x500_mono_cam_down")
    parser.add_argument("--simulator-world", default="aruco")
    parser.add_argument("--git-sha", required=True)
    parser.add_argument("--horizontal-fov-rad", type=float, default=1.74)
    parser.add_argument("--marker-size-m", type=float, default=0.5)
    parser.add_argument("--surrogate-trace", type=Path, default=None)
    args = parser.parse_args()
    output = analyze(args)
    print(json.dumps(output["result"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
