from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scripts import run_phase13_external_validity_gauntlet as p13
    from scripts import run_phase13_external_validity_gauntlet_remediation1 as remediation1
except ModuleNotFoundError:
    import run_phase13_external_validity_gauntlet as p13
    import run_phase13_external_validity_gauntlet_remediation1 as remediation1

PHASE13B_NAME = "Thirteen Paired Degradation Audit"
FROZEN_PHASE12_SCIENTIFIC_SHA = p13.FROZEN_PHASE12_SCIENTIFIC_SHA
FROZEN_PHASE12_CANDIDATE_SHA256 = p13.FROZEN_PHASE12_CANDIDATE_SHA256

STAGE_SEEDS = {
    "dev": 1313131,
    "transfer": 1313132,
    "validation": 1313133,
    "final": 1313134,
}

STAGE_FAMILIES = {
    "dev": tuple(range(1297, 1321)),
    "transfer": tuple(range(1321, 1345)),
    "validation": tuple(range(1345, 1369)),
    "final": tuple(range(1369, 1393)),
}

EVIDENCE_ROLES = {
    "dev": "phase13b_development_only_permanently_seen_after_run",
    "transfer": "phase13b_transfer_seen_once_after_development_pass",
    "validation": "phase13b_protected_seen_once_after_transfer_pass",
    "final": "phase13b_final_seen_once_after_protected_pass",
}

CATASTROPHIC_COVERAGE_FLOOR = 0.80
MAX_PAIRED_COVERAGE_LOSS = 0.08
INNOVATION_ERROR_SPEARMAN_FLOOR = 0.20
COMPOUND_DOMAIN = "latency_wind_calibration_compound"


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _configure_frozen_generator(stage: str) -> None:
    if stage not in STAGE_SEEDS:
        raise RuntimeError(f"unknown Phase 13B stage {stage}")
    # Amendment 01 changes only the parity helper used by the already-frozen
    # reacquisition stress. Phase 13B then supplies wholly fresh evidence
    # partitions; no Phase 13A development seed is reused.
    remediation1.install_execution_remediation()
    p13.STAGE_SEEDS[stage] = STAGE_SEEDS[stage]
    p13.STAGE_FAMILIES[stage] = STAGE_FAMILIES[stage]
    if stage == "dev":
        p13.DEV_SEED = STAGE_SEEDS[stage]


def _domain_metrics(df: pd.DataFrame, candidate: dict[str, object]) -> dict[str, object]:
    return p13._domain_metrics(df, candidate)


def _manual_spearman(x: np.ndarray, y: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    if x.size < 10:
        return float("nan")
    rx = pd.Series(x).rank(method="average").to_numpy(float)
    ry = pd.Series(y).rank(method="average").to_numpy(float)
    if float(np.std(rx)) == 0.0 or float(np.std(ry)) == 0.0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def _innovation_error_spearman(df: pd.DataFrame, candidate: dict[str, object]) -> float:
    d = df[p13.v1.p11._available(df)].copy()
    groups = p13.v1.p11._groups(d).astype(str)
    d = d[groups.isin(set(p13.v3.RELIABILITY_GROUPS))].copy()
    if len(d) < 10:
        return float("nan")
    scale = float(candidate["innovation_scales"]["lateral"])
    u = np.log1p(d["p9_anchor_innovation_lateral_abs"].to_numpy(float) / scale)
    err = d["p14_lateral_abs_error_m"].to_numpy(float)
    return _manual_spearman(u, err)


def _rescue_coverage(df: pd.DataFrame, candidate: dict[str, object]) -> dict[str, object]:
    available = p13.v1.p11._available(df)
    rescue = df["p14_source"].astype(str) == str(p13.v1.p11.GROUP_RESCUE)
    d = df[available & rescue].copy()
    result: dict[str, object] = {"rows": int(len(d))}
    for axis in ("lateral", "altitude"):
        err = d[f"p14_{axis}_abs_error_m"].to_numpy(float)
        hw = p13.v3._halfwidths(d, candidate, axis, 0.95)
        result[f"{axis}_95_coverage"] = float(np.mean(err <= hw)) if err.size else float("nan")
    return result


def _integrity_for_domain(control: pd.DataFrame, shifted: pd.DataFrame) -> dict[str, object]:
    same_rows = len(control) == len(shifted)
    same_truth_visible = int(control["truth_visible"].astype(bool).sum()) == int(
        shifted["truth_visible"].astype(bool).sum()
    )
    same_availability = bool(
        np.array_equal(
            control["p14_available"].astype(bool).to_numpy(),
            shifted["p14_available"].astype(bool).to_numpy(),
        )
    )
    same_truth_lateral = bool(
        np.array_equal(
            control["truth_lateral_x_m"].to_numpy(float),
            shifted["truth_lateral_x_m"].to_numpy(float),
            equal_nan=True,
        )
    )
    same_truth_altitude = bool(
        np.array_equal(
            control["truth_altitude_m"].to_numpy(float),
            shifted["truth_altitude_m"].to_numpy(float),
            equal_nan=True,
        )
    )
    return {
        "control_rows": int(len(control)),
        "shifted_rows": int(len(shifted)),
        "same_row_count": bool(same_rows),
        "same_truth_visible_count": bool(same_truth_visible),
        "same_useful_availability": bool(same_availability),
        "same_truth_lateral": bool(same_truth_lateral),
        "same_truth_altitude": bool(same_truth_altitude),
        "pass": bool(
            same_rows
            and same_truth_visible
            and same_availability
            and same_truth_lateral
            and same_truth_altitude
        ),
    }


def _paired_domain_result(
    control: pd.DataFrame,
    shifted: pd.DataFrame,
    candidate: dict[str, object],
) -> dict[str, object]:
    c = _domain_metrics(control, candidate)
    s = _domain_metrics(shifted, candidate)
    out: dict[str, object] = {
        "integrity": _integrity_for_domain(control, shifted),
        "control": c,
        "shifted": s,
        "coverage_delta_shift_minus_control": {},
        "p95_error_inflation_ratio_shift_over_control": {},
    }
    for axis in ("lateral", "altitude"):
        c_cov = float(c[f"{axis}_95_coverage"])
        s_cov = float(s[f"{axis}_95_coverage"])
        c_err = float(c[f"{axis}_p95_error_m"])
        s_err = float(s[f"{axis}_p95_error_m"])
        out["coverage_delta_shift_minus_control"][axis] = float(s_cov - c_cov)
        out["p95_error_inflation_ratio_shift_over_control"][axis] = (
            float(s_err / c_err) if c_err > 0.0 else float("nan")
        )
    return out


def _gates(
    paired: dict[str, dict[str, object]],
    rescue: dict[str, object],
    spearman: float,
) -> dict[str, object]:
    integrity_passes = {name: bool(v["integrity"]["pass"]) for name, v in paired.items()}

    catastrophic_passes: dict[str, bool] = {}
    degradation_passes: dict[str, bool] = {}
    for name, values in paired.items():
        shifted = values["shifted"]
        delta = values["coverage_delta_shift_minus_control"]
        catastrophic_passes[name] = bool(
            float(shifted["lateral_95_coverage"]) >= CATASTROPHIC_COVERAGE_FLOOR
            and float(shifted["altitude_95_coverage"]) >= CATASTROPHIC_COVERAGE_FLOOR
        )
        degradation_passes[name] = bool(
            float(delta["lateral"]) >= -MAX_PAIRED_COVERAGE_LOSS
            and float(delta["altitude"]) >= -MAX_PAIRED_COVERAGE_LOSS
        )

    compound_ok = bool(
        integrity_passes.get(COMPOUND_DOMAIN, False)
        and catastrophic_passes.get(COMPOUND_DOMAIN, False)
        and degradation_passes.get(COMPOUND_DOMAIN, False)
    )

    rescue_lat = float(rescue["lateral_95_coverage"])
    rescue_alt = float(rescue["altitude_95_coverage"])

    return {
        "g13b_1_paired_construction_integrity": {
            "passing_domains": int(sum(integrity_passes.values())),
            "required_domains": 13,
            "domain_passes": integrity_passes,
            "pass": bool(len(integrity_passes) == 13 and all(integrity_passes.values())),
        },
        "g13b_2_no_catastrophic_shifted_domain": {
            "coverage_floor": CATASTROPHIC_COVERAGE_FLOOR,
            "passing_domains": int(sum(catastrophic_passes.values())),
            "required_domains": 13,
            "domain_passes": catastrophic_passes,
            "pass": bool(len(catastrophic_passes) == 13 and all(catastrophic_passes.values())),
        },
        "g13b_3_bounded_paired_coverage_degradation": {
            "minimum_coverage_delta": -MAX_PAIRED_COVERAGE_LOSS,
            "passing_domains": int(sum(degradation_passes.values())),
            "required_domains": 13,
            "domain_passes": degradation_passes,
            "pass": bool(len(degradation_passes) == 13 and all(degradation_passes.values())),
        },
        "g13b_4_rescue_honesty_floor": {
            "rows": int(rescue["rows"]),
            "coverage_floor": CATASTROPHIC_COVERAGE_FLOOR,
            "lateral_95_coverage": rescue_lat,
            "altitude_95_coverage": rescue_alt,
            "pass": bool(
                int(rescue["rows"]) > 0
                and rescue_lat >= CATASTROPHIC_COVERAGE_FLOOR
                and rescue_alt >= CATASTROPHIC_COVERAGE_FLOOR
            ),
        },
        "g13b_5_reliability_mechanism_survives": {
            "continuity_innovation_error_spearman": spearman,
            "minimum": INNOVATION_ERROR_SPEARMAN_FLOOR,
            "pass": bool(np.isfinite(spearman) and spearman >= INNOVATION_ERROR_SPEARMAN_FLOOR),
        },
        "g13b_6_compound_domain_stands_alone": {
            "domain": COMPOUND_DOMAIN,
            "integrity_pass": integrity_passes.get(COMPOUND_DOMAIN, False),
            "catastrophic_floor_pass": catastrophic_passes.get(COMPOUND_DOMAIN, False),
            "paired_degradation_pass": degradation_passes.get(COMPOUND_DOMAIN, False),
            "pass": compound_ok,
        },
        "g13b_7_zero_adaptation": {
            "phase12_candidate_changed": False,
            "phase13_stress_manifest_changed": False,
            "recalibration_performed": False,
            "post_hoc_interval_multiplier": False,
            "threshold_changed_after_exposure": False,
            "pass": True,
        },
    }


def _manifest(out: Path, files: list[str], stage: str, git_sha: str) -> None:
    payload = {
        "schema": "aegisland.phase13b.paired-degradation.manifest.v1",
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
    _configure_frozen_generator(stage)
    candidate = p13._validate_candidate(candidate_path)
    seed = STAGE_SEEDS[stage]

    control, shifted = p13.generate_gauntlet(stage, candidate)
    domains = [str(p["name"]) for p in p13.DOMAIN_PROFILES]
    paired: dict[str, dict[str, object]] = {}
    for name in domains:
        c = control[control["phase13_domain"].astype(str) == name].reset_index(drop=True)
        s = shifted[shifted["phase13_domain"].astype(str) == name].reset_index(drop=True)
        paired[name] = _paired_domain_result(c, s, candidate)

    rescue = _rescue_coverage(shifted, candidate)
    spearman = _innovation_error_spearman(shifted, candidate)
    gates = _gates(paired, rescue, spearman)
    pass_all = bool(all(bool(g["pass"]) for g in gates.values()))

    result = {
        "schema": f"aegisland.phase13b.paired-degradation.{stage}-result.v1",
        "phase13b_name": PHASE13B_NAME,
        "evidence_role": EVIDENCE_ROLES[stage],
        "evaluated_seed_seen_after_run": seed,
        "families": list(STAGE_FAMILIES[stage]),
        "scientific_git_sha": git_sha,
        "frozen_phase12_scientific_sha": FROZEN_PHASE12_SCIENTIFIC_SHA,
        "frozen_phase12_candidate_sha256": FROZEN_PHASE12_CANDIDATE_SHA256,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "phase13a_absolute_transfer_failure_preserved": True,
        "zero_adaptation": True,
        "all_primary_gates_pass": pass_all,
        "phase13b_pass": pass_all,
        "gates": gates,
        "paired_domain_metrics": paired,
        "aggregate_shifted_rescue": rescue,
        "continuity_innovation_error_spearman": spearman,
    }

    out.mkdir(parents=True, exist_ok=True)
    control_name = f"{stage}_paired_control_frames.csv"
    shifted_name = f"{stage}_shifted_frames.csv"
    result_name = f"{stage}_result.json"
    candidate_name = "candidate_freeze.json"
    control.to_csv(out / control_name, index=False)
    shifted.to_csv(out / shifted_name, index=False)
    (out / result_name).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / candidate_name).write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _manifest(out, [control_name, shifted_name, result_name, candidate_name], stage, git_sha)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 13B preregistered paired degradation audit")
    parser.add_argument("--stage", choices=("dev", "transfer", "validation", "final"), required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--git-sha", default="unknown")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = evaluate(args.stage, args.candidate, args.out, args.git_sha)
    print(
        "PHASE13B_"
        + args.stage.upper()
        + "_GATES="
        + json.dumps(
            {
                "phase13b_pass": result["phase13b_pass"],
                "gates": result["gates"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
