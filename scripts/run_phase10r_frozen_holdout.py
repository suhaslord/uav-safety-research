from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd

FROZEN_CANDIDATE_SHA = "e1d566f8baa47bf10f9bdf39dd5988724208be80"
CALIBRATION_SHA256 = "3ffdf1e37c94361ac01d8175f902a0ae4fb8d831274bb7850c171e92d79c527b"
HOLDOUT_SEED = 1618033
N = 48
TRAJECTORIES = tuple(range(12))
APPEARANCES = ("nominal", "dim_contrast", "blur_noise")
TARGETS = (0.50, 0.68, 0.80, 0.90, 0.95)


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _dump(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _load_frozen_module(tmp: Path):
    pkg = tmp / "scripts"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("")
    for name in ("run_phase10r_generalization.py", "analyze_phase9_gazebo_camera_evidence.py"):
        content = subprocess.check_output(
            ["git", "show", f"{FROZEN_CANDIDATE_SHA}:scripts/{name}"], text=True
        )
        (pkg / name).write_text(content)
    sys.path.insert(0, str(tmp))
    spec = importlib.util.spec_from_file_location(
        "frozen_phase10r", pkg / "run_phase10r_generalization.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load frozen Phase 10R module")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    if getattr(mod, "MIN_VISIBLE", None) != 0.66:
        raise RuntimeError("frozen candidate MIN_VISIBLE changed")
    return mod


def _trajectory(tid: int, t: float) -> tuple[float, float, float]:
    phase = (tid % 6) * math.pi / 6
    family = tid % 4
    if family == 0:
        q = 1.06 * math.sin(2 * math.pi * t + phase)
    elif family == 1:
        q = -1.04 + 2.08 * t
    elif family == 2:
        q = 1.04 - 2.08 * t
    else:
        q = 0.88 * math.sin(4 * math.pi * t + phase) + 0.17 * math.sin(2 * math.pi * t)
    z0 = 1.72 + 0.12 * (tid % 5)
    z = z0 + 1.05 * math.sin(math.pi * t) + 0.10 * math.sin(3 * math.pi * t + phase)
    vshift = 8.0 * math.sin(2 * math.pi * t + 0.23 * tid)
    return q, float(np.clip(z, 1.60, 3.25)), vshift


def _quad(mod, u: float, v: float, z: float, difficult: bool, tid: int) -> np.ndarray:
    h = mod.FX * mod.MARKER / z / 2
    if not difficult:
        return np.array([[u-h, v-h], [u+h, v-h], [u+h, v+h], [u-h, v+h]], np.float32)
    severity = 0.50 + 0.06 * (tid % 4)
    top = severity * h
    bot = (0.88 + 0.02 * (tid % 3)) * h
    skew = (0.10 + 0.025 * (tid % 3)) * h
    return np.array(
        [[u-top+skew, v-h], [u+top+skew, v-h], [u+bot-skew, v+h], [u-bot-skew, v+h]],
        np.float32,
    )


def _render(mod, tid: int, i: int, appearance: str) -> tuple[np.ndarray, dict]:
    cv2 = mod.cv2()
    difficult = tid % 3 != 0
    off = {"nominal": 0, "dim_contrast": 17, "blur_noise": 29}[appearance]
    rng = np.random.default_rng(HOLDOUT_SEED + tid * 100003 + i * 1009 + off)
    yy, xx = np.mgrid[0:mod.H, 0:mod.W]
    image = np.clip(
        203 + 8*np.sin(xx/24) + 6*np.cos(yy/17) + rng.normal(0, 3.5, (mod.H, mod.W)),
        0, 255,
    ).astype(np.uint8)
    t = i / (N - 1)
    q, z, vshift = _trajectory(tid, t)
    u = mod.CX + q * (mod.W / 2 - 2)
    v = mod.CY + vshift
    corners = _quad(mod, u, v, z, difficult, tid)
    present = 4 <= i < 44
    if present:
        dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        marker = cv2.aruco.generateImageMarker(dictionary, 0, 96)
        src = np.array([[0,0], [95,0], [95,95], [0,95]], np.float32)
        M = cv2.getPerspectiveTransform(src, corners)
        warped = cv2.warpPerspective(marker, M, (mod.W, mod.H), flags=cv2.INTER_LINEAR, borderValue=255)
        mask = cv2.warpPerspective(np.full_like(marker,255), M, (mod.W,mod.H), flags=cv2.INTER_NEAREST, borderValue=0)
        image[mask > 0] = warped[mask > 0]
    if appearance == "dim_contrast":
        image = np.clip(image.astype(float) * 0.36 + 18 + rng.normal(0, 5, image.shape), 0, 255).astype(np.uint8)
    elif appearance == "blur_noise":
        image = cv2.GaussianBlur(image, (5,5), 1.55)
        image = np.clip(image.astype(float) + rng.normal(0, 11, image.shape), 0, 255).astype(np.uint8)
    inside = (
        (corners[:,0] >= 0) & (corners[:,0] < mod.W) &
        (corners[:,1] >= 0) & (corners[:,1] < mod.H)
    )
    partial = bool(present and not inside.all())
    x = (u - mod.CX) * z / mod.FX
    margin = min(u, mod.W-1-u, v, mod.H-1-v) / (mod.FX * mod.MARKER / z / 2)
    return image, {
        "visible": present,
        "u": float(u),
        "v": float(v),
        "x": float(x),
        "z": float(z),
        "partial": partial,
        "margin": float(margin),
        "difficult": difficult,
    }


def _load_calibration(path: Path) -> dict:
    if _sha(path) != CALIBRATION_SHA256:
        raise RuntimeError("candidate calibration hash mismatch")
    return json.loads(path.read_text())


def _radius(cal: dict, source: str | None, axis: str, q: float) -> float:
    rec = cal["sources"].get(str(source), cal["fallback"])
    return float(rec[axis][f"{q:.2f}"])


def _improvement(base: float, candidate: float) -> float:
    return (base - candidate) / base if base > 0 else 0.0


def _evaluate(mod, out: Path, calibration: dict, keep_raw: bool) -> tuple[pd.DataFrame, dict]:
    rows: list[dict] = []
    raw_root = out / "raw" / "phase10r_frozen_holdout"
    for appearance in APPEARANCES:
        for tid in TRAJECTORIES:
            sid = f"holdout-t{tid:02d}-{appearance}"
            seq_dir = raw_root / sid
            if keep_raw:
                seq_dir.mkdir(parents=True, exist_ok=True)
            state = mod.State()
            for i in range(N):
                gray, truth = _render(mod, tid, i, appearance)
                payload = gray.tobytes()
                rel = f"raw/phase10r_frozen_holdout/{sid}/frame_{i:04d}.raw"
                if keep_raw:
                    (seq_dir / f"frame_{i:04d}.raw").write_bytes(payload)
                baseline = mod._detect_marker(gray, mod.MARKER, mod.FX, mod.FY, mod.CX, mod.CY)
                candidate = mod.candidate(gray, baseline, state)
                row = {
                    "evidence_role": "phase10r_frozen_holdout",
                    "holdout_seed": HOLDOUT_SEED,
                    "sequence_id": sid,
                    "trajectory_id": tid,
                    "appearance": appearance,
                    "obliquity": "difficult" if truth["difficult"] else "nominal",
                    "frame_index": i,
                    "frame_path": rel,
                    "frame_sha256": sha256(payload).hexdigest(),
                    "truth_target_visible": truth["visible"],
                    "truth_partial_edge": truth["partial"],
                    "truth_edge_margin_ratio": truth["margin"],
                    "truth_center_x_px": truth["u"],
                    "truth_lateral_x_m": truth["x"],
                    "truth_altitude_m": truth["z"],
                    "clean_aruco_truth": bool(truth["visible"] and not truth["difficult"] and appearance == "nominal" and not truth["partial"]),
                    "ambiguous_partial_truth": bool(truth["visible"] and (truth["difficult"] or truth["partial"])),
                }
                if baseline:
                    row.update(
                        baseline_available=True,
                        baseline_source=str(baseline.get("detector_kind") or "unknown"),
                        baseline_lateral_abs_error_m=abs(float(baseline["lateral_x_m"]) - truth["x"]),
                        baseline_altitude_abs_error_m=abs(float(baseline["altitude_m"]) - truth["z"]),
                    )
                else:
                    row.update(
                        baseline_available=False,
                        baseline_source=None,
                        baseline_lateral_abs_error_m=np.nan,
                        baseline_altitude_abs_error_m=np.nan,
                    )
                if candidate:
                    row.update(
                        candidate_available=True,
                        candidate_source=candidate["source"],
                        candidate_lateral_abs_error_m=abs(float(candidate["x"]) - truth["x"]),
                        candidate_altitude_abs_error_m=abs(float(candidate["z"]) - truth["z"]),
                    )
                else:
                    row.update(
                        candidate_available=False,
                        candidate_source=None,
                        candidate_lateral_abs_error_m=np.nan,
                        candidate_altitude_abs_error_m=np.nan,
                    )
                rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(out / "holdout_frames.csv", index=False)

    visible = df[df.truth_target_visible]
    ambiguous = df[df.ambiguous_partial_truth]
    clean = df[df.clean_aruco_truth]
    not_visible = df[~df.truth_target_visible]

    metrics: dict[str, object] = {
        "truth_visible_frames": int(len(visible)),
        "trajectories": int(df.sequence_id.nunique()),
        "geometry_trajectory_ids": len(TRAJECTORIES),
        "appearances": list(APPEARANCES),
        "candidate_miss_rate": float(1 - visible.candidate_available.mean()),
        "baseline_miss_rate": float(1 - visible.baseline_available.mean()),
        "candidate_false_positive_rate": float(not_visible.candidate_available.mean()),
        "baseline_false_positive_rate": float(not_visible.baseline_available.mean()),
    }

    gates: dict[str, bool] = {}
    axis_metrics: dict[str, dict] = {}
    for axis in ("lateral", "altitude"):
        b_amb = ambiguous[f"baseline_{axis}_abs_error_m"].dropna().to_numpy()
        c_amb = ambiguous[f"candidate_{axis}_abs_error_m"].dropna().to_numpy()
        b_clean = clean[f"baseline_{axis}_abs_error_m"].dropna().to_numpy()
        c_clean = clean[f"candidate_{axis}_abs_error_m"].dropna().to_numpy()
        b_mae = float(b_amb.mean())
        c_mae = float(c_amb.mean())
        b_p95 = float(np.percentile(b_amb, 95))
        c_p95 = float(np.percentile(c_amb, 95))
        clean_b = float(b_clean.mean())
        clean_c = float(c_clean.mean())
        axis_metrics[axis] = {
            "ambiguous_baseline_mae_m": b_mae,
            "ambiguous_candidate_mae_m": c_mae,
            "ambiguous_mae_improvement": _improvement(b_mae, c_mae),
            "ambiguous_baseline_p95_m": b_p95,
            "ambiguous_candidate_p95_m": c_p95,
            "ambiguous_p95_improvement": _improvement(b_p95, c_p95),
            "clean_baseline_mae_m": clean_b,
            "clean_candidate_mae_m": clean_c,
            "clean_mae_ratio": clean_c / clean_b if clean_b > 0 else 0.0,
        }
        gates[f"clean_{axis}_mae_le_1_10x"] = axis_metrics[axis]["clean_mae_ratio"] <= 1.10
        gates[f"ambiguous_{axis}_mae_improvement_ge_30pct"] = axis_metrics[axis]["ambiguous_mae_improvement"] >= 0.30
        gates[f"ambiguous_{axis}_p95_improvement_ge_25pct"] = axis_metrics[axis]["ambiguous_p95_improvement"] >= 0.25
    metrics["axes"] = axis_metrics

    covered = {}
    cvis = visible[visible.candidate_available].copy()
    for axis in ("lateral", "altitude"):
        covered[axis] = {}
        for q in TARGETS:
            hits = []
            for _, row in cvis.iterrows():
                r = _radius(calibration, row.candidate_source, axis, q)
                hits.append(float(row[f"candidate_{axis}_abs_error_m"]) <= r)
            covered[axis][f"{q:.2f}"] = float(np.mean(hits)) if hits else 0.0
    metrics["coverage"] = covered
    gates["truth_visible_miss_rate_le_10pct"] = metrics["candidate_miss_rate"] <= 0.10
    gates["false_positive_rate_le_1pct"] = metrics["candidate_false_positive_rate"] <= 0.01
    gates["lateral_95_coverage_90_to_98pct"] = 0.90 <= covered["lateral"]["0.95"] <= 0.98
    gates["altitude_95_coverage_90_to_98pct"] = 0.90 <= covered["altitude"]["0.95"] <= 0.98

    result = {
        "schema": "aegisland.phase10r.frozen-holdout-result.v1",
        "evidence_role": "phase10r_frozen_holdout",
        "candidate_freeze_sha": FROZEN_CANDIDATE_SHA,
        "calibration_sha256": CALIBRATION_SHA256,
        "holdout_seed": HOLDOUT_SEED,
        "holdout_generation_commit": os.getenv("GITHUB_SHA", "local"),
        "manual_frame_inspection_before_evaluation": False,
        "historical_phase10_holdout_used_for_selection": False,
        "validation_seed_used_for_retuning": False,
        "metrics": metrics,
        "gates": gates,
        "all_preregistered_frozen_holdout_gates_pass": bool(all(gates.values())),
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "physical_flight_validation": False,
    }
    return df, result


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--calibration", type=Path, required=True)
    p.add_argument("--no-raw", action="store_true")
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    frozen_tmp = args.out / ".frozen_source"
    mod = _load_frozen_module(frozen_tmp)
    calibration = _load_calibration(args.calibration)
    _, result = _evaluate(mod, args.out, calibration, not args.no_raw)
    _dump(args.out / "holdout_result.json", result)
    summary = result["metrics"]
    axes = summary["axes"]
    text = (
        "# Phase 10R frozen holdout\n\n"
        f"- all preregistered gates passed: **{result['all_preregistered_frozen_holdout_gates_pass']}**\n"
        f"- truth-visible frames: **{summary['truth_visible_frames']}**\n"
        f"- candidate miss rate: **{100*summary['candidate_miss_rate']:.2f}%**\n"
        f"- false-positive rate: **{100*summary['candidate_false_positive_rate']:.2f}%**\n"
        f"- ambiguous lateral MAE / p95 improvement: **{100*axes['lateral']['ambiguous_mae_improvement']:.1f}% / {100*axes['lateral']['ambiguous_p95_improvement']:.1f}%**\n"
        f"- ambiguous altitude MAE / p95 improvement: **{100*axes['altitude']['ambiguous_mae_improvement']:.1f}% / {100*axes['altitude']['ambiguous_p95_improvement']:.1f}%**\n"
        f"- 95% coverage: **{100*summary['coverage']['lateral']['0.95']:.1f}% lateral / {100*summary['coverage']['altitude']['0.95']:.1f}% altitude**\n\n"
        "Simulation-only frozen evidence. `safety_acceptance = false`; no physical-flight validation claim.\n"
    )
    (args.out / "summary.md").write_text(text)
    manifest_files = ["holdout_frames.csv", "holdout_result.json", "summary.md"]
    _dump(
        args.out / "result_manifest.json",
        {
            "schema": "aegisland.phase10r.frozen-holdout-manifest.v1",
            "files": {
                name: {"sha256": _sha(args.out / name), "bytes": (args.out / name).stat().st_size}
                for name in manifest_files
            },
        },
    )
    print(text)


if __name__ == "__main__":
    main()
