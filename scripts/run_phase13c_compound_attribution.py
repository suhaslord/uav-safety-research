from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scripts import run_phase13_external_validity_gauntlet as p13
except ModuleNotFoundError:
    import run_phase13_external_validity_gauntlet as p13

PHASE13C_NAME = "Thirteen-Contrast Compound Interaction Attribution"
FROZEN_PHASE12_SCIENTIFIC_SHA = p13.FROZEN_PHASE12_SCIENTIFIC_SHA
FROZEN_PHASE12_CANDIDATE_SHA256 = p13.FROZEN_PHASE12_CANDIDATE_SHA256
BASE_DOMAIN = "edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout"
ORIGINAL_COMPOUND_NAME = "latency_wind_calibration_compound"

COMPONENTS = ("A", "B", "C", "D", "E", "F")
COMPONENT_NAMES = {
    "A": "latency",
    "B": "bias_pair",
    "C": "lateral_wind_drift",
    "D": "measurement_noise_pair",
    "E": "innovation_response",
    "F": "severity_response",
}

CONTRAST_COMPONENTS = {
    "latency_only": frozenset({"A"}),
    "bias_only": frozenset({"B"}),
    "wind_only": frozenset({"C"}),
    "noise_only": frozenset({"D"}),
    "innovation_response_only": frozenset({"E"}),
    "severity_response_only": frozenset({"F"}),
    "full_minus_latency": frozenset({"B", "C", "D", "E", "F"}),
    "full_minus_bias": frozenset({"A", "C", "D", "E", "F"}),
    "full_minus_wind": frozenset({"A", "B", "D", "E", "F"}),
    "full_minus_noise": frozenset({"A", "B", "C", "E", "F"}),
    "full_minus_innovation_response": frozenset({"A", "B", "C", "D", "F"}),
    "full_minus_severity_response": frozenset({"A", "B", "C", "D", "E"}),
    "full_compound": frozenset(COMPONENTS),
}

SINGLETON_CONTRAST = {
    "A": "latency_only",
    "B": "bias_only",
    "C": "wind_only",
    "D": "noise_only",
    "E": "innovation_response_only",
    "F": "severity_response_only",
}
LEAVE_ONE_OUT_CONTRAST = {
    "A": "full_minus_latency",
    "B": "full_minus_bias",
    "C": "full_minus_wind",
    "D": "full_minus_noise",
    "E": "full_minus_innovation_response",
    "F": "full_minus_severity_response",
}

STAGE_SEEDS = {
    "dev": 1313135,
    "transfer": 1313136,
    "validation": 1313137,
    "final": 1313138,
}
STAGE_FAMILIES = {
    "dev": tuple(range(1393, 1417)),
    "transfer": tuple(range(1417, 1441)),
    "validation": tuple(range(1441, 1465)),
    "final": tuple(range(1465, 1489)),
}
EVIDENCE_ROLES = {
    "dev": "phase13c_development_mechanism_discovery_permanently_seen_after_run",
    "transfer": "phase13c_transfer_confirmation_seen_once_after_authorization",
    "validation": "phase13c_protected_seen_once_after_transfer_confirmation",
    "final": "phase13c_final_seen_once_after_protected_confirmation",
}

FAILURE_DELTA_THRESHOLD = -0.08
CATASTROPHIC_COVERAGE_FLOOR = 0.80


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _validate_stage(stage: str) -> tuple[int, tuple[int, ...], dict[str, tuple[int, ...]]]:
    if stage not in STAGE_SEEDS:
        raise RuntimeError(f"unknown Phase 13C stage {stage}")
    families = STAGE_FAMILIES[stage]
    return STAGE_SEEDS[stage], families, p13._strata(families)


def _compound_profile() -> dict[str, object]:
    profile = p13._profile(ORIGINAL_COMPOUND_NAME)
    if str(profile["base_domain"]) != BASE_DOMAIN:
        raise RuntimeError("Phase 13C base-domain identity mismatch")
    return profile


def _noise_rng(seed: int, sequence_id: str, frame: int) -> np.random.Generator:
    # Preserve the original domain-13 noise stream tag so full_compound remains
    # execution-equivalent to the frozen Phase 13 transform.
    return np.random.default_rng(
        p13._stable_seed(seed, ORIGINAL_COMPOUND_NAME, sequence_id, int(frame), "noise")
    )


def _apply_component_subset(
    df: pd.DataFrame,
    contrast_name: str,
    components: frozenset[str],
    seed: int,
) -> pd.DataFrame:
    if components == frozenset(COMPONENTS):
        # Exact frozen implementation path for the full compound.
        out = p13.apply_shift(df, ORIGINAL_COMPOUND_NAME, seed)
        out["phase13c_contrast"] = contrast_name
        out["phase13c_components"] = "+".join(COMPONENTS)
        return out

    unknown = set(components).difference(COMPONENTS)
    if unknown:
        raise RuntimeError(f"unknown Phase 13C component(s): {sorted(unknown)}")

    out = df.copy(deep=True)
    out["phase13c_contrast"] = contrast_name
    out["phase13c_components"] = "+".join(sorted(components))
    out["phase13_domain"] = ORIGINAL_COMPOUND_NAME
    out["phase13_domain_category"] = "compound"
    out["phase13_base_domain"] = BASE_DOMAIN
    out["phase13_shift_applied"] = bool(components)
    out["sequence_id"] = out["sequence_id"].astype(str) + f"|phase13c:{contrast_name}"

    original_lat = out["p14_estimate_lateral_x_m"].to_numpy(float).copy()
    original_alt = out["p14_estimate_altitude_m"].to_numpy(float).copy()

    for _, idx_obj in out.groupby("sequence_id", sort=False).groups.items():
        idx = list(idx_obj)
        frames = out.loc[idx, "frame_index"].to_numpy(int)
        lat = out.loc[idx, "p14_estimate_lateral_x_m"].to_numpy(float).copy()
        alt = out.loc[idx, "p14_estimate_altitude_m"].to_numpy(float).copy()

        if "A" in components:
            lag = np.full(len(idx), 2, dtype=int)
            lat = p13._lagged(lat, lag)
            alt = p13._lagged(alt, lag)

        if "B" in components:
            lat = lat + 0.04
            alt = alt + 0.08

        if "C" in components:
            t = frames / max(1.0, float(np.max(frames) or 1))
            lat = lat + 0.07 * (2.0 * t - 1.0)

        if "D" in components:
            seq_for_stream = str(out.loc[idx[0], "sequence_id"])
            # Remove the Phase 13C suffix before deriving the frozen noise stream.
            seq_for_stream = seq_for_stream.split("|phase13c:", 1)[0]
            for j, frame in enumerate(frames):
                rng = _noise_rng(seed, seq_for_stream, int(frame))
                lat[j] += float(rng.normal(0.0, 0.02))
                alt[j] += float(rng.normal(0.0, 0.04))

        out.loc[idx, "p14_estimate_lateral_x_m"] = lat
        out.loc[idx, "p14_estimate_altitude_m"] = alt

    available = out["p14_available"].astype(bool) & out["truth_visible"].astype(bool)
    out.loc[~available, "p14_estimate_lateral_x_m"] = np.nan
    out.loc[~available, "p14_estimate_altitude_m"] = np.nan

    out["p14_lateral_abs_error_m"] = np.abs(
        out["p14_estimate_lateral_x_m"].to_numpy(float)
        - out["truth_lateral_x_m"].to_numpy(float)
    )
    out["p14_altitude_abs_error_m"] = np.abs(
        out["p14_estimate_altitude_m"].to_numpy(float)
        - out["truth_altitude_m"].to_numpy(float)
    )

    lat_delta = np.abs(out["p14_estimate_lateral_x_m"].to_numpy(float) - original_lat)
    alt_delta = np.abs(out["p14_estimate_altitude_m"].to_numpy(float) - original_alt)

    if "E" in components:
        innovation = out["p9_anchor_innovation_lateral_abs"].to_numpy(float)
        if not np.all(np.isfinite(innovation)) or np.any(innovation < 0.0):
            raise RuntimeError("Phase 13C requires finite nonnegative anchor innovation")
        out["p9_anchor_innovation_lateral_abs"] = np.maximum(
            0.0,
            innovation * 1.35 + 0.45 * np.nan_to_num(lat_delta, nan=0.0),
        )

    if "F" in components:
        severity = out["severity"].to_numpy(float)
        if not np.all(np.isfinite(severity)):
            raise RuntimeError("Phase 13C requires finite severity")
        response = np.clip(
            (
                np.nan_to_num(lat_delta, nan=0.0)
                + 0.5 * np.nan_to_num(alt_delta, nan=0.0)
            )
            / 0.30,
            0.0,
            1.0,
        )
        out["severity"] = np.clip(severity + 0.12 + 0.18 * response, 0.0, 1.0)

    return out


def _metrics(df: pd.DataFrame, candidate: dict[str, object]) -> dict[str, object]:
    truth_rows = int(df["truth_visible"].astype(bool).sum())
    available = p13.v1.p11._available(df)
    d = df[available].copy()
    result: dict[str, object] = {
        "rows": int(len(df)),
        "truth_visible_rows": truth_rows,
        "available_rows": int(len(d)),
        "available_fraction": float(len(d) / truth_rows) if truth_rows else float("nan"),
    }
    for axis in ("lateral", "altitude"):
        err = d[f"p14_{axis}_abs_error_m"].to_numpy(float)
        hw = p13.v3._halfwidths(d, candidate, axis, 0.95)
        result[f"{axis}_95_coverage"] = float(np.mean(err <= hw)) if err.size else float("nan")
        result[f"{axis}_p95_error_m"] = float(np.percentile(err, 95)) if err.size else float("nan")
        result[f"{axis}_median_halfwidth_m"] = float(np.median(hw)) if hw.size else float("nan")
        result[f"{axis}_p95_halfwidth_m"] = float(np.percentile(hw, 95)) if hw.size else float("nan")
    return result


def _integrity(control: pd.DataFrame, contrast: pd.DataFrame) -> dict[str, object]:
    same_rows = len(control) == len(contrast)
    same_truth_visible = bool(
        np.array_equal(
            control["truth_visible"].astype(bool).to_numpy(),
            contrast["truth_visible"].astype(bool).to_numpy(),
        )
    )
    same_available = bool(
        np.array_equal(
            control["p14_available"].astype(bool).to_numpy(),
            contrast["p14_available"].astype(bool).to_numpy(),
        )
    )
    same_lat_truth = bool(
        np.array_equal(
            control["truth_lateral_x_m"].to_numpy(float),
            contrast["truth_lateral_x_m"].to_numpy(float),
            equal_nan=True,
        )
    )
    same_alt_truth = bool(
        np.array_equal(
            control["truth_altitude_m"].to_numpy(float),
            contrast["truth_altitude_m"].to_numpy(float),
            equal_nan=True,
        )
    )
    return {
        "same_row_count": bool(same_rows),
        "same_truth_visible": same_truth_visible,
        "same_useful_availability": same_available,
        "same_lateral_truth": same_lat_truth,
        "same_altitude_truth": same_alt_truth,
        "pass": bool(
            same_rows
            and same_truth_visible
            and same_available
            and same_lat_truth
            and same_alt_truth
        ),
    }


def _rank_component(values: dict[str, float]) -> str:
    # Largest value wins; alphabetic component label is the preregistered tie break.
    return sorted(values, key=lambda c: (-float(values[c]), c))[0]


def _attribution(
    control_metrics: dict[str, object],
    contrast_metrics: dict[str, dict[str, object]],
) -> dict[str, object]:
    control_cov = float(control_metrics["lateral_95_coverage"])
    full_cov = float(contrast_metrics["full_compound"]["lateral_95_coverage"])
    singleton_losses = {
        component: float(
            control_cov
            - float(contrast_metrics[SINGLETON_CONTRAST[component]]["lateral_95_coverage"])
        )
        for component in COMPONENTS
    }
    leave_one_out_recoveries = {
        component: float(
            float(contrast_metrics[LEAVE_ONE_OUT_CONTRAST[component]]["lateral_95_coverage"])
            - full_cov
        )
        for component in COMPONENTS
    }
    full_loss = float(control_cov - full_cov)
    sum_singletons = float(sum(singleton_losses.values()))
    interaction_excess = float(full_loss - sum_singletons)
    return {
        "singleton_lateral_coverage_losses": singleton_losses,
        "leave_one_out_lateral_coverage_recoveries": leave_one_out_recoveries,
        "full_lateral_coverage_loss": full_loss,
        "sum_singleton_lateral_coverage_losses": sum_singletons,
        "interaction_excess": interaction_excess,
        "largest_singleton_loss_component": _rank_component(singleton_losses),
        "largest_leave_one_out_recovery_component": _rank_component(leave_one_out_recoveries),
        "component_names": COMPONENT_NAMES,
    }


def _manifest(out: Path, files: list[str], stage: str, git_sha: str) -> None:
    payload = {
        "schema": "aegisland.phase13c.compound-attribution.manifest.v1",
        "stage": stage,
        "scientific_git_sha": git_sha,
        "frozen_phase12_candidate_sha256": FROZEN_PHASE12_CANDIDATE_SHA256,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "files": {
            name: {
                "sha256": _sha256_file(out / name),
                "bytes": int((out / name).stat().st_size),
            }
            for name in files
        },
    }
    (out / "manifest.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def evaluate(stage: str, candidate_path: Path, out: Path, git_sha: str) -> dict[str, object]:
    seed, families, strata = _validate_stage(stage)
    candidate = p13._validate_candidate(candidate_path)
    _compound_profile()

    base = p13.v1._event(
        f"phase13c_{stage}_domain13_base",
        seed,
        families,
        (BASE_DOMAIN,),
        strata,
        candidate,
    )
    control = base.copy(deep=True)
    control["phase13c_contrast"] = "control"
    control["phase13c_components"] = ""
    control["sequence_id"] = control["sequence_id"].astype(str) + "|phase13c:control"

    contrast_frames: dict[str, pd.DataFrame] = {}
    for name, components in CONTRAST_COMPONENTS.items():
        contrast_frames[name] = _apply_component_subset(base, name, components, seed)

    control_metrics = _metrics(control, candidate)
    contrast_metrics = {
        name: _metrics(frame, candidate) for name, frame in contrast_frames.items()
    }
    integrity = {
        name: _integrity(control, frame) for name, frame in contrast_frames.items()
    }

    for name, metrics in contrast_metrics.items():
        for axis in ("lateral", "altitude"):
            metrics[f"{axis}_coverage_delta_vs_control"] = float(
                float(metrics[f"{axis}_95_coverage"])
                - float(control_metrics[f"{axis}_95_coverage"])
            )
            c_err = float(control_metrics[f"{axis}_p95_error_m"])
            s_err = float(metrics[f"{axis}_p95_error_m"])
            metrics[f"{axis}_p95_error_inflation_vs_control"] = (
                float(s_err / c_err) if c_err > 0.0 else float("nan")
            )

    attribution = _attribution(control_metrics, contrast_metrics)
    full = contrast_metrics["full_compound"]
    full_delta = float(full["lateral_coverage_delta_vs_control"])
    full_coverage = float(full["lateral_95_coverage"])

    finite_attr = all(
        np.isfinite(float(v))
        for v in (
            list(attribution["singleton_lateral_coverage_losses"].values())
            + list(attribution["leave_one_out_lateral_coverage_recoveries"].values())
            + [attribution["interaction_excess"]]
        )
    )

    gates = {
        "c13_1_construction_integrity": {
            "passing_contrasts": int(sum(bool(v["pass"]) for v in integrity.values())),
            "required_contrasts": 13,
            "contrast_passes": {k: bool(v["pass"]) for k, v in integrity.items()},
            "pass": bool(len(integrity) == 13 and all(bool(v["pass"]) for v in integrity.values())),
        },
        "c13_2_full_compound_execution_equivalence": {
            "implementation_path": "direct_frozen_phase13_apply_shift",
            "fixture_test_required_before_evidence": True,
            "pass": True,
        },
        "c13_3_fresh_failure_phenomenon_replication": {
            "full_compound_lateral_coverage_delta_vs_control": full_delta,
            "maximum_delta": FAILURE_DELTA_THRESHOLD,
            "full_compound_lateral_95_coverage": full_coverage,
            "catastrophic_floor": CATASTROPHIC_COVERAGE_FLOOR,
            "pass": bool(
                full_delta <= FAILURE_DELTA_THRESHOLD
                and full_coverage >= CATASTROPHIC_COVERAGE_FLOOR
            ),
        },
        "c13_4_attribution_completeness": {
            "finite": bool(finite_attr),
            "singleton_count": len(attribution["singleton_lateral_coverage_losses"]),
            "leave_one_out_count": len(attribution["leave_one_out_lateral_coverage_recoveries"]),
            "pass": bool(finite_attr and len(COMPONENTS) == 6),
        },
        "c13_5_zero_adaptation": {
            "phase12_candidate_changed": False,
            "domain13_base_domain_changed": False,
            "component_magnitudes_changed": False,
            "interval_recalibration": False,
            "post_hoc_multiplier": False,
            "controller_tuning": False,
            "pass": True,
        },
    }
    pass_all = bool(all(bool(g["pass"]) for g in gates.values()))

    result = {
        "schema": f"aegisland.phase13c.compound-attribution.{stage}-result.v1",
        "phase13c_name": PHASE13C_NAME,
        "evidence_role": EVIDENCE_ROLES[stage],
        "evaluated_seed_seen_after_run": seed,
        "families": list(families),
        "scientific_git_sha": git_sha,
        "frozen_phase12_scientific_sha": FROZEN_PHASE12_SCIENTIFIC_SHA,
        "frozen_phase12_candidate_sha256": FROZEN_PHASE12_CANDIDATE_SHA256,
        "base_domain": BASE_DOMAIN,
        "contrast_count": 13,
        "contrast_names": list(CONTRAST_COMPONENTS),
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "phase13a_failure_preserved": True,
        "phase13b_failure_preserved": True,
        "zero_adaptation": True,
        "phase13c_pass": pass_all,
        "all_primary_gates_pass": pass_all,
        "gates": gates,
        "control_metrics": control_metrics,
        "contrast_metrics": contrast_metrics,
        "construction_integrity": integrity,
        "attribution": attribution,
    }

    out.mkdir(parents=True, exist_ok=True)
    control_name = f"{stage}_control_frames.csv"
    contrast_name = f"{stage}_contrast_frames.csv"
    result_name = f"{stage}_result.json"
    candidate_name = "candidate_freeze.json"
    control.to_csv(out / control_name, index=False)
    pd.concat(contrast_frames.values(), ignore_index=True).to_csv(out / contrast_name, index=False)
    (out / result_name).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / candidate_name).write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _manifest(out, [control_name, contrast_name, result_name, candidate_name], stage, git_sha)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 13C compound interaction attribution")
    parser.add_argument("--stage", choices=("dev", "transfer", "validation", "final"), required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--git-sha", default="unknown")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = evaluate(args.stage, args.candidate, args.out, args.git_sha)
    print(
        "PHASE13C_"
        + args.stage.upper()
        + "_RESULT="
        + json.dumps(
            {
                "phase13c_pass": result["phase13c_pass"],
                "gates": result["gates"],
                "attribution": result["attribution"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()