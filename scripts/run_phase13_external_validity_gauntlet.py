from __future__ import annotations

import argparse
import json
import math
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scripts import run_phase12_adaptive_normalized_conformal as v1
    from scripts import run_phase12_adaptive_normalized_conformal_v3 as v3
except ModuleNotFoundError:
    import run_phase12_adaptive_normalized_conformal as v1
    import run_phase12_adaptive_normalized_conformal_v3 as v3

FROZEN_PHASE12_SCIENTIFIC_SHA = "8d0617a83d699cd14eae6194ce3a86a5c034dfbc"
FROZEN_PHASE12_CANDIDATE_SHA256 = "e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991"

DEV_SEED = 946946
TRANSFER_SEED = 957957
VALIDATION_SEED = 968968
FINAL_SEED = 979979

DOMAIN_PROFILES: tuple[dict[str, object], ...] = (
    {
        "name": "camera_scale_miscalibration",
        "category": "sensing",
        "base_domain": "small_scale+oblique+temporal_dropout",
        "lat_error_gain": 1.12,
        "alt_error_gain": 1.08,
        "innovation_gain": 1.08,
        "severity_delta": 0.04,
    },
    {
        "name": "lateral_sensor_bias",
        "category": "sensing",
        "base_domain": "edge+low_contrast+temporal_dropout",
        "lat_bias_m": 0.06,
        "innovation_gain": 1.12,
        "severity_delta": 0.05,
    },
    {
        "name": "correlated_measurement_noise",
        "category": "sensing",
        "base_domain": "blur_noise+low_contrast+temporal_dropout",
        "correlated_lat_amp_m": 0.055,
        "correlated_alt_amp_m": 0.11,
        "innovation_gain": 1.18,
        "severity_delta": 0.06,
    },
    {
        "name": "heavy_tail_measurement_noise",
        "category": "sensing",
        "base_domain": "edge+blur_noise+temporal_dropout",
        "noise_lat_sigma_m": 0.025,
        "noise_alt_sigma_m": 0.05,
        "tail_probability": 0.04,
        "tail_multiplier": 4.0,
        "innovation_gain": 1.22,
        "severity_delta": 0.07,
    },
    {
        "name": "fixed_latency_2f",
        "category": "timing",
        "base_domain": "small_scale+temporal_dropout",
        "lag_frames": 2,
        "innovation_gain": 1.18,
        "severity_delta": 0.06,
    },
    {
        "name": "jittered_latency_0_4f",
        "category": "timing",
        "base_domain": "oblique+dim+temporal_dropout",
        "jitter_lag_max": 4,
        "innovation_gain": 1.24,
        "severity_delta": 0.08,
    },
    {
        "name": "burst_staleness_5f",
        "category": "timing",
        "base_domain": "edge+small_scale+temporal_dropout",
        "burst_staleness_frames": 5,
        "innovation_gain": 1.28,
        "severity_delta": 0.09,
    },
    {
        "name": "lateral_wind_drift",
        "category": "dynamics",
        "base_domain": "edge+oblique+temporal_dropout",
        "lateral_drift_amp_m": 0.09,
        "innovation_gain": 1.16,
        "severity_delta": 0.06,
    },
    {
        "name": "vertical_gust",
        "category": "dynamics",
        "base_domain": "small_scale+dim+temporal_dropout",
        "vertical_gust_amp_m": 0.18,
        "innovation_gain": 1.10,
        "severity_delta": 0.06,
    },
    {
        "name": "dynamics_gain_mismatch",
        "category": "dynamics",
        "base_domain": "edge+small_scale+oblique+temporal_dropout",
        "lat_error_gain": 1.30,
        "alt_error_gain": 1.20,
        "innovation_gain": 1.20,
        "severity_delta": 0.08,
    },
    {
        "name": "oscillatory_drift",
        "category": "dynamics",
        "base_domain": "oblique+blur_noise+temporal_dropout",
        "osc_lat_amp_m": 0.07,
        "osc_alt_amp_m": 0.12,
        "innovation_gain": 1.15,
        "severity_delta": 0.06,
    },
    {
        "name": "reacquisition_shock",
        "category": "compound",
        "base_domain": "oblique+blur_noise+temporal_dropout",
        "reacquisition_lat_m": 0.10,
        "reacquisition_alt_m": 0.20,
        "innovation_gain": 1.35,
        "severity_delta": 0.10,
    },
    {
        "name": "latency_wind_calibration_compound",
        "category": "compound",
        "base_domain": "edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout",
        "lag_frames": 2,
        "lat_bias_m": 0.04,
        "alt_bias_m": 0.08,
        "lateral_drift_amp_m": 0.07,
        "noise_lat_sigma_m": 0.02,
        "noise_alt_sigma_m": 0.04,
        "innovation_gain": 1.35,
        "severity_delta": 0.12,
    },
)

STAGE_FAMILIES = {
    "dev": tuple(range(1201, 1225)),
    "transfer": tuple(range(1225, 1249)),
    "validation": tuple(range(1249, 1273)),
    "final": tuple(range(1273, 1297)),
}

STAGE_SEEDS = {
    "dev": DEV_SEED,
    "transfer": TRANSFER_SEED,
    "validation": VALIDATION_SEED,
    "final": FINAL_SEED,
}

EVIDENCE_ROLES = {
    "dev": "phase13_development_only_permanently_seen_after_run",
    "transfer": "phase13_transfer_seen_once_after_development_pass",
    "validation": "phase13_protected_seen_once_after_transfer_pass",
    "final": "phase13_final_seen_once_after_protected_pass",
}

DOMAIN_COVERAGE_FLOOR = 0.88
CATASTROPHIC_COVERAGE_FLOOR = 0.80
INNOVATION_ERROR_SPEARMAN_FLOOR = 0.20


def _strata(families: tuple[int, ...]) -> dict[str, tuple[int, ...]]:
    if len(families) != 24:
        raise RuntimeError("Phase 13 expects exactly 24 families per stage")
    names = ("bootstrap5", "gap3", "gap7", "gap12")
    return {name: families[i * 6 : (i + 1) * 6] for i, name in enumerate(names)}


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _stable_seed(*parts: object) -> int:
    token = "|".join(str(p) for p in parts).encode("utf-8")
    return int.from_bytes(sha256(token).digest()[:8], "little", signed=False)


def _validate_candidate(candidate_path: Path) -> dict[str, object]:
    if _sha256_file(candidate_path) != FROZEN_PHASE12_CANDIDATE_SHA256:
        raise RuntimeError("Phase 13 requires the exact frozen Phase 12 iteration-3 candidate")
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    if candidate.get("schema") != v3.CANDIDATE_SCHEMA:
        raise RuntimeError("Phase 13 predecessor candidate schema mismatch")
    if candidate.get("scientific_git_sha") != FROZEN_PHASE12_SCIENTIFIC_SHA:
        raise RuntimeError("Phase 13 predecessor scientific SHA mismatch")
    if candidate.get("simulation_only") is not True:
        raise RuntimeError("Phase 13 predecessor must remain simulation-only")
    if candidate.get("safety_acceptance") is not False:
        raise RuntimeError("Phase 13 predecessor safety boundary mismatch")
    if candidate.get("controller_tuning_allowed") is not False:
        raise RuntimeError("Phase 13 predecessor controller boundary mismatch")
    return candidate


def _profile(name: str) -> dict[str, object]:
    for profile in DOMAIN_PROFILES:
        if profile["name"] == name:
            return profile
    raise KeyError(name)


def _lagged(values: np.ndarray, lags: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    lags = np.asarray(lags, dtype=int)
    if len(values) != len(lags):
        raise RuntimeError("lag vector length mismatch")
    out = values.copy()
    finite = np.isfinite(values)
    for i, lag in enumerate(lags):
        j = max(0, i - max(0, int(lag)))
        while j > 0 and not finite[j]:
            j -= 1
        if finite[j]:
            out[i] = values[j]
    return out


def _sequence_phase(sequence_id: str, profile_name: str) -> float:
    return (_stable_seed("phase13-phase", sequence_id, profile_name) % 100000) / 100000.0 * 2.0 * math.pi


def apply_shift(df: pd.DataFrame, profile_name: str, seed: int) -> pd.DataFrame:
    profile = _profile(profile_name)
    required = {
        "sequence_id",
        "frame_index",
        "p14_available",
        "truth_visible",
        "truth_lateral_x_m",
        "truth_altitude_m",
        "p14_estimate_lateral_x_m",
        "p14_estimate_altitude_m",
        "p14_lateral_abs_error_m",
        "p14_altitude_abs_error_m",
        "p9_anchor_innovation_lateral_abs",
        "severity",
    }
    missing = required.difference(df.columns)
    if missing:
        raise RuntimeError(f"Phase 13 shift input missing columns: {sorted(missing)}")

    out = df.copy(deep=True)
    out["phase13_domain"] = profile_name
    out["phase13_domain_category"] = str(profile["category"])
    out["phase13_base_domain"] = str(profile["base_domain"])
    out["phase13_shift_applied"] = True
    out["sequence_id"] = out["sequence_id"].astype(str) + f"|phase13:{profile_name}"

    original_lat = out["p14_estimate_lateral_x_m"].to_numpy(float).copy()
    original_alt = out["p14_estimate_altitude_m"].to_numpy(float).copy()

    for _, idx in out.groupby("sequence_id", sort=False).groups.items():
        idx = list(idx)
        frames = out.loc[idx, "frame_index"].to_numpy(int)
        lat = out.loc[idx, "p14_estimate_lateral_x_m"].to_numpy(float)
        alt = out.loc[idx, "p14_estimate_altitude_m"].to_numpy(float)
        truth_lat = out.loc[idx, "truth_lateral_x_m"].to_numpy(float)
        truth_alt = out.loc[idx, "truth_altitude_m"].to_numpy(float)
        seq = str(out.loc[idx[0], "sequence_id"])
        phase = _sequence_phase(seq, profile_name)

        if "lag_frames" in profile:
            lag = np.full(len(idx), int(profile["lag_frames"]), dtype=int)
            lat = _lagged(lat, lag)
            alt = _lagged(alt, lag)

        if "jitter_lag_max" in profile:
            max_lag = int(profile["jitter_lag_max"])
            lag = np.asarray(
                [_stable_seed(seed, profile_name, seq, int(frame), "lag") % (max_lag + 1) for frame in frames],
                dtype=int,
            )
            lat = _lagged(lat, lag)
            alt = _lagged(alt, lag)

        if "burst_staleness_frames" in profile:
            width = int(profile["burst_staleness_frames"])
            lag = np.zeros(len(idx), dtype=int)
            for start in (18, 43):
                mask = (frames >= start) & (frames < start + width)
                lag[mask] = frames[mask] - start
            lat = _lagged(lat, lag)
            alt = _lagged(alt, lag)

        lat_gain = float(profile.get("lat_error_gain", 1.0))
        alt_gain = float(profile.get("alt_error_gain", 1.0))
        lat = truth_lat + lat_gain * (lat - truth_lat)
        alt = truth_alt + alt_gain * (alt - truth_alt)

        lat += float(profile.get("lat_bias_m", 0.0))
        alt += float(profile.get("alt_bias_m", 0.0))

        if "correlated_lat_amp_m" in profile or "correlated_alt_amp_m" in profile:
            wave = np.sin(2.0 * math.pi * frames / 20.0 + phase)
            lat += float(profile.get("correlated_lat_amp_m", 0.0)) * wave
            alt += float(profile.get("correlated_alt_amp_m", 0.0)) * wave

        if "lateral_drift_amp_m" in profile:
            t = frames / max(1.0, float(np.max(frames) or 1))
            lat += float(profile["lateral_drift_amp_m"]) * (2.0 * t - 1.0)

        if "vertical_gust_amp_m" in profile:
            gust = np.sin(2.0 * math.pi * frames / 17.0 + phase)
            alt += float(profile["vertical_gust_amp_m"]) * gust

        if "osc_lat_amp_m" in profile or "osc_alt_amp_m" in profile:
            wave = np.sin(2.0 * math.pi * frames / 11.0 + phase)
            lat += float(profile.get("osc_lat_amp_m", 0.0)) * wave
            alt += float(profile.get("osc_alt_amp_m", 0.0)) * np.cos(2.0 * math.pi * frames / 13.0 + phase)

        if "reacquisition_lat_m" in profile or "reacquisition_alt_m" in profile:
            for offset, decay in ((9, 1.0), (10, 0.5), (11, 0.25)):
                mask = frames % 15 == offset
                sign = np.where(((frames + _stable_seed(seq, profile_name)) % 2) == 0, 1.0, -1.0)
                lat[mask] += sign[mask] * float(profile.get("reacquisition_lat_m", 0.0)) * decay
                alt[mask] += sign[mask] * float(profile.get("reacquisition_alt_m", 0.0)) * decay

        noise_lat = float(profile.get("noise_lat_sigma_m", 0.0))
        noise_alt = float(profile.get("noise_alt_sigma_m", 0.0))
        tail_probability = float(profile.get("tail_probability", 0.0))
        tail_multiplier = float(profile.get("tail_multiplier", 1.0))
        if noise_lat > 0.0 or noise_alt > 0.0:
            for j, frame in enumerate(frames):
                rng = np.random.default_rng(_stable_seed(seed, profile_name, seq, int(frame), "noise"))
                scale = tail_multiplier if rng.random() < tail_probability else 1.0
                if noise_lat > 0.0:
                    lat[j] += float(rng.normal(0.0, noise_lat * scale))
                if noise_alt > 0.0:
                    alt[j] += float(rng.normal(0.0, noise_alt * scale))

        out.loc[idx, "p14_estimate_lateral_x_m"] = lat
        out.loc[idx, "p14_estimate_altitude_m"] = alt

    available = out["p14_available"].astype(bool) & out["truth_visible"].astype(bool)
    out.loc[~available, "p14_estimate_lateral_x_m"] = np.nan
    out.loc[~available, "p14_estimate_altitude_m"] = np.nan

    out["p14_lateral_abs_error_m"] = np.abs(
        out["p14_estimate_lateral_x_m"].to_numpy(float) - out["truth_lateral_x_m"].to_numpy(float)
    )
    out["p14_altitude_abs_error_m"] = np.abs(
        out["p14_estimate_altitude_m"].to_numpy(float) - out["truth_altitude_m"].to_numpy(float)
    )

    lat_delta = np.abs(out["p14_estimate_lateral_x_m"].to_numpy(float) - original_lat)
    alt_delta = np.abs(out["p14_estimate_altitude_m"].to_numpy(float) - original_alt)
    perturb = np.nan_to_num(lat_delta, nan=0.0) + 0.5 * np.nan_to_num(alt_delta, nan=0.0)
    response = np.clip(perturb / 0.30, 0.0, 1.0)

    severity = out["severity"].to_numpy(float)
    if not np.all(np.isfinite(severity)):
        raise RuntimeError("Phase 13 requires finite inference-visible severity")
    out["severity"] = np.clip(
        severity + float(profile.get("severity_delta", 0.0)) + 0.18 * response,
        0.0,
        1.0,
    )

    innovation = out["p9_anchor_innovation_lateral_abs"].to_numpy(float)
    if not np.all(np.isfinite(innovation)) or np.any(innovation < 0.0):
        raise RuntimeError("Phase 13 requires finite nonnegative anchor innovation")
    innovation_gain = float(profile.get("innovation_gain", 1.0))
    out["p9_anchor_innovation_lateral_abs"] = np.maximum(
        0.0,
        innovation * innovation_gain + 0.45 * np.nan_to_num(lat_delta, nan=0.0),
    )
    return out


def _stage_config(stage: str) -> tuple[int, tuple[int, ...], dict[str, tuple[int, ...]], dict[str, int]]:
    if stage not in STAGE_SEEDS:
        raise RuntimeError(f"unknown Phase 13 stage {stage}")
    families = STAGE_FAMILIES[stage]
    minimums = v1.FINAL_MINIMUMS if stage == "final" else v1.EVAL_MINIMUMS
    return STAGE_SEEDS[stage], families, _strata(families), minimums


def generate_gauntlet(stage: str, candidate: dict[str, object]) -> tuple[pd.DataFrame, pd.DataFrame]:
    seed, families, strata, _ = _stage_config(stage)
    controls: list[pd.DataFrame] = []
    shifted: list[pd.DataFrame] = []

    for profile in DOMAIN_PROFILES:
        name = str(profile["name"])
        base_domain = str(profile["base_domain"])
        base = v1._event(
            f"phase13_{stage}_{name}_base",
            seed,
            families,
            (base_domain,),
            strata,
            candidate,
        )
        control = base.copy(deep=True)
        control["phase13_domain"] = name
        control["phase13_domain_category"] = str(profile["category"])
        control["phase13_base_domain"] = base_domain
        control["phase13_shift_applied"] = False
        control["sequence_id"] = control["sequence_id"].astype(str) + f"|phase13-control:{name}"
        controls.append(control)
        shifted.append(apply_shift(base, name, seed))

    return pd.concat(controls, ignore_index=True), pd.concat(shifted, ignore_index=True)


def _domain_metrics(df: pd.DataFrame, candidate: dict[str, object]) -> dict[str, object]:
    truth_rows = int(df["truth_visible"].astype(bool).sum())
    available_mask = v1.p11._available(df)
    d = df[available_mask].copy()
    result: dict[str, object] = {
        "rows": int(len(df)),
        "truth_visible_rows": truth_rows,
        "available_rows": int(len(d)),
        "available_fraction": float(len(d) / truth_rows) if truth_rows else float("nan"),
    }
    for axis in ("lateral", "altitude"):
        err = d[f"p14_{axis}_abs_error_m"].to_numpy(float)
        hw = v3._halfwidths(d, candidate, axis, 0.95)
        p95e = float(np.percentile(err, 95)) if err.size else float("nan")
        p95w = float(np.percentile(hw, 95)) if hw.size else float("nan")
        result[f"{axis}_95_coverage"] = float(np.mean(err <= hw)) if err.size else float("nan")
        result[f"{axis}_p95_error_m"] = p95e
        result[f"{axis}_p95_halfwidth_m"] = p95w
        result[f"{axis}_p95_halfwidth_over_p95_error"] = p95w / p95e if p95e > 0 else float("nan")
    return result


def _innovation_error_spearman(df: pd.DataFrame, candidate: dict[str, object]) -> float:
    d = df[v1.p11._available(df)].copy()
    groups = v1.p11._groups(d).astype(str)
    d = d[groups.isin(set(v3.RELIABILITY_GROUPS))].copy()
    if len(d) < 10:
        return float("nan")
    scale = float(candidate["innovation_scales"]["lateral"])
    u = np.log1p(d["p9_anchor_innovation_lateral_abs"].to_numpy(float) / scale)
    err = d["p14_lateral_abs_error_m"].to_numpy(float)
    return float(pd.Series(u).corr(pd.Series(err), method="spearman"))


def _phase13_gates(
    control_result: dict[str, object],
    shifted_result: dict[str, object],
    domain_metrics: dict[str, dict[str, object]],
    spearman: float,
) -> dict[str, object]:
    domain_passes = {
        name: bool(
            float(metrics["lateral_95_coverage"]) >= DOMAIN_COVERAGE_FLOOR
            and float(metrics["altitude_95_coverage"]) >= DOMAIN_COVERAGE_FLOOR
        )
        for name, metrics in domain_metrics.items()
    }
    worst_lat = min(float(m["lateral_95_coverage"]) for m in domain_metrics.values())
    worst_alt = min(float(m["altitude_95_coverage"]) for m in domain_metrics.values())

    gates = {
        "g13_1_paired_control_integrity": {
            "phase12_primary_gates_pass": bool(control_result["all_primary_gates_pass"]),
            "pass": bool(control_result["all_primary_gates_pass"]),
        },
        "g13_2_zero_shot_shifted_primary_gates": {
            "phase12_primary_gates_pass": bool(shifted_result["all_primary_gates_pass"]),
            "pass": bool(shifted_result["all_primary_gates_pass"]),
        },
        "g13_3_thirteen_domain_honesty": {
            "domain_coverage_floor": DOMAIN_COVERAGE_FLOOR,
            "passing_domains": int(sum(domain_passes.values())),
            "required_domains": 13,
            "domain_passes": domain_passes,
            "pass": bool(len(domain_passes) == 13 and all(domain_passes.values())),
        },
        "g13_4_no_catastrophic_domain": {
            "coverage_floor": CATASTROPHIC_COVERAGE_FLOOR,
            "worst_lateral_95_coverage": worst_lat,
            "worst_altitude_95_coverage": worst_alt,
            "pass": bool(
                worst_lat >= CATASTROPHIC_COVERAGE_FLOOR
                and worst_alt >= CATASTROPHIC_COVERAGE_FLOOR
            ),
        },
        "g13_5_reliability_mechanism_survives_shift": {
            "continuity_innovation_error_spearman": spearman,
            "minimum": INNOVATION_ERROR_SPEARMAN_FLOOR,
            "pass": bool(np.isfinite(spearman) and spearman >= INNOVATION_ERROR_SPEARMAN_FLOOR),
        },
        "g13_6_zero_adaptation": {
            "candidate_changed": False,
            "recalibration_performed": False,
            "post_hoc_threshold_change": False,
            "pass": True,
        },
    }
    return gates


def evaluate(stage: str, candidate_path: Path, out: Path, git_sha: str) -> dict[str, object]:
    candidate = _validate_candidate(candidate_path)
    seed, _, _, minimums = _stage_config(stage)
    control, shifted = generate_gauntlet(stage, candidate)

    control_result = v3._summarize(
        control,
        candidate,
        f"phase13_{stage}_paired_control",
        seed,
        minimums,
    )
    shifted_result = v3._summarize(
        shifted,
        candidate,
        EVIDENCE_ROLES[stage],
        seed,
        minimums,
    )

    per_domain = {
        name: _domain_metrics(group, candidate)
        for name, group in shifted.groupby("phase13_domain", sort=True)
    }
    spearman = _innovation_error_spearman(shifted, candidate)
    gates = _phase13_gates(control_result, shifted_result, per_domain, spearman)
    pass_all = bool(all(bool(g["pass"]) for g in gates.values()))

    result = {
        "schema": f"aegisland.phase13.external-validity-gauntlet.{stage}-result.v1",
        "phase13_name": "Thirteen-Domain Gauntlet",
        "evidence_role": EVIDENCE_ROLES[stage],
        "evaluated_seed_seen_after_run": seed,
        "scientific_git_sha": git_sha,
        "frozen_phase12_scientific_sha": FROZEN_PHASE12_SCIENTIFIC_SHA,
        "frozen_phase12_candidate_sha256": FROZEN_PHASE12_CANDIDATE_SHA256,
        "domain_count": len(DOMAIN_PROFILES),
        "domain_names": [str(p["name"]) for p in DOMAIN_PROFILES],
        "zero_shot": True,
        "adaptation_performed": False,
        "recalibration_performed": False,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "paired_control_result": control_result,
        "shifted_result": shifted_result,
        "per_domain": per_domain,
        "phase13_gates": gates,
        "phase13_pass": pass_all,
    }

    out.mkdir(parents=True, exist_ok=True)
    control.to_csv(out / f"{stage}_paired_control_frames.csv", index=False)
    shifted.to_csv(out / f"{stage}_shifted_frames.csv", index=False)
    (out / f"{stage}_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "schema": "aegisland.phase13.external-validity-gauntlet.manifest.v1",
        "stage": stage,
        "scientific_git_sha": git_sha,
        "frozen_phase12_candidate_sha256": FROZEN_PHASE12_CANDIDATE_SHA256,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "files": {
            path.name: {
                "sha256": _sha256_file(path),
                "bytes": path.stat().st_size,
            }
            for path in (
                out / f"{stage}_paired_control_frames.csv",
                out / f"{stage}_shifted_frames.csv",
                out / f"{stage}_result.json",
            )
        },
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Phase 13 Thirteen-Domain Gauntlet: zero-shot external-validity stress test"
    )
    p.add_argument("--stage", choices=("dev", "transfer", "validation", "final"), required=True)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--git-sha", default="unknown")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    result = evaluate(args.stage, args.candidate, args.out, args.git_sha)
    print("PHASE13_DOMAIN_COUNT=" + str(result["domain_count"]))
    print("PHASE13_ZERO_SHOT=true")
    print("PHASE13_PASS=" + str(bool(result["phase13_pass"])).lower())
    print("PHASE13_GATES=" + json.dumps(result["phase13_gates"], sort_keys=True))


if __name__ == "__main__":
    main()
