from __future__ import annotations

import argparse
import json
import math
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd

FIT_SEED = 11011
CAL_SEED = 22022
CHALLENGE_SEED = 33033
FRAMES_PER_SEQUENCE = 60
TARGETS = (0.50, 0.68, 0.80, 0.90, 0.95)

FIT_DOMAINS = (
    "nominal",
    "edge",
    "small_scale",
    "oblique",
    "dim",
    "blur_noise",
    "temporal_dropout",
    "low_contrast",
)
CHALLENGE_DOMAINS = (
    "edge+dim",
    "edge+blur_noise",
    "small_scale+oblique",
    "dim+blur_noise",
    "edge+small_scale+oblique",
    "small_scale+blur_noise+temporal_dropout",
    "oblique+dim+temporal_dropout",
    "edge+oblique+dim+blur_noise",
)
SPLITS = {
    "fit": (FIT_SEED, tuple(range(0, 6)), FIT_DOMAINS),
    "calibration": (CAL_SEED, tuple(range(6, 9)), FIT_DOMAINS),
    "challenge": (CHALLENGE_SEED, tuple(range(9, 12)), CHALLENGE_DOMAINS),
}

RISK_WEIGHTS = {
    "edge_visibility": 0.25,
    "small_scale": 0.15,
    "obliquity": 0.15,
    "appearance": 0.20,
    "temporal": 0.15,
    "track": 0.10,
}

FROZEN_PHASE10R_CALIBRATION = {
    "fallback": {
        "lateral": {"0.50": 0.005082803480209355, "0.68": 0.007634858053297222, "0.80": 0.011017193971801342, "0.90": 0.015733817313478227, "0.95": 0.020801880640489046},
        "altitude": {"0.50": 0.021120020906166825, "0.68": 0.03070213070112393, "0.80": 0.040998159901058706, "0.90": 0.05043075206756109, "0.95": 0.0573995023620415},
    },
    "known_aruco_refined": {
        "lateral": {"0.50": 0.004463256800127768, "0.68": 0.006293466167798856, "0.80": 0.008664743623924664, "0.90": 0.012269796331351057, "0.95": 0.014782393624177215},
        "altitude": {"0.50": 0.019821419412917596, "0.68": 0.028840844025188606, "0.80": 0.037452461082823074, "0.90": 0.04667406380543371, "0.95": 0.051750371024914976},
    },
    "partial_edge": {
        "lateral": {"0.50": 0.010905028800905825, "0.68": 0.017231041324218044, "0.80": 0.020670143376924743, "0.90": 0.025015126507574648, "0.95": 0.029143235592355987},
        "altitude": {"0.50": 0.029638730447637318, "0.68": 0.04188314597198728, "0.80": 0.052827668551611584, "0.90": 0.061709202080701964, "0.95": 0.0821502980046942},
    },
    "phase9_center_regeometry": {
        "lateral": {"0.50": 0.006282358695612, "0.68": 0.009433870589548254, "0.80": 0.012429102775271983, "0.90": 0.01844245693779134, "0.95": 0.023556679732330776},
        "altitude": {"0.50": 0.02280830504628195, "0.68": 0.03393167210084691, "0.80": 0.04992031134313857, "0.90": 0.060363041001812334, "0.95": 0.07472846750114792},
    },
}


def _clip01(x: float) -> float:
    return float(min(1.0, max(0.0, x)))


def _factors(domain: str) -> set[str]:
    return set(domain.split("+")) if domain != "nominal" else set()


def _trajectory(family: int, frame: int, n: int) -> tuple[float, float]:
    t = frame / max(1, n - 1)
    phase = (family % 6) * 0.43
    freq = 1.0 + (family % 3) * 0.35
    lateral = 0.42 * math.sin(2 * math.pi * freq * t + phase)
    lateral += 0.10 * math.sin(5 * math.pi * t + 0.2 * family)
    altitude = 2.15 + 0.45 * math.sin(math.pi * t + phase * 0.3)
    altitude += 0.06 * ((family % 5) - 2)
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
    low_contrast = 0.68 if "low_contrast" in factors else 0.0
    dropout_event = "temporal_dropout" in factors and frame % 15 in (7, 8)
    reacquisition = "temporal_dropout" in factors and frame % 15 == 9
    temporal = 0.12 + (0.72 if dropout_event else 0.32 if reacquisition else 0.0)
    appearance = max(dim, blur, low_contrast)
    track = 0.10 + 0.48 * temporal + 0.18 * edge
    return {
        "edge": _clip01(edge),
        "scale": _clip01(scale),
        "oblique": _clip01(oblique),
        "appearance": _clip01(appearance),
        "temporal": _clip01(temporal),
        "track": _clip01(track),
        "dropout_event": bool(dropout_event),
        "reacquisition": bool(reacquisition),
    }


def _observed_features(latent: dict[str, float | bool], rng: np.random.Generator) -> dict[str, float | bool]:
    noise = lambda s: float(rng.normal(0.0, s))
    edge = _clip01(float(latent["edge"]) + noise(0.035))
    scale_risk = _clip01(float(latent["scale"]) + noise(0.035))
    oblique = _clip01(float(latent["oblique"]) + noise(0.035))
    appearance = _clip01(float(latent["appearance"]) + noise(0.045))
    temporal = _clip01(float(latent["temporal"]) + noise(0.035))
    track = _clip01(float(latent["track"]) + noise(0.035))

    edge_margin_ratio = max(-0.25, 1.12 - 1.42 * edge + noise(0.025))
    visible_fraction_proxy = _clip01(1.02 - 0.74 * edge + noise(0.025))
    projected_scale_px = max(8.0, 84.0 - 62.0 * scale_risk + noise(1.8))
    obliquity_proxy = _clip01(oblique + noise(0.015))
    brightness_mean = float(np.clip(205.0 - 118.0 * appearance + noise(5.0), 25.0, 235.0))
    contrast_std = float(np.clip(52.0 - 30.0 * appearance + noise(2.5), 6.0, 65.0))
    laplacian_var = float(np.clip(180.0 - 145.0 * appearance + noise(8.0), 8.0, 220.0))
    temporal_innovation = _clip01(temporal + noise(0.025))
    track_stability = _clip01(1.0 - track + noise(0.025))
    return {
        "edge_margin_ratio": float(edge_margin_ratio),
        "visible_fraction_proxy": float(visible_fraction_proxy),
        "projected_scale_px": float(projected_scale_px),
        "obliquity_proxy": float(obliquity_proxy),
        "brightness_mean": brightness_mean,
        "contrast_std": contrast_std,
        "laplacian_var": laplacian_var,
        "temporal_innovation": float(temporal_innovation),
        "track_stability": float(track_stability),
        "reacquisition": bool(latent["reacquisition"]),
    }


def reliability_components(features: dict[str, float | bool]) -> dict[str, float]:
    edge_margin = float(features["edge_margin_ratio"])
    visible = float(features["visible_fraction_proxy"])
    scale_px = float(features["projected_scale_px"])
    oblique = float(features["obliquity_proxy"])
    brightness = float(features["brightness_mean"])
    contrast = float(features["contrast_std"])
    lap_var = float(features["laplacian_var"])
    innovation = float(features["temporal_innovation"])
    stability = float(features["track_stability"])
    reacq = bool(features["reacquisition"])

    edge_risk = max(_clip01((0.85 - edge_margin) / 1.10), _clip01((0.72 - visible) / 0.72))
    scale_risk = _clip01((52.0 - scale_px) / 44.0)
    obliquity_risk = _clip01(oblique)
    brightness_risk = _clip01(abs(brightness - 185.0) / 145.0)
    contrast_risk = _clip01((38.0 - contrast) / 32.0)
    blur_risk = _clip01((125.0 - lap_var) / 117.0)
    appearance_risk = max(brightness_risk, contrast_risk, blur_risk)
    temporal_risk = _clip01(innovation)
    track_risk = max(_clip01(1.0 - stability), 0.88 if reacq else 0.0)
    return {
        "edge_visibility": edge_risk,
        "small_scale": scale_risk,
        "obliquity": obliquity_risk,
        "appearance": appearance_risk,
        "temporal": temporal_risk,
        "track": track_risk,
    }


def reliability_score(features: dict[str, float | bool]) -> float:
    parts = reliability_components(features)
    return float(sum(RISK_WEIGHTS[k] * parts[k] for k in RISK_WEIGHTS))


def _risk_stratum(score: float) -> str:
    if score < 0.30:
        return "low"
    if score < 0.60:
        return "medium"
    return "high"


def _source(latent: dict[str, float | bool], available: bool) -> str | None:
    if not available:
        return None
    if float(latent["edge"]) > 0.68:
        return "partial_edge"
    if float(latent["appearance"]) > 0.55 or float(latent["oblique"]) > 0.55:
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
    availability_logit = (
        4.9
        - 2.2 * float(latent["edge"])
        - 1.2 * float(latent["appearance"])
        - 1.0 * float(latent["scale"])
        - 1.0 * float(latent["oblique"])
        - 2.6 * float(latent["temporal"])
        - 0.45 * multi
    )
    p_available = 1.0 / (1.0 + math.exp(-availability_logit))
    if bool(latent["dropout_event"]):
        p_available *= 0.08
    available = bool(rng.random() < p_available)

    interaction = multi * (0.012 + 0.018 * score)
    lat_sigma = 0.0048 + 0.011 * parts["edge_visibility"] + 0.008 * parts["small_scale"] + 0.007 * parts["obliquity"]
    lat_sigma += 0.010 * parts["appearance"] + 0.010 * parts["temporal"] + interaction
    alt_sigma = 0.018 + 0.026 * parts["edge_visibility"] + 0.021 * parts["small_scale"] + 0.021 * parts["obliquity"]
    alt_sigma += 0.030 * parts["appearance"] + 0.022 * parts["temporal"] + 2.2 * interaction

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
        est_x = truth_x + lat_err
        est_z = truth_z + alt_err
        lateral_abs_error = abs(lat_err)
        altitude_abs_error = abs(alt_err)
    else:
        est_x = np.nan
        est_z = np.nan
        lateral_abs_error = np.nan
        altitude_abs_error = np.nan

    source = _source(latent, available)
    return {
        "split": split,
        "seed": seed,
        "sequence_id": f"{split}-f{family:02d}-{domain}",
        "family": family,
        "domain": domain,
        "domain_factor_count": len(_factors(domain)),
        "frame_index": frame,
        "truth_visible": True,
        "candidate_available": available,
        "candidate_source": source,
        "truth_lateral_x_m": truth_x,
        "truth_altitude_m": truth_z,
        "estimate_lateral_x_m": est_x,
        "estimate_altitude_m": est_z,
        "lateral_abs_error_m": lateral_abs_error,
        "altitude_abs_error_m": altitude_abs_error,
        **features,
        "risk_score": score,
        "risk_stratum": _risk_stratum(score),
    }


def generate_split(name: str, seed: int, families: tuple[int, ...], domains: tuple[str, ...], frames: int = FRAMES_PER_SEQUENCE) -> pd.DataFrame:
    rows = [
        _simulate_row(name, seed, family, domain, frame, frames)
        for domain in domains
        for family in families
        for frame in range(frames)
    ]
    return pd.DataFrame(rows)


def conformal_radius(values: pd.Series | np.ndarray, q: float) -> float:
    arr = np.asarray(values, dtype=float)
    arr = np.sort(arr[np.isfinite(arr)])
    if arr.size == 0:
        return float("nan")
    k = int(math.ceil((arr.size + 1) * q))
    return float(arr[min(arr.size - 1, max(0, k - 1))])


def build_calibration(cal: pd.DataFrame) -> dict[str, object]:
    avail = cal[cal["truth_visible"] & cal["candidate_available"]].copy()
    global_radii: dict[str, dict[str, float]] = {}
    context_radii: dict[str, dict[str, dict[str, float]]] = {}
    for axis in ("lateral", "altitude"):
        col = f"{axis}_abs_error_m"
        global_radii[axis] = {f"{q:.2f}": conformal_radius(avail[col], q) for q in TARGETS}
        context_radii[axis] = {}
        for stratum in ("low", "medium", "high"):
            g = avail[avail["risk_stratum"] == stratum]
            use = g if len(g) >= 40 else avail
            context_radii[axis][stratum] = {f"{q:.2f}": conformal_radius(use[col], q) for q in TARGETS}
    threshold = float(np.quantile(cal["risk_score"].to_numpy(float), 0.90))
    return {
        "schema": "aegisland.phase11.p0.calibration.v1",
        "targets": list(TARGETS),
        "abstention_risk_threshold_q90": threshold,
        "global": global_radii,
        "context": context_radii,
        "context_min_count": 40,
        "risk_strata": {"low": "<0.30", "medium": "0.30<=x<0.60", "high": ">=0.60"},
    }


def _frozen_radius(source: str | None, axis: str, q: float) -> float:
    src = source if source in FROZEN_PHASE10R_CALIBRATION else "fallback"
    return float(FROZEN_PHASE10R_CALIBRATION[src][axis][f"{q:.2f}"])


def _method_radius(row: pd.Series, calibration: dict[str, object], method: str, axis: str, q: float) -> float:
    key = f"{q:.2f}"
    if method == "frozen_reference":
        return _frozen_radius(row["candidate_source"], axis, q)
    if method == "global_conformal":
        return float(calibration["global"][axis][key])
    if method in ("context_conformal", "shift_aware_abstention"):
        return float(calibration["context"][axis][str(row["risk_stratum"])][key])
    raise ValueError(method)


def _coverage_table(df: pd.DataFrame, calibration: dict[str, object], method: str, accepted: pd.Series) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for axis in ("lateral", "altitude"):
        col = f"{axis}_abs_error_m"
        axis_out = {}
        for q in TARGETS:
            mask = accepted & df["candidate_available"] & df["truth_visible"] & df[col].notna()
            d = df[mask]
            if d.empty:
                axis_out[f"{q:.2f}"] = float("nan")
                continue
            hits = []
            for _, row in d.iterrows():
                hits.append(float(row[col]) <= _method_radius(row, calibration, method, axis, q))
            axis_out[f"{q:.2f}"] = float(np.mean(hits))
        out[axis] = axis_out
    return out


def _width_stats(df: pd.DataFrame, calibration: dict[str, object], method: str, accepted: pd.Series) -> dict[str, dict[str, float]]:
    out = {}
    mask = accepted & df["candidate_available"] & df["truth_visible"]
    d = df[mask]
    for axis in ("lateral", "altitude"):
        widths = np.array([2.0 * _method_radius(row, calibration, method, axis, 0.95) for _, row in d.iterrows()], dtype=float)
        out[axis] = {
            "median": float(np.nanmedian(widths)) if widths.size else float("nan"),
            "p95": float(np.nanpercentile(widths, 95)) if widths.size else float("nan"),
        }
    return out


def _error_stats(df: pd.DataFrame, accepted: pd.Series) -> dict[str, float]:
    mask = accepted & df["candidate_available"] & df["truth_visible"]
    d = df[mask]
    out = {"availability": float(mask.mean())}
    for axis in ("lateral", "altitude"):
        arr = d[f"{axis}_abs_error_m"].dropna().to_numpy(float)
        out[f"{axis}_mae"] = float(arr.mean()) if arr.size else float("nan")
        out[f"{axis}_p95"] = float(np.percentile(arr, 95)) if arr.size else float("nan")
    return out


def _auc(labels: np.ndarray, scores: np.ndarray) -> float:
    labels = np.asarray(labels, dtype=int)
    scores = np.asarray(scores, dtype=float)
    pos = scores[labels == 1]
    neg = scores[labels == 0]
    if pos.size == 0 or neg.size == 0:
        return float("nan")
    wins = 0.0
    for p in pos:
        wins += float(np.sum(p > neg)) + 0.5 * float(np.sum(p == neg))
    return float(wins / (pos.size * neg.size))


def trajectory_shift_auc(cal: pd.DataFrame, challenge: pd.DataFrame) -> float:
    a = cal.groupby("sequence_id", as_index=False)["risk_score"].mean()
    a["label"] = 0
    b = challenge.groupby("sequence_id", as_index=False)["risk_score"].mean()
    b["label"] = 1
    z = pd.concat([a, b], ignore_index=True)
    return _auc(z["label"].to_numpy(int), z["risk_score"].to_numpy(float))


def summarize(cal: pd.DataFrame, challenge: pd.DataFrame, calibration: dict[str, object]) -> dict[str, object]:
    all_accept = pd.Series(True, index=challenge.index)
    shift_accept = challenge["risk_score"] <= float(calibration["abstention_risk_threshold_q90"])

    methods = {}
    for method, accept in (
        ("frozen_reference", all_accept),
        ("global_conformal", all_accept),
        ("context_conformal", all_accept),
        ("shift_aware_abstention", shift_accept),
    ):
        cov = _coverage_table(challenge, calibration, method, accept)
        widths = _width_stats(challenge, calibration, method, accept)
        errors = _error_stats(challenge, accept)
        mace = float(np.nanmean([
            abs(cov[axis][f"{q:.2f}"] - q)
            for axis in ("lateral", "altitude")
            for q in TARGETS
        ]))
        methods[method] = {
            "coverage": cov,
            "mean_absolute_coverage_error": mace,
            "widths_95": widths,
            "errors": errors,
        }

    context = methods["context_conformal"]
    global_ = methods["global_conformal"]
    selective = methods["shift_aware_abstention"]
    base_err = methods["global_conformal"]["errors"]

    h1_lat = context["coverage"]["lateral"]["0.95"]
    h1_alt = context["coverage"]["altitude"]["0.95"]
    h1 = {
        "lateral_95_coverage": h1_lat,
        "altitude_95_coverage": h1_alt,
        "pass": bool(0.90 <= h1_lat <= 0.98 and 0.90 <= h1_alt <= 0.98),
    }

    lat_ratio = context["widths_95"]["lateral"]["median"] / global_["widths_95"]["lateral"]["median"]
    alt_ratio = context["widths_95"]["altitude"]["median"] / global_["widths_95"]["altitude"]["median"]
    h2 = {
        "lateral_median_width_ratio_vs_global": float(lat_ratio),
        "altitude_median_width_ratio_vs_global": float(alt_ratio),
        "pass": bool(lat_ratio <= 1.35 and alt_ratio <= 1.35),
    }

    def improvement(b: float, x: float) -> float:
        return float((b - x) / b) if b > 0 else float("nan")

    lat_imp = improvement(base_err["lateral_p95"], selective["errors"]["lateral_p95"])
    alt_imp = improvement(base_err["altitude_p95"], selective["errors"]["altitude_p95"])
    h3 = {
        "lateral_p95_improvement": lat_imp,
        "altitude_p95_improvement": alt_imp,
        "usable_availability": selective["errors"]["availability"],
        "pass": bool(lat_imp >= 0.25 and alt_imp >= 0.25 and selective["errors"]["availability"] >= 0.70),
    }

    auc = trajectory_shift_auc(cal, challenge)
    h4 = {"trajectory_level_auroc": auc, "pass": bool(auc >= 0.80)}

    domain_stats = []
    for domain, g in challenge.groupby("domain"):
        accept = g["risk_score"] <= float(calibration["abstention_risk_threshold_q90"])
        stats = _error_stats(g, accept)
        domain_stats.append({"domain": domain, **stats})
    domain_stats.sort(key=lambda x: max(x["lateral_p95"], x["altitude_p95"]), reverse=True)

    return {
        "schema": "aegisland.phase11.p0.benchmark-result.v1",
        "evidence_role": "phase11_p0_non_authoritative_synthetic_development",
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "challenge_seed_seen_after_run": CHALLENGE_SEED,
        "all_primary_gates_pass": bool(h1["pass"] and h2["pass"] and h3["pass"] and h4["pass"]),
        "gates": {"h1_coverage_transfer": h1, "h2_useful_sharpness": h2, "h3_selective_reliability": h3, "h4_shift_discrimination": h4},
        "methods": methods,
        "worst_three_challenge_domains": domain_stats[:3],
    }


def _hash_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def write_outputs(out: Path, git_sha: str, frames: int = FRAMES_PER_SEQUENCE) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    split_frames = {}
    for name, (seed, families, domains) in SPLITS.items():
        df = generate_split(name, seed, families, domains, frames=frames)
        split_frames[name] = df
        df.to_csv(out / f"{name}_frames.csv", index=False)

    cal = build_calibration(split_frames["calibration"])
    (out / "calibration.json").write_text(json.dumps(cal, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = summarize(split_frames["calibration"], split_frames["challenge"], cal)
    result["benchmark_config"] = {
        "fit_seed": FIT_SEED,
        "calibration_seed": CAL_SEED,
        "challenge_seed": CHALLENGE_SEED,
        "frames_per_sequence": frames,
        "fit_domains": list(FIT_DOMAINS),
        "challenge_domains": list(CHALLENGE_DOMAINS),
        "git_sha": git_sha,
    }
    (out / "benchmark_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    g = result["gates"]
    summary = [
        "# Phase 11 P0 domain-shift reliability benchmark",
        "",
        "**Evidence role:** non-authoritative synthetic development benchmark.",
        "",
        f"- H1 coverage transfer: {'PASS' if g['h1_coverage_transfer']['pass'] else 'FAIL'} — lateral {g['h1_coverage_transfer']['lateral_95_coverage']:.1%}, altitude {g['h1_coverage_transfer']['altitude_95_coverage']:.1%}",
        f"- H2 useful sharpness: {'PASS' if g['h2_useful_sharpness']['pass'] else 'FAIL'} — width ratios {g['h2_useful_sharpness']['lateral_median_width_ratio_vs_global']:.3f} lateral / {g['h2_useful_sharpness']['altitude_median_width_ratio_vs_global']:.3f} altitude",
        f"- H3 selective reliability: {'PASS' if g['h3_selective_reliability']['pass'] else 'FAIL'} — p95 gains {g['h3_selective_reliability']['lateral_p95_improvement']:.1%} lateral / {g['h3_selective_reliability']['altitude_p95_improvement']:.1%} altitude; availability {g['h3_selective_reliability']['usable_availability']:.1%}",
        f"- H4 shift discrimination: {'PASS' if g['h4_shift_discrimination']['pass'] else 'FAIL'} — trajectory AUROC {g['h4_shift_discrimination']['trajectory_level_auroc']:.3f}",
        "",
        f"**Overall:** {'PASS' if result['all_primary_gates_pass'] else 'MIXED / FAILED'}",
        "",
        "This result does not establish physical-flight safety or new raw-camera accuracy.",
    ]
    (out / "benchmark_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    files = [
        "fit_frames.csv",
        "calibration_frames.csv",
        "challenge_frames.csv",
        "calibration.json",
        "benchmark_result.json",
        "benchmark_summary.md",
    ]
    manifest = {
        "schema": "aegisland.phase11.p0.manifest.v1",
        "git_sha": git_sha,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "files": {name: {"sha256": _hash_file(out / name), "bytes": (out / name).stat().st_size} for name in files},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run the preregistered Phase 11 P0 domain-shift reliability benchmark.")
    p.add_argument("--out", type=Path, default=Path("results/phase11_development"))
    p.add_argument("--git-sha", default="unknown")
    p.add_argument("--frames", type=int, default=FRAMES_PER_SEQUENCE)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if args.frames < 8:
        raise SystemExit("--frames must be >= 8")
    result = write_outputs(args.out, args.git_sha, frames=args.frames)
    print(json.dumps(result["gates"], indent=2, sort_keys=True))
    print(f"overall={'PASS' if result['all_primary_gates_pass'] else 'MIXED_OR_FAILED'}")


if __name__ == "__main__":
    main()
