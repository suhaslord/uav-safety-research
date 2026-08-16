from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scripts import run_phase11_p1_adaptive_reliability as p1
except ModuleNotFoundError:
    import run_phase11_p1_adaptive_reliability as p1

FIT_SEED = 209209
CALIBRATION_SEED = 220220
TRANSFER_SEED = 231231
VALIDATION_SEED = 242242
FRAMES_PER_SEQUENCE = 60
TARGETS = (0.50, 0.68, 0.80, 0.90, 0.95)
RIDGE_LAMBDA = 4.0
MAX_BRIDGE_HORIZON = 5
FIT_FAMILIES = tuple(range(72, 78))
CALIBRATION_FAMILIES = tuple(range(78, 81))
TRANSFER_FAMILIES = tuple(range(81, 84))
VALIDATION_FAMILIES = tuple(range(84, 87))
FIT_DOMAINS = p1.FIT_DOMAINS
TRANSFER_DOMAINS = (
    "edge+temporal_dropout",
    "small_scale+blur_noise",
    "oblique+dim",
    "blur_noise+low_contrast",
    "edge+small_scale+temporal_dropout",
    "oblique+blur_noise+low_contrast",
    "edge+dim+temporal_dropout",
    "small_scale+oblique+blur_noise",
)
VALIDATION_DOMAINS = (
    "edge+blur_noise",
    "small_scale+dim+temporal_dropout",
    "oblique+low_contrast",
    "edge+small_scale+dim",
    "blur_noise+low_contrast+temporal_dropout",
    "edge+oblique+temporal_dropout",
    "small_scale+oblique+dim+low_contrast",
    "edge+small_scale+oblique+blur_noise+temporal_dropout",
)
RISK_COLUMNS = tuple(f"risk_{name}" for name in ("edge", "scale", "oblique", "dim", "blur", "contrast", "temporal", "track"))


def _raw(name: str, seed: int, families: tuple[int, ...], domains: tuple[str, ...]) -> pd.DataFrame:
    return p1.generate_split(name, seed, families, domains, frames=FRAMES_PER_SEQUENCE)


def fit_velocity_caps(fit_raw: pd.DataFrame) -> dict[str, float]:
    lateral_rates: list[float] = []
    altitude_rates: list[float] = []
    for _, group in fit_raw.groupby("sequence_id"):
        direct = group[group["candidate_available"]].sort_values("frame_index")
        rows = list(direct.itertuples(index=False))
        for a, b in zip(rows[:-1], rows[1:]):
            dt = max(1, int(b.frame_index) - int(a.frame_index))
            lateral_rates.append(abs(float(b.estimate_lateral_x_m) - float(a.estimate_lateral_x_m)) / dt)
            altitude_rates.append(abs(float(b.estimate_altitude_m) - float(a.estimate_altitude_m)) / dt)
    if not lateral_rates or not altitude_rates:
        raise ValueError("fit split does not contain enough direct transitions")
    return {
        "lateral_per_frame": float(np.quantile(lateral_rates, 0.99)),
        "altitude_per_frame": float(np.quantile(altitude_rates, 0.99)),
    }


def add_continuity_bridge(df: pd.DataFrame, velocity_caps: dict[str, float]) -> pd.DataFrame:
    out = df.copy()
    out["p1_available"] = out["candidate_available"].astype(bool)
    out["p1_estimate_lateral_x_m"] = out["estimate_lateral_x_m"]
    out["p1_estimate_altitude_m"] = out["estimate_altitude_m"]
    out["p1_source"] = out["candidate_source"].fillna("")
    out["bridge_horizon"] = 0

    for _, indices in out.groupby("sequence_id").groups.items():
        ordered = sorted(indices, key=lambda i: int(out.loc[i, "frame_index"]))
        history: list[tuple[int, float, float]] = []
        for i in ordered:
            frame = int(out.loc[i, "frame_index"])
            if bool(out.loc[i, "candidate_available"]):
                history.append((frame, float(out.loc[i, "estimate_lateral_x_m"]), float(out.loc[i, "estimate_altitude_m"])))
                history = history[-2:]
                continue
            if not history:
                continue
            last_frame, last_x, last_z = history[-1]
            horizon = frame - last_frame
            if horizon < 1 or horizon > MAX_BRIDGE_HORIZON:
                continue
            if len(history) == 1:
                if horizon != 1:
                    continue
                pred_x, pred_z = last_x, last_z
            else:
                first_frame, first_x, first_z = history[-2]
                dt = max(1, last_frame - first_frame)
                vx = (last_x - first_x) / dt
                vz = (last_z - first_z) / dt
                vx = float(np.clip(vx, -velocity_caps["lateral_per_frame"], velocity_caps["lateral_per_frame"]))
                vz = float(np.clip(vz, -velocity_caps["altitude_per_frame"], velocity_caps["altitude_per_frame"]))
                pred_x = last_x + vx * horizon
                pred_z = last_z + vz * horizon
            out.loc[i, "p1_available"] = True
            out.loc[i, "p1_estimate_lateral_x_m"] = pred_x
            out.loc[i, "p1_estimate_altitude_m"] = pred_z
            out.loc[i, "p1_source"] = "temporal_bridge"
            out.loc[i, "bridge_horizon"] = horizon

    out["p1_lateral_abs_error_m"] = np.abs(out["p1_estimate_lateral_x_m"] - out["truth_lateral_x_m"])
    out["p1_altitude_abs_error_m"] = np.abs(out["p1_estimate_altitude_m"] - out["truth_altitude_m"])
    return out


def _prepare(raw: pd.DataFrame, velocity_caps: dict[str, float]) -> pd.DataFrame:
    return p1.add_reliability_state(add_continuity_bridge(raw, velocity_caps))


def _available(df: pd.DataFrame) -> pd.Series:
    return df["p1_available"].astype(bool) & df["truth_visible"].astype(bool)


def _continuous_basis(df: pd.DataFrame) -> np.ndarray:
    risks = df[list(RISK_COLUMNS)].to_numpy(float)
    primary = risks[:, :7]
    ordered = np.sort(primary, axis=1)
    return np.column_stack([
        risks,
        df["risk_score"].to_numpy(float),
        df["coactivation_count"].to_numpy(float) / 7.0,
        ordered[:, -1],
        ordered[:, -2],
        df["bridge_horizon"].to_numpy(float) / MAX_BRIDGE_HORIZON,
    ])


def _source_basis(df: pd.DataFrame) -> np.ndarray:
    source = df["p1_source"].fillna("").astype(str)
    return np.column_stack([
        (source == "partial_edge").to_numpy(float),
        (source == "phase9_center_regeometry").to_numpy(float),
        (source == "known_aruco_refined").to_numpy(float),
        (source == "temporal_bridge").to_numpy(float),
    ])


def _fit_standardizer(df: pd.DataFrame) -> dict[str, list[float]]:
    x = _continuous_basis(df)
    mean = x.mean(axis=0)
    std = np.where(x.std(axis=0) < 1e-6, 1.0, x.std(axis=0))
    return {"mean": mean.tolist(), "std": std.tolist()}


def _design(df: pd.DataFrame, standardizer: dict[str, list[float]]) -> np.ndarray:
    x = _continuous_basis(df)
    z = (x - np.asarray(standardizer["mean"])) / np.asarray(standardizer["std"])
    return np.column_stack([np.ones(len(df)), z, _source_basis(df)])


def _ridge_fit(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    penalty = np.eye(x.shape[1]); penalty[0, 0] = 0.0
    return np.linalg.solve(x.T @ x + RIDGE_LAMBDA * penalty, x.T @ y)


def fit_scale_model(fit: pd.DataFrame) -> dict[str, object]:
    d = fit[_available(fit)].copy()
    standardizer = _fit_standardizer(d)
    x = _design(d, standardizer)
    axes = {}
    for axis in ("lateral", "altitude"):
        raw_y = np.log(d[f"p1_{axis}_abs_error_m"].to_numpy(float) + 1e-4)
        lo, hi = np.quantile(raw_y, [0.02, 0.98])
        y = np.clip(raw_y, lo, hi)
        beta = _ridge_fit(x, y)
        fitted = x @ beta
        pred_lo, pred_hi = np.quantile(fitted, [0.01, 0.99])
        axes[axis] = {
            "coefficients": beta.tolist(),
            "target_winsor_log_bounds": [float(lo), float(hi)],
            "prediction_guard_log_bounds": [float(pred_lo - 0.35), float(pred_hi + 0.35)],
        }
    return {"standardizer": standardizer, "axes": axes}


def predicted_scale(df: pd.DataFrame, model: dict[str, object], axis: str) -> np.ndarray:
    x = _design(df, model["standardizer"])
    info = model["axes"][axis]
    log_scale = x @ np.asarray(info["coefficients"])
    lo, hi = info["prediction_guard_log_bounds"]
    return np.exp(np.clip(log_scale, lo, hi))


def conformal(values: np.ndarray, q: float) -> float:
    arr = np.sort(np.asarray(values, dtype=float)[np.isfinite(values)])
    if not len(arr):
        return float("nan")
    k = int(math.ceil((len(arr) + 1) * q))
    return float(arr[min(len(arr) - 1, max(0, k - 1))])


def single_factor_calibration(calibration: pd.DataFrame, model: dict[str, object]) -> dict[str, dict[str, float]]:
    d = calibration[_available(calibration)].copy()
    out = {}
    for axis in ("lateral", "altitude"):
        norm = d[f"p1_{axis}_abs_error_m"].to_numpy(float) / np.maximum(predicted_scale(d, model, axis), 1e-9)
        out[axis] = {f"{q:.2f}": conformal(norm, q) for q in TARGETS}
    return out


def provisional(df: pd.DataFrame, candidate: dict[str, object], axis: str, q: float) -> np.ndarray:
    return predicted_scale(df, candidate["scale_model"], axis) * float(candidate["single_factor_conformal"][axis][f"{q:.2f}"])


def transfer_calibration(transfer: pd.DataFrame, model: dict[str, object], single: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    d = transfer[_available(transfer)].copy()
    candidate = {"scale_model": model, "single_factor_conformal": single}
    out = {}
    for axis in ("lateral", "altitude"):
        err = d[f"p1_{axis}_abs_error_m"].to_numpy(float)
        out[axis] = {}
        for q in TARGETS:
            ratio = err / np.maximum(provisional(d, candidate, axis, q), 1e-9)
            out[axis][f"{q:.2f}"] = conformal(ratio, q)
    return out


def halfwidths(df: pd.DataFrame, candidate: dict[str, object], axis: str) -> dict[str, np.ndarray]:
    cols = [provisional(df, candidate, axis, q) * float(candidate["transfer_multipliers"][axis][f"{q:.2f}"]) for q in TARGETS]
    nested = np.maximum.accumulate(np.column_stack(cols), axis=1)
    return {f"{q:.2f}": nested[:, i] for i, q in enumerate(TARGETS)}


def build_candidate(fit: pd.DataFrame, calibration: pd.DataFrame, transfer: pd.DataFrame, velocity_caps: dict[str, float], git_sha: str) -> dict[str, object]:
    model = fit_scale_model(fit)
    single = single_factor_calibration(calibration, model)
    transfer_multipliers = transfer_calibration(transfer, model, single)
    return {
        "schema": "aegisland.phase11.p5.candidate-freeze.v1",
        "git_sha": git_sha,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "validation_seed_unseen_at_freeze": VALIDATION_SEED,
        "max_bridge_horizon": MAX_BRIDGE_HORIZON,
        "velocity_caps": velocity_caps,
        "ridge_lambda": RIDGE_LAMBDA,
        "scale_model": model,
        "single_factor_conformal": single,
        "transfer_multipliers": transfer_multipliers,
    }


def coverage(df: pd.DataFrame, candidate: dict[str, object], mask: pd.Series | None = None) -> dict[str, dict[str, float]]:
    use = _available(df) if mask is None else (_available(df) & mask)
    d = df[use].copy()
    out = {}
    for axis in ("lateral", "altitude"):
        widths = halfwidths(d, candidate, axis)
        err = d[f"p1_{axis}_abs_error_m"].to_numpy(float)
        out[axis] = {f"{q:.2f}": float(np.mean(err <= widths[f"{q:.2f}"])) if len(err) else float("nan") for q in TARGETS}
    return out


def error_stats(df: pd.DataFrame) -> dict[str, float]:
    available = _available(df)
    d = df[available]
    out = {"availability": float(available.mean()), "long_bridge_count": int(((df["bridge_horizon"] >= 3) & available).sum())}
    for axis in ("lateral", "altitude"):
        values = d[f"p1_{axis}_abs_error_m"].dropna().to_numpy(float)
        out[f"{axis}_mae"] = float(np.mean(values)) if len(values) else float("nan")
        out[f"{axis}_p95"] = float(np.percentile(values, 95)) if len(values) else float("nan")
    return out


def interval_stats(df: pd.DataFrame, candidate: dict[str, object]) -> dict[str, dict[str, float]]:
    d = df[_available(df)].copy()
    out = {}
    for axis in ("lateral", "altitude"):
        hw = halfwidths(d, candidate, axis)["0.95"]
        out[axis] = {"median_halfwidth_95": float(np.median(hw)), "p95_halfwidth_95": float(np.percentile(hw, 95))}
    return out


def _auc(labels: np.ndarray, scores: np.ndarray) -> float:
    pos, neg = scores[labels == 1], scores[labels == 0]
    if not len(pos) or not len(neg): return float("nan")
    wins = sum(float(np.sum(p > neg)) + 0.5 * float(np.sum(p == neg)) for p in pos)
    return float(wins / (len(pos) * len(neg)))


def shift_auc(calibration: pd.DataFrame, evaluated: pd.DataFrame) -> float:
    a = calibration.groupby("sequence_id", as_index=False)["severity"].mean(); a["label"] = 0
    b = evaluated.groupby("sequence_id", as_index=False)["severity"].mean(); b["label"] = 1
    z = pd.concat([a, b], ignore_index=True)
    return _auc(z["label"].to_numpy(int), z["severity"].to_numpy(float))


def summarize(evaluated: pd.DataFrame, calibration: pd.DataFrame, candidate: dict[str, object], role: str, seed: int) -> dict[str, object]:
    cov = coverage(evaluated, candidate)
    errors = error_stats(evaluated)
    intervals = interval_stats(evaluated, candidate)
    h1 = {"availability": errors["availability"], "pass": bool(errors["availability"] >= 0.90)}
    h2 = {"lateral_95_coverage": cov["lateral"]["0.95"], "altitude_95_coverage": cov["altitude"]["0.95"]}
    h2["pass"] = bool(0.90 <= h2["lateral_95_coverage"] <= 0.98 and 0.90 <= h2["altitude_95_coverage"] <= 0.98)
    mace = float(np.mean([abs(cov[a][f"{q:.2f}"] - q) for a in ("lateral", "altitude") for q in TARGETS]))
    h3 = {"mean_absolute_coverage_error": mace, "pass": bool(mace <= 0.06)}
    h4 = {}
    for axis in ("lateral", "altitude"):
        p95 = errors[f"{axis}_p95"]
        h4[f"{axis}_median_halfwidth_over_p95_error"] = intervals[axis]["median_halfwidth_95"] / p95
        h4[f"{axis}_p95_halfwidth_over_p95_error"] = intervals[axis]["p95_halfwidth_95"] / p95
    h4["pass"] = bool(all(h4[k] <= (1.25 if "median" in k else 2.25) for k in h4 if k != "pass"))

    long_mask = evaluated["bridge_horizon"].between(3, 5)
    long_count = int((_available(evaluated) & long_mask).sum())
    h5 = {"long_bridge_count": long_count}
    if long_count >= 40:
        long_cov = coverage(evaluated, candidate, long_mask)
        long_df = evaluated[_available(evaluated) & long_mask].copy()
        h5["lateral_95_coverage"] = long_cov["lateral"]["0.95"]
        h5["altitude_95_coverage"] = long_cov["altitude"]["0.95"]
        for axis in ("lateral", "altitude"):
            median_error = float(np.median(long_df[f"p1_{axis}_abs_error_m"]))
            median_hw = float(np.median(halfwidths(long_df, candidate, axis)["0.95"]))
            h5[f"{axis}_median_halfwidth_over_median_error"] = median_hw / max(median_error, 1e-12)
        h5["pass"] = bool(h5["lateral_95_coverage"] >= 0.88 and h5["altitude_95_coverage"] >= 0.88 and h5["lateral_median_halfwidth_over_median_error"] >= 1.0 and h5["altitude_median_halfwidth_over_median_error"] >= 1.0)
    else:
        h5["pass"] = False
        h5["insufficient_evidence"] = True

    h6 = {"trajectory_level_auroc": shift_auc(calibration, evaluated)}
    h6["pass"] = bool(h6["trajectory_level_auroc"] >= 0.85)
    gates = {"h1_availability": h1, "h2_coverage": h2, "h3_calibration_curve": h3, "h4_interval_efficiency": h4, "h5_long_bridge_honesty": h5, "h6_shift_discrimination": h6}
    return {"schema": "aegisland.phase11.p5.result.v1", "evidence_role": role, "simulation_only": True, "safety_acceptance": False, "controller_tuning_allowed": False, "evaluated_seed_seen_after_run": seed, "all_primary_gates_pass": bool(all(g["pass"] for g in gates.values())), "gates": gates, "coverage": cov, "error_stats": errors, "interval_stats": intervals}


def freeze(out: Path, git_sha: str) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    fit_raw = _raw("fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS)
    caps = fit_velocity_caps(fit_raw)
    fit = _prepare(fit_raw, caps)
    calibration = _prepare(_raw("calibration", CALIBRATION_SEED, CALIBRATION_FAMILIES, FIT_DOMAINS), caps)
    transfer = _prepare(_raw("transfer", TRANSFER_SEED, TRANSFER_FAMILIES, TRANSFER_DOMAINS), caps)
    candidate = build_candidate(fit, calibration, transfer, caps, git_sha)
    result = summarize(transfer, calibration, candidate, "phase11_p5_seen_transfer_calibration", TRANSFER_SEED)
    fit.to_csv(out / "fit_frames.csv", index=False); calibration.to_csv(out / "calibration_frames.csv", index=False); transfer.to_csv(out / "transfer_frames.csv", index=False)
    (out / "candidate_freeze.json").write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n")
    (out / "transfer_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("P5_CANDIDATE_FREEZE_JSON=" + json.dumps(candidate, sort_keys=True))
    print("P5_TRANSFER_GATES=" + json.dumps(result["gates"], sort_keys=True))
    return candidate


def validate(out: Path, candidate_path: Path, git_sha: str) -> dict[str, object]:
    candidate = json.loads(candidate_path.read_text())
    if int(candidate.get("validation_seed_unseen_at_freeze", -1)) != VALIDATION_SEED: raise SystemExit("candidate validation seed mismatch")
    caps = candidate["velocity_caps"]
    calibration = _prepare(_raw("calibration", CALIBRATION_SEED, CALIBRATION_FAMILIES, FIT_DOMAINS), caps)
    validation = _prepare(_raw("validation", VALIDATION_SEED, VALIDATION_FAMILIES, VALIDATION_DOMAINS), caps)
    result = summarize(validation, calibration, candidate, "phase11_p5_frozen_candidate_validation", VALIDATION_SEED)
    result["git_sha"] = git_sha
    out.mkdir(parents=True, exist_ok=True)
    validation.to_csv(out / "validation_frames.csv", index=False)
    (out / "validation_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("P5_VALIDATION_GATES=" + json.dumps(result["gates"], sort_keys=True))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("freeze", "validation"), required=True)
    parser.add_argument("--out", type=Path, default=Path("results/phase11_p5"))
    parser.add_argument("--candidate", type=Path, default=Path("results/phase11_p5/candidate_freeze.json"))
    parser.add_argument("--git-sha", default="unknown")
    args = parser.parse_args()
    freeze(args.out, args.git_sha) if args.stage == "freeze" else validate(args.out, args.candidate, args.git_sha)


if __name__ == "__main__": main()
