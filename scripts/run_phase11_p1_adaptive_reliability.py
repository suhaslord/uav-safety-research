from __future__ import annotations

import argparse
import json
import math
import subprocess
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd

FRAMES_PER_SEQUENCE = 60
FIT_SEED = 44044
CALIBRATION_SEED = 55055
DEVELOPMENT_SEED = 66066
VALIDATION_SEED = 77077
FIT_FAMILIES = tuple(range(12, 18))
CALIBRATION_FAMILIES = tuple(range(18, 21))
DEVELOPMENT_FAMILIES = tuple(range(21, 24))
VALIDATION_FAMILIES = tuple(range(24, 27))
FIT_DOMAINS = ("nominal", "edge", "small_scale", "oblique", "dim", "blur_noise", "temporal_dropout", "low_contrast")
DEVELOPMENT_DOMAINS = (
    "edge+dim",
    "small_scale+blur_noise",
    "oblique+low_contrast",
    "edge+temporal_dropout",
    "dim+blur_noise",
    "small_scale+oblique",
    "edge+low_contrast+temporal_dropout",
    "small_scale+dim+blur_noise",
)
VALIDATION_DOMAINS = (
    "edge+blur_noise",
    "small_scale+dim",
    "oblique+temporal_dropout",
    "blur_noise+low_contrast",
    "edge+small_scale+oblique",
    "dim+low_contrast+temporal_dropout",
    "edge+oblique+blur_noise+low_contrast",
    "small_scale+oblique+dim+temporal_dropout",
)
TARGETS = (0.50, 0.68, 0.80, 0.90, 0.95)
RISK_WEIGHTS = {"edge": 0.18, "scale": 0.12, "oblique": 0.12, "dim": 0.12, "blur": 0.12, "contrast": 0.10, "temporal": 0.14, "track": 0.10}
MAX_BRIDGE_GAP = 2
COACTIVATION_THRESHOLD = 0.45
SEVERITY_COACTIVATION_WEIGHT = 0.75
SEVERITY_BRIDGE_WEIGHT = 0.25
ACCEPTANCE_THRESHOLD = 0.40078671864763
RIDGE_LAMBDA = 1.0
MULTIPLIER_COACTIVATION = 3.0
MULTIPLIER_RISK = 6.0
MULTIPLIER_BRIDGE = 2.0


def _clip01(x: float) -> float:
    return float(min(1.0, max(0.0, x)))


def _factors(domain: str) -> set[str]:
    return set(domain.split("+")) if domain != "nominal" else set()


def _trajectory(family: int, frame: int, n: int) -> tuple[float, float]:
    t = frame / max(1, n - 1)
    phase = (family % 6) * 0.43
    freq = 1.0 + (family % 3) * 0.35
    lateral = 0.42 * math.sin(2 * math.pi * freq * t + phase) + 0.10 * math.sin(5 * math.pi * t + 0.2 * family)
    altitude = 2.15 + 0.45 * math.sin(math.pi * t + phase * 0.3) + 0.06 * ((family % 5) - 2)
    return float(lateral), float(max(1.15, altitude))


def _latent_context(domain: str, family: int, frame: int, n: int) -> dict[str, float | bool]:
    factors = _factors(domain)
    t = frame / max(1, n - 1)
    edge_wave = abs(math.sin(2 * math.pi * t + 0.31 * family))
    edge = 0.10 + 0.26 * edge_wave + (0.56 if "edge" in factors else 0.0)
    scale = 0.10 + (0.67 if "small_scale" in factors else 0.0)
    oblique = 0.08 + (0.72 if "oblique" in factors else 0.0)
    dim = 0.72 if "dim" in factors else 0.0
    blur = 0.72 if "blur_noise" in factors else 0.0
    contrast = 0.68 if "low_contrast" in factors else 0.0
    dropout_event = "temporal_dropout" in factors and frame % 15 in (7, 8)
    reacquisition = "temporal_dropout" in factors and frame % 15 == 9
    temporal = 0.12 + (0.72 if dropout_event else 0.32 if reacquisition else 0.0)
    track = 0.10 + 0.48 * temporal + 0.18 * edge + 0.05 * blur
    return {"edge": _clip01(edge), "scale": _clip01(scale), "oblique": _clip01(oblique), "dim": _clip01(dim), "blur": _clip01(blur), "contrast": _clip01(contrast), "temporal": _clip01(temporal), "track": _clip01(track), "dropout_event": bool(dropout_event), "reacquisition": bool(reacquisition)}


def _observed_features(latent: dict[str, float | bool], rng: np.random.Generator) -> dict[str, float | bool]:
    noise = lambda s: float(rng.normal(0.0, s))
    edge = _clip01(float(latent["edge"]) + noise(0.035))
    scale = _clip01(float(latent["scale"]) + noise(0.035))
    oblique = _clip01(float(latent["oblique"]) + noise(0.035))
    dim = _clip01(float(latent["dim"]) + noise(0.040))
    blur = _clip01(float(latent["blur"]) + noise(0.040))
    contrast = _clip01(float(latent["contrast"]) + noise(0.040))
    temporal = _clip01(float(latent["temporal"]) + noise(0.035))
    track = _clip01(float(latent["track"]) + noise(0.035))
    return {
        "edge_margin_ratio": float(max(-0.25, 1.12 - 1.42 * edge + noise(0.025))),
        "visible_fraction_proxy": _clip01(1.02 - 0.74 * edge + noise(0.025)),
        "projected_scale_px": float(max(8.0, 84.0 - 62.0 * scale + noise(1.8))),
        "obliquity_proxy": _clip01(oblique + noise(0.015)),
        "brightness_mean": float(np.clip(205.0 - 120.0 * dim - 10.0 * contrast + noise(5.0), 25.0, 235.0)),
        "contrast_std": float(np.clip(52.0 - 34.0 * contrast - 8.0 * blur + noise(2.5), 6.0, 65.0)),
        "laplacian_var": float(np.clip(180.0 - 150.0 * blur - 18.0 * contrast + noise(8.0), 8.0, 220.0)),
        "temporal_innovation": _clip01(temporal + noise(0.025)),
        "track_stability": _clip01(1.0 - track + noise(0.025)),
        "reacquisition": bool(latent["reacquisition"]),
    }


def reliability_components(features: dict[str, object] | pd.Series) -> dict[str, float]:
    edge = max(_clip01((0.85 - float(features["edge_margin_ratio"])) / 1.10), _clip01((0.72 - float(features["visible_fraction_proxy"])) / 0.72))
    scale = _clip01((52.0 - float(features["projected_scale_px"])) / 44.0)
    oblique = _clip01(float(features["obliquity_proxy"]))
    dim = _clip01((175.0 - float(features["brightness_mean"])) / 130.0)
    blur = _clip01((125.0 - float(features["laplacian_var"])) / 117.0)
    contrast = _clip01((38.0 - float(features["contrast_std"])) / 32.0)
    temporal = _clip01(float(features["temporal_innovation"]))
    track = max(_clip01(1.0 - float(features["track_stability"])), 0.88 if bool(features["reacquisition"]) else 0.0)
    return {"edge": edge, "scale": scale, "oblique": oblique, "dim": dim, "blur": blur, "contrast": contrast, "temporal": temporal, "track": track}


def reliability_score(features: dict[str, object] | pd.Series) -> float:
    parts = reliability_components(features)
    return float(sum(RISK_WEIGHTS[k] * parts[k] for k in RISK_WEIGHTS))


def _source(latent: dict[str, float | bool], available: bool) -> str | None:
    if not available:
        return None
    if float(latent["edge"]) > 0.68:
        return "partial_edge"
    if float(latent["blur"]) > 0.55 or float(latent["dim"]) > 0.55 or float(latent["contrast"]) > 0.55 or float(latent["oblique"]) > 0.55:
        return "phase9_center_regeometry"
    return "known_aruco_refined"


def _simulate_row(split: str, seed: int, family: int, domain: str, frame: int, n: int) -> dict[str, object]:
    seq_seed = seed + family * 100003 + sum(ord(c) for c in domain) * 97 + frame * 997
    rng = np.random.default_rng(seq_seed)
    truth_x, truth_z = _trajectory(family, frame, n)
    latent = _latent_context(domain, family, frame, n)
    features = _observed_features(latent, rng)
    score = reliability_score(features)
    parts = reliability_components(features)
    multi = max(0, len(_factors(domain)) - 1)
    availability_logit = 4.9 - 2.2 * float(latent["edge"]) - 1.2 * float(latent["dim"]) - 1.2 * float(latent["blur"]) - 1.2 * float(latent["contrast"]) - 1.0 * float(latent["scale"]) - 1.0 * float(latent["oblique"]) - 2.6 * float(latent["temporal"]) - 0.45 * multi
    p_available = 1.0 / (1.0 + math.exp(-availability_logit))
    if bool(latent["dropout_event"]):
        p_available *= 0.08
    available = bool(rng.random() < p_available)
    interaction = multi * (0.012 + 0.018 * score)
    lat_sigma = 0.0048 + 0.011 * parts["edge"] + 0.008 * parts["scale"] + 0.007 * parts["oblique"] + 0.007 * parts["dim"] + 0.008 * parts["blur"] + 0.007 * parts["contrast"] + 0.010 * parts["temporal"] + interaction
    alt_sigma = 0.018 + 0.026 * parts["edge"] + 0.021 * parts["scale"] + 0.021 * parts["oblique"] + 0.022 * parts["dim"] + 0.024 * parts["blur"] + 0.020 * parts["contrast"] + 0.022 * parts["temporal"] + 2.2 * interaction
    tail_prob = _clip01(0.006 + 0.09 * score**2 + 0.055 * multi)
    tail_scale = 1.0
    if rng.random() < tail_prob:
        tail_scale = 2.8 + 2.4 * rng.random()
    bias_sign = -1.0 if (family + frame) % 2 else 1.0
    lat_bias = bias_sign * multi * 0.0035 * (0.4 + score)
    alt_bias = bias_sign * multi * 0.0090 * (0.4 + score)
    if available:
        lat_err = float(rng.normal(lat_bias, lat_sigma * tail_scale))
        alt_err = float(rng.normal(alt_bias, alt_sigma * tail_scale))
        estimate_x, estimate_z = truth_x + lat_err, truth_z + alt_err
        lateral_abs_error, altitude_abs_error = abs(lat_err), abs(alt_err)
    else:
        estimate_x = estimate_z = lateral_abs_error = altitude_abs_error = np.nan
    return {"split": split, "seed": seed, "sequence_id": f"{split}-f{family:02d}-{domain}", "family": family, "domain": domain, "domain_factor_count": len(_factors(domain)), "frame_index": frame, "truth_visible": True, "candidate_available": available, "candidate_source": _source(latent, available), "truth_lateral_x_m": truth_x, "truth_altitude_m": truth_z, "estimate_lateral_x_m": estimate_x, "estimate_altitude_m": estimate_z, "lateral_abs_error_m": lateral_abs_error, "altitude_abs_error_m": altitude_abs_error, **features, "risk_score": score}


def generate_split(name: str, seed: int, families: tuple[int, ...], domains: tuple[str, ...], frames: int = FRAMES_PER_SEQUENCE) -> pd.DataFrame:
    return pd.DataFrame([_simulate_row(name, seed, family, domain, frame, frames) for domain in domains for family in families for frame in range(frames)])


def add_temporal_bridge(df: pd.DataFrame, max_gap: int = MAX_BRIDGE_GAP) -> pd.DataFrame:
    out = df.copy()
    out["p1_available"] = out["candidate_available"].astype(bool)
    out["p1_estimate_lateral_x_m"] = out["estimate_lateral_x_m"]
    out["p1_estimate_altitude_m"] = out["estimate_altitude_m"]
    out["p1_source"] = out["candidate_source"].fillna("")
    out["bridge_horizon"] = 0
    for _, indices in out.groupby("sequence_id").groups.items():
        ordered = sorted(indices, key=lambda i: int(out.loc[i, "frame_index"]))
        history: list[tuple[int, float, float]] = []
        gap = 0
        for i in ordered:
            frame = int(out.loc[i, "frame_index"])
            if bool(out.loc[i, "candidate_available"]):
                history.append((frame, float(out.loc[i, "estimate_lateral_x_m"]), float(out.loc[i, "estimate_altitude_m"])))
                history = history[-2:]
                gap = 0
                continue
            gap += 1
            if gap > max_gap or not history:
                continue
            if len(history) >= 2:
                f1, x1, z1 = history[-2]
                f2, x2, z2 = history[-1]
                dt = max(1, f2 - f1)
                step = frame - f2
                pred_x = x2 + ((x2 - x1) / dt) * step
                pred_z = z2 + ((z2 - z1) / dt) * step
            else:
                _, pred_x, pred_z = history[-1]
            out.loc[i, "p1_available"] = True
            out.loc[i, "p1_estimate_lateral_x_m"] = pred_x
            out.loc[i, "p1_estimate_altitude_m"] = pred_z
            out.loc[i, "p1_source"] = "temporal_bridge"
            out.loc[i, "bridge_horizon"] = gap
    out["p1_lateral_abs_error_m"] = np.abs(out["p1_estimate_lateral_x_m"] - out["truth_lateral_x_m"])
    out["p1_altitude_abs_error_m"] = np.abs(out["p1_estimate_altitude_m"] - out["truth_altitude_m"])
    return out


def add_reliability_state(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    names = ("edge", "scale", "oblique", "dim", "blur", "contrast", "temporal", "track")
    values = np.asarray([[reliability_components(row)[k] for k in names] for _, row in out.iterrows()], dtype=float)
    for j, name in enumerate(names):
        out[f"risk_{name}"] = values[:, j]
    out["coactivation_count"] = (values[:, :7] > COACTIVATION_THRESHOLD).sum(axis=1).astype(int)
    out["severity"] = out["risk_score"].to_numpy(float) + SEVERITY_COACTIVATION_WEIGHT * (out["coactivation_count"].to_numpy(float) / 7.0) + SEVERITY_BRIDGE_WEIGHT * out["bridge_horizon"].to_numpy(float)
    out["accepted"] = out["p1_available"].astype(bool) & (out["severity"] <= ACCEPTANCE_THRESHOLD)
    return out


SCALE_FEATURES = ("risk_edge", "risk_scale", "risk_oblique", "risk_dim", "risk_blur", "risk_contrast", "risk_temporal", "risk_track")


def _scale_basis(df: pd.DataFrame) -> np.ndarray:
    risk = df["risk_score"].to_numpy(float)
    bridge = df["bridge_horizon"].to_numpy(float)
    source = df["p1_source"].fillna("").astype(str)
    return np.column_stack([np.ones(len(df)), df[list(SCALE_FEATURES)].to_numpy(float), risk, risk * risk, bridge, bridge * risk, (source == "partial_edge").to_numpy(float), (source == "phase9_center_regeometry").to_numpy(float), (source == "known_aruco_refined").to_numpy(float), (source == "temporal_bridge").to_numpy(float)])


def _ridge_fit(x: np.ndarray, y: np.ndarray, lam: float = RIDGE_LAMBDA) -> np.ndarray:
    penalty = np.eye(x.shape[1], dtype=float)
    penalty[0, 0] = 0.0
    return np.linalg.solve(x.T @ x + lam * penalty, x.T @ y)


def fit_scale_models(fit: pd.DataFrame) -> dict[str, list[float]]:
    d = fit[fit["p1_available"]].copy()
    x = _scale_basis(d)
    out = {}
    for axis in ("lateral", "altitude"):
        y = np.log(d[f"p1_{axis}_abs_error_m"].to_numpy(float) + 1e-4)
        out[axis] = _ridge_fit(x, y).tolist()
    return out


def _predicted_scale(df: pd.DataFrame, beta: list[float]) -> np.ndarray:
    return np.exp(_scale_basis(df) @ np.asarray(beta, dtype=float))


def _multiplier(df: pd.DataFrame) -> np.ndarray:
    return 1.0 + MULTIPLIER_COACTIVATION * df["coactivation_count"].to_numpy(float) + MULTIPLIER_RISK * df["risk_score"].to_numpy(float) + MULTIPLIER_BRIDGE * df["bridge_horizon"].to_numpy(float)


def conformal_radius(values: np.ndarray | pd.Series, q: float) -> float:
    arr = np.sort(np.asarray(values, dtype=float)[np.isfinite(values)])
    if arr.size == 0:
        return float("nan")
    k = int(math.ceil((arr.size + 1) * q))
    return float(arr[min(arr.size - 1, max(0, k - 1))])


def calibrate(calibration: pd.DataFrame, models: dict[str, list[float]]) -> dict[str, object]:
    d = calibration[calibration["accepted"]].copy()
    mult = _multiplier(d)
    out: dict[str, object] = {"schema": "aegisland.phase11.p1.calibration.v1", "targets": list(TARGETS), "accepted_rows": int(len(d)), "acceptance_threshold": ACCEPTANCE_THRESHOLD, "coactivation_threshold": COACTIVATION_THRESHOLD, "radii": {}, "scale_models": models}
    for axis in ("lateral", "altitude"):
        pred = _predicted_scale(d, models[axis])
        normalized = d[f"p1_{axis}_abs_error_m"].to_numpy(float) / (pred * mult)
        out["radii"][axis] = {f"{q:.2f}": conformal_radius(normalized, q) for q in TARGETS}
    return out


def _halfwidths(df: pd.DataFrame, calibration: dict[str, object], axis: str, q: float) -> np.ndarray:
    return float(calibration["radii"][axis][f"{q:.2f}"]) * _predicted_scale(df, calibration["scale_models"][axis]) * _multiplier(df)


def _auc(labels: np.ndarray, scores: np.ndarray) -> float:
    labels = np.asarray(labels, dtype=int)
    scores = np.asarray(scores, dtype=float)
    pos, neg = scores[labels == 1], scores[labels == 0]
    if pos.size == 0 or neg.size == 0:
        return float("nan")
    wins = sum(float(np.sum(p > neg)) + 0.5 * float(np.sum(p == neg)) for p in pos)
    return float(wins / (pos.size * neg.size))


def trajectory_shift_auc(calibration: pd.DataFrame, evaluated: pd.DataFrame) -> float:
    a = calibration.groupby("sequence_id", as_index=False)["severity"].mean(); a["label"] = 0
    b = evaluated.groupby("sequence_id", as_index=False)["severity"].mean(); b["label"] = 1
    z = pd.concat([a, b], ignore_index=True)
    return _auc(z["label"].to_numpy(int), z["severity"].to_numpy(float))


def summarize(evaluated: pd.DataFrame, calibration_df: pd.DataFrame, calibration: dict[str, object], evidence_role: str, seed: int) -> dict[str, object]:
    accepted = evaluated["accepted"].to_numpy(bool)
    available = evaluated["p1_available"].to_numpy(bool)
    coverage_curve, interval_stats, error_stats = {}, {}, {}
    for axis in ("lateral", "altitude"):
        col = f"p1_{axis}_abs_error_m"
        d = evaluated.loc[accepted, col].to_numpy(float)
        baseline = evaluated.loc[available, col].to_numpy(float)
        p95 = float(np.percentile(d, 95)) if d.size else float("nan")
        base_p95 = float(np.percentile(baseline, 95)) if baseline.size else float("nan")
        coverage_curve[axis] = {f"{q:.2f}": float(np.mean(d <= _halfwidths(evaluated.loc[accepted], calibration, axis, q))) if d.size else float("nan") for q in TARGETS}
        widths95 = _halfwidths(evaluated.loc[accepted], calibration, axis, 0.95)
        interval_stats[axis] = {"median_halfwidth_95": float(np.median(widths95)) if widths95.size else float("nan"), "p95_halfwidth_95": float(np.percentile(widths95, 95)) if widths95.size else float("nan"), "median_halfwidth_over_accepted_p95_error": float(np.median(widths95) / p95) if p95 > 0 else float("nan")}
        error_stats[f"{axis}_p95_all_available"] = base_p95
        error_stats[f"{axis}_p95_accepted"] = p95
        error_stats[f"{axis}_p95_improvement"] = float((base_p95 - p95) / base_p95) if base_p95 > 0 else float("nan")
        error_stats[f"{axis}_mae_accepted"] = float(np.mean(d)) if d.size else float("nan")
    availability = float(np.mean(accepted))
    h1 = {"lateral_95_coverage": coverage_curve["lateral"]["0.95"], "altitude_95_coverage": coverage_curve["altitude"]["0.95"]}
    h1["pass"] = bool(0.90 <= h1["lateral_95_coverage"] <= 0.98 and 0.90 <= h1["altitude_95_coverage"] <= 0.98)
    h2 = {"lateral_efficiency_ratio": interval_stats["lateral"]["median_halfwidth_over_accepted_p95_error"], "altitude_efficiency_ratio": interval_stats["altitude"]["median_halfwidth_over_accepted_p95_error"]}
    h2["pass"] = bool(h2["lateral_efficiency_ratio"] <= 1.50 and h2["altitude_efficiency_ratio"] <= 1.50)
    h3 = {"lateral_p95_improvement": error_stats["lateral_p95_improvement"], "altitude_p95_improvement": error_stats["altitude_p95_improvement"], "usable_availability": availability}
    h3["pass"] = bool(h3["lateral_p95_improvement"] >= 0.25 and h3["altitude_p95_improvement"] >= 0.25 and availability >= 0.70)
    auc = trajectory_shift_auc(calibration_df, evaluated)
    h4 = {"trajectory_level_auroc": auc, "pass": bool(auc >= 0.85)}
    mace = float(np.mean([abs(coverage_curve[axis][f"{q:.2f}"] - q) for axis in ("lateral", "altitude") for q in TARGETS]))
    return {"schema": "aegisland.phase11.p1.result.v1", "evidence_role": evidence_role, "simulation_only": True, "safety_acceptance": False, "controller_tuning_allowed": False, "evaluated_seed_seen_after_run": seed, "all_primary_gates_pass": bool(h1["pass"] and h2["pass"] and h3["pass"] and h4["pass"]), "gates": {"h1_selective_coverage_transfer": h1, "h2_interval_efficiency": h2, "h3_useful_selective_reliability": h3, "h4_shift_discrimination": h4}, "coverage_curve": coverage_curve, "mean_absolute_coverage_error": mace, "interval_stats": interval_stats, "error_stats": error_stats, "accepted_rows": int(np.sum(accepted)), "total_rows": int(len(evaluated)), "preselection_available_rows": int(np.sum(available))}


def _hash_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def write_outputs(out: Path, stage: str, git_sha: str) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    fit = add_reliability_state(add_temporal_bridge(generate_split("fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS)))
    cal = add_reliability_state(add_temporal_bridge(generate_split("calibration", CALIBRATION_SEED, CALIBRATION_FAMILIES, FIT_DOMAINS)))
    if stage == "development":
        eval_seed, eval_name, eval_families, eval_domains, role = DEVELOPMENT_SEED, "development", DEVELOPMENT_FAMILIES, DEVELOPMENT_DOMAINS, "phase11_p1_seen_exploratory_development"
    elif stage == "validation":
        eval_seed, eval_name, eval_families, eval_domains, role = VALIDATION_SEED, "validation", VALIDATION_FAMILIES, VALIDATION_DOMAINS, "phase11_p1_frozen_candidate_validation"
    else:
        raise ValueError(stage)
    evaluated = add_reliability_state(add_temporal_bridge(generate_split(eval_name, eval_seed, eval_families, eval_domains)))
    models = fit_scale_models(fit)
    calibration = calibrate(cal, models)
    result = summarize(evaluated, cal, calibration, role, eval_seed)
    result["benchmark_config"] = {"stage": stage, "fit_seed": FIT_SEED, "calibration_seed": CALIBRATION_SEED, "evaluated_seed": eval_seed, "frames_per_sequence": FRAMES_PER_SEQUENCE, "fit_domains": list(FIT_DOMAINS), "evaluated_domains": list(eval_domains), "git_sha": git_sha, "candidate_constants": {"max_bridge_gap": MAX_BRIDGE_GAP, "coactivation_threshold": COACTIVATION_THRESHOLD, "severity_coactivation_weight": SEVERITY_COACTIVATION_WEIGHT, "severity_bridge_weight": SEVERITY_BRIDGE_WEIGHT, "acceptance_threshold": ACCEPTANCE_THRESHOLD, "ridge_lambda": RIDGE_LAMBDA, "multiplier_coactivation": MULTIPLIER_COACTIVATION, "multiplier_risk": MULTIPLIER_RISK, "multiplier_bridge": MULTIPLIER_BRIDGE}}
    fit.to_csv(out / "fit_frames.csv", index=False)
    cal.to_csv(out / "calibration_frames.csv", index=False)
    evaluated.to_csv(out / f"{eval_name}_frames.csv", index=False)
    (out / "calibration.json").write_text(json.dumps(calibration, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / f"{eval_name}_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    g = result["gates"]
    summary = [f"# Phase 11 P1 {eval_name} result", "", f"**Evidence role:** `{role}`", "", f"- Overall primary gates: {'PASS' if result['all_primary_gates_pass'] else 'MIXED / FAIL'}", f"- H1 95% coverage: lateral {g['h1_selective_coverage_transfer']['lateral_95_coverage']:.2%}, altitude {g['h1_selective_coverage_transfer']['altitude_95_coverage']:.2%}", f"- H2 efficiency: lateral {g['h2_interval_efficiency']['lateral_efficiency_ratio']:.3f}x, altitude {g['h2_interval_efficiency']['altitude_efficiency_ratio']:.3f}x", f"- H3 p95 improvement: lateral {g['h3_useful_selective_reliability']['lateral_p95_improvement']:.2%}, altitude {g['h3_useful_selective_reliability']['altitude_p95_improvement']:.2%}; availability {g['h3_useful_selective_reliability']['usable_availability']:.2%}", f"- H4 trajectory AUROC: {g['h4_shift_discrimination']['trajectory_level_auroc']:.4f}", f"- Coverage MACE across 50/68/80/90/95: {result['mean_absolute_coverage_error']:.4f}", "", "This remains a simulation-only synthetic reliability-layer benchmark."]
    (out / f"{eval_name}_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    names = ["fit_frames.csv", "calibration_frames.csv", f"{eval_name}_frames.csv", "calibration.json", f"{eval_name}_result.json", f"{eval_name}_summary.md"]
    manifest = {"schema": "aegisland.phase11.p1.manifest.v1", "stage": stage, "git_sha": git_sha, "artifacts": {name: _hash_file(out / name) for name in names}}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("development", "validation"), default="development")
    parser.add_argument("--out", type=Path, default=Path("results/phase11_p1"))
    parser.add_argument("--git-sha", default=None)
    parser.add_argument("--acknowledge-validation-exposure", action="store_true", help="Required for --stage validation; validation seed becomes permanently seen.")
    args = parser.parse_args()
    if args.stage == "validation" and not args.acknowledge_validation_exposure:
        raise SystemExit("validation blocked: pass --acknowledge-validation-exposure after candidate freeze")
    result = write_outputs(args.out, args.stage, args.git_sha or _git_sha())
    print(json.dumps(result["gates"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
