from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd

from uav_safety.phase10_calibration import Phase10UncertaintyCalibrator
from uav_safety.phase10_metric import AegisT10, MetricFrame, Phase10MetricConfig

EVIDENCE_ROLES = {"phase10_development_seen", "phase10_validation_seen", "phase10_holdout_unseen"}


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().isin({"1", "true", "yes"})


def _optional_float(row: pd.Series, key: str) -> float | None:
    value = row.get(key)
    if value is None or pd.isna(value):
        return None
    value = float(value)
    return value if np.isfinite(value) else None


def _frames(trace: pd.DataFrame, details: pd.DataFrame) -> list[MetricFrame]:
    joined = trace.merge(details[["frame_index", "detector_kind", "reprojection_rms_px", "detected_area_px2"]], on="frame_index", how="left", validate="one_to_one")
    return [MetricFrame(t_s=float(row["t_s"]), frame_index=int(row["frame_index"]), observation_available=bool(row["observation_available"]), observed_lateral_x_m=_optional_float(row, "observed_lateral_x_m"), observed_altitude_m=_optional_float(row, "observed_altitude_m"), detector_kind=None if pd.isna(row["detector_kind"]) else str(row["detector_kind"]), reprojection_rms_px=_optional_float(row, "reprojection_rms_px"), detected_area_px2=_optional_float(row, "detected_area_px2")) for _, row in joined.sort_values(["t_s", "frame_index"]).iterrows()]


def _simple_smoothing(trace: pd.DataFrame, alpha: float = 0.35) -> pd.DataFrame:
    x = z = None
    rows = []
    for _, row in trace.sort_values(["t_s", "frame_index"]).iterrows():
        available = bool(row["observation_available"])
        if available and pd.notna(row["observed_lateral_x_m"]) and pd.notna(row["observed_altitude_m"]):
            mx, mz = float(row["observed_lateral_x_m"]), float(row["observed_altitude_m"])
            if x is None: x, z = mx, mz
            else:
                x = alpha * mx + (1.0 - alpha) * x
                z = alpha * mz + (1.0 - alpha) * z
            metric_available = True
        else: metric_available = False
        rows.append({"frame_index": int(row["frame_index"]), "smooth_metric_available": metric_available, "smooth_lateral_x_m": x if metric_available else np.nan, "smooth_altitude_m": z if metric_available else np.nan})
    return pd.DataFrame(rows)


def _error_stats(truth: pd.Series, estimate: pd.Series, available: pd.Series) -> dict:
    mask = available.astype(bool) & truth.notna() & estimate.notna()
    residual = estimate[mask].astype(float).to_numpy() - truth[mask].astype(float).to_numpy()
    absolute = np.abs(residual)
    if absolute.size == 0:
        return {"n": 0, "mae": None, "median_abs": None, "rmse": None, "p90_abs": None, "p95_abs": None, "max_abs": None, "signed_bias": None}
    return {"n": int(absolute.size), "mae": float(np.mean(absolute)), "median_abs": float(np.median(absolute)), "rmse": float(np.sqrt(np.mean(residual ** 2))), "p90_abs": float(np.quantile(absolute, 0.90)), "p95_abs": float(np.quantile(absolute, 0.95)), "max_abs": float(np.max(absolute)), "signed_bias": float(np.mean(residual))}


def _reduction(new, baseline):
    if new is None or baseline is None or baseline <= 0: return None
    return float((baseline - new) / baseline)


def _result_manifest(out_dir: Path, files: list[str]) -> dict:
    manifest = {"schema": "aegisland.phase10.result-manifest.v1", "files": {}}
    for name in files:
        path = out_dir / name
        manifest["files"][name] = {"sha256": _sha256_file(path), "bytes": path.stat().st_size}
    return manifest


def run_benchmark(trace_path: Path, details_path: Path, out_dir: Path, *, evidence_role: str, calibration_path: Path | None, fit_calibration: bool) -> dict:
    if evidence_role not in EVIDENCE_ROLES: raise ValueError(f"unsupported evidence role: {evidence_role}")
    if evidence_role == "phase10_holdout_unseen" and fit_calibration: raise ValueError("holdout evaluation may not fit calibration")
    if evidence_role == "phase10_holdout_unseen" and calibration_path is None: raise ValueError("holdout evaluation requires a frozen development calibration")
    trace, details = pd.read_csv(trace_path), pd.read_csv(details_path)
    trace["truth_target_visible"] = _bool_series(trace["truth_target_visible"])
    trace["observation_available"] = _bool_series(trace["observation_available"])
    if trace["frame_index"].duplicated().any() or details["frame_index"].duplicated().any(): raise ValueError("frame_index must be unique")
    if set(trace["frame_index"]) != set(details["frame_index"]): raise ValueError("trace and detection details must cover the same frames")

    model = AegisT10(Phase10MetricConfig())
    started = time.perf_counter()
    estimates = [model.update(frame) for frame in _frames(trace, details)]
    runtime_s = time.perf_counter() - started
    estimate_df = pd.DataFrame([estimate.to_dict() for estimate in estimates])
    joined = trace.merge(details, on="frame_index", how="left", validate="one_to_one").merge(estimate_df, on=["frame_index", "t_s"], how="left", validate="one_to_one").merge(_simple_smoothing(trace), on="frame_index", how="left", validate="one_to_one").sort_values(["t_s", "frame_index"]).reset_index(drop=True)
    visible = joined["truth_target_visible"].astype(bool); model_available = joined["metric_estimate_available"].astype(bool); baseline_available = joined["observation_available"].astype(bool); smooth_available = joined["smooth_metric_available"].astype(bool)
    joined["baseline_lateral_abs_error_m"] = np.where(visible & baseline_available, np.abs(joined["observed_lateral_x_m"] - joined["truth_lateral_x_m"]), np.nan)
    joined["baseline_altitude_abs_error_m"] = np.where(visible & baseline_available, np.abs(joined["observed_altitude_m"] - joined["truth_altitude_m"]), np.nan)
    joined["phase10_lateral_abs_error_m"] = np.where(visible & model_available, np.abs(joined["lateral_x_m"] - joined["truth_lateral_x_m"]), np.nan)
    joined["phase10_altitude_abs_error_m"] = np.where(visible & model_available, np.abs(joined["altitude_m"] - joined["truth_altitude_m"]), np.nan)
    calibration_samples = [{"source": str(row["source"]), "abs_lateral_error_m": float(row["phase10_lateral_abs_error_m"]), "abs_altitude_error_m": float(row["phase10_altitude_abs_error_m"])} for _, row in joined[visible & model_available & joined["phase10_lateral_abs_error_m"].notna() & joined["phase10_altitude_abs_error_m"].notna()].iterrows()]
    calibrator = Phase10UncertaintyCalibrator.fit(calibration_samples) if fit_calibration else (Phase10UncertaintyCalibrator.load(calibration_path) if calibration_path else None)
    if calibrator:
        sigmas = joined["source"].map(lambda source: calibrator.sigma(str(source)))
        joined["phase10_sigma_lateral_m"] = [v[0] for v in sigmas]; joined["phase10_sigma_altitude_m"] = [v[1] for v in sigmas]
        joined["phase10_norm_lateral_residual"] = joined["phase10_lateral_abs_error_m"] / joined["phase10_sigma_lateral_m"]
        joined["phase10_norm_altitude_residual"] = joined["phase10_altitude_abs_error_m"] / joined["phase10_sigma_altitude_m"]
    else:
        joined["phase10_sigma_lateral_m"] = np.nan; joined["phase10_sigma_altitude_m"] = np.nan; joined["phase10_norm_lateral_residual"] = np.nan; joined["phase10_norm_altitude_residual"] = np.nan
    baseline_x = _error_stats(joined["truth_lateral_x_m"], joined["observed_lateral_x_m"], visible & baseline_available); baseline_z = _error_stats(joined["truth_altitude_m"], joined["observed_altitude_m"], visible & baseline_available)
    smooth_x = _error_stats(joined["truth_lateral_x_m"], joined["smooth_lateral_x_m"], visible & smooth_available); smooth_z = _error_stats(joined["truth_altitude_m"], joined["smooth_altitude_m"], visible & smooth_available)
    phase10_x = _error_stats(joined["truth_lateral_x_m"], joined["lateral_x_m"], visible & model_available); phase10_z = _error_stats(joined["truth_altitude_m"], joined["altitude_m"], visible & model_available)
    visible_count = int(visible.sum()); front_end_visible_obs = int((visible & baseline_available).sum()); model_visible_estimates = int((visible & model_available).sum()); false_positive_front_end = int((~visible & baseline_available).sum()); false_positive_metric = int((~visible & model_available).sum())
    normalized = joined[visible & model_available]; nx = normalized["phase10_norm_lateral_residual"].dropna().to_numpy(dtype=float); nz = normalized["phase10_norm_altitude_residual"].dropna().to_numpy(dtype=float)
    uncertainty = {"calibrated": calibrator is not None, "median_norm_lateral_residual": None if nx.size == 0 else float(np.median(nx)), "p95_norm_lateral_residual": None if nx.size == 0 else float(np.quantile(nx, .95)), "median_norm_altitude_residual": None if nz.size == 0 else float(np.median(nz)), "p95_norm_altitude_residual": None if nz.size == 0 else float(np.quantile(nz, .95)), "lateral_1sigma_coverage": None if nx.size == 0 else float(np.mean(nx <= 1)), "lateral_2sigma_coverage": None if nx.size == 0 else float(np.mean(nx <= 2)), "altitude_1sigma_coverage": None if nz.size == 0 else float(np.mean(nz <= 1)), "altitude_2sigma_coverage": None if nz.size == 0 else float(np.mean(nz <= 2))}
    reductions = {"lateral_mae": _reduction(phase10_x["mae"], baseline_x["mae"]), "altitude_mae": _reduction(phase10_z["mae"], baseline_z["mae"]), "lateral_p95": _reduction(phase10_x["p95_abs"], baseline_x["p95_abs"]), "altitude_p95": _reduction(phase10_z["p95_abs"], baseline_z["p95_abs"])}
    availability_drop_pp = 0.0 if visible_count == 0 else 100.0 * (front_end_visible_obs - model_visible_estimates) / visible_count
    gate = {"lateral_mae_reduction_ge_50pct": reductions["lateral_mae"] is not None and reductions["lateral_mae"] >= .50, "altitude_mae_reduction_ge_50pct": reductions["altitude_mae"] is not None and reductions["altitude_mae"] >= .50, "lateral_p95_reduction_ge_35pct": reductions["lateral_p95"] is not None and reductions["lateral_p95"] >= .35, "altitude_p95_reduction_ge_35pct": reductions["altitude_p95"] is not None and reductions["altitude_p95"] >= .35, "metric_availability_drop_le_2pp": availability_drop_pp <= 2.0, "no_false_positive_regression": false_positive_metric <= false_positive_front_end, "median_norm_lateral_below_2": uncertainty["median_norm_lateral_residual"] is not None and uncertainty["median_norm_lateral_residual"] < 2.0, "median_norm_altitude_below_2": uncertainty["median_norm_altitude_residual"] is not None and uncertainty["median_norm_altitude_residual"] < 2.0}
    result = {"schema": "aegisland.phase10.metric-result.v1", "evidence_role": evidence_role, "simulation_only": True, "safety_acceptance": False, "controller_tuning_allowed": False, "phase10_model": "AegisT10-deterministic-temporal", "phase10_config": Phase10MetricConfig().to_dict(), "inputs": {"trace": str(trace_path), "trace_sha256": _sha256_file(trace_path), "detection_details": str(details_path), "detection_details_sha256": _sha256_file(details_path), "calibration": None if calibration_path is None else str(calibration_path), "calibration_sha256": None if calibration_path is None else _sha256_file(calibration_path)}, "availability": {"truth_visible_frames": visible_count, "phase9_front_end_observations_on_visible": front_end_visible_obs, "phase10_metric_estimates_on_visible": model_visible_estimates, "phase10_metric_availability_drop_percentage_points": availability_drop_pp, "phase9_false_positive_observations": false_positive_front_end, "phase10_false_positive_metric_estimates": false_positive_metric}, "phase9_baseline": {"lateral": baseline_x, "altitude": baseline_z}, "simple_causal_smoothing": {"lateral": smooth_x, "altitude": smooth_z}, "phase10": {"lateral": phase10_x, "altitude": phase10_z}, "relative_reductions": reductions, "uncertainty": uncertainty, "source_counts": {str(k): int(v) for k, v in joined.loc[visible & model_available, "source"].value_counts().items()}, "minimum_substantial_win_gate": gate, "minimum_substantial_win_gate_all": bool(all(gate.values())), "compute": {"frames": int(len(joined)), "total_model_runtime_ms": float(runtime_s*1000), "mean_model_runtime_ms_per_frame": float(runtime_s*1000/max(1,len(joined)))}, "interpretation": "development-only; not a final Phase 10 claim" if evidence_role != "phase10_holdout_unseen" else "frozen holdout result; simulation only; not physical-flight validation"}
    out_dir.mkdir(parents=True, exist_ok=True); joined.to_csv(out_dir / "per_frame.csv", index=False); (out_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True)+"\n")
    if fit_calibration and calibrator: calibrator.save(out_dir / "calibration.json")
    summary = ["# AegisT10 metric benchmark", "", f"Evidence role: `{evidence_role}`", "", "Simulation only. `safety_acceptance = false`.", "", "## Paired result", "", "| Metric | Phase 9 | Simple smoothing | AegisT10 | Reduction vs Phase 9 |", "|---|---:|---:|---:|---:|", f"| lateral MAE (m) | {baseline_x['mae']:.4f} | {smooth_x['mae']:.4f} | {phase10_x['mae']:.4f} | {100*reductions['lateral_mae']:.1f}% |", f"| altitude MAE (m) | {baseline_z['mae']:.4f} | {smooth_z['mae']:.4f} | {phase10_z['mae']:.4f} | {100*reductions['altitude_mae']:.1f}% |", f"| lateral p95 (m) | {baseline_x['p95_abs']:.4f} | {smooth_x['p95_abs']:.4f} | {phase10_x['p95_abs']:.4f} | {100*reductions['lateral_p95']:.1f}% |", f"| altitude p95 (m) | {baseline_z['p95_abs']:.4f} | {smooth_z['p95_abs']:.4f} | {phase10_z['p95_abs']:.4f} | {100*reductions['altitude_p95']:.1f}% |", "", "Predicted-through rejected quads are explicitly marked prediction-only and are never labelled as fresh geometry."]
    (out_dir / "summary.md").write_text("\n".join(summary)+"\n"); files=["per_frame.csv","result.json","summary.md"] + (["calibration.json"] if fit_calibration else []); manifest=_result_manifest(out_dir,files); (out_dir/"result_manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    return result


def main():
    parser=argparse.ArgumentParser(description="Run paired Phase 9 / AegisT10 metric benchmark."); parser.add_argument("trace",type=Path); parser.add_argument("detection_details",type=Path); parser.add_argument("--out",type=Path,required=True); parser.add_argument("--evidence-role",choices=sorted(EVIDENCE_ROLES),required=True); parser.add_argument("--calibration",type=Path); parser.add_argument("--fit-calibration",action="store_true"); args=parser.parse_args(); print(json.dumps(run_benchmark(args.trace,args.detection_details,args.out,evidence_role=args.evidence_role,calibration_path=args.calibration,fit_calibration=args.fit_calibration),indent=2,sort_keys=True))

if __name__ == "__main__": main()
