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
    from scripts import run_phase13_external_validity_gauntlet as p13
except ModuleNotFoundError:
    import run_phase12_adaptive_normalized_conformal as v1
    import run_phase12_adaptive_normalized_conformal_v3 as v3
    import run_phase13_external_validity_gauntlet as p13

PHASE14_NAME = "Uncertainty-Gated Recoverability Bridge"
BRIDGE_SCHEMA = "aegisland.phase14.uncertainty-recoverability.bridge-candidate.v1"
FROZEN_PHASE12_SCIENTIFIC_SHA = p13.FROZEN_PHASE12_SCIENTIFIC_SHA
FROZEN_PHASE12_CANDIDATE_SHA256 = p13.FROZEN_PHASE12_CANDIDATE_SHA256

RECOVERABLE_HALF_WIDTH_M = {"lateral": 0.30, "altitude": 0.85}
RESERVE_FRACTION = 0.90
NORMALIZED_RESIDUAL_QUANTILE = 0.99
HALFWIDTH_FLOOR_M = 1.0e-9
LATENCY_PROFILE = "fixed_latency_2f"
LATENCY_BASE_DOMAIN = "small_scale+temporal_dropout"

FIT_SEED = 1414140
STAGE_SEEDS = {
    "dev": 1414141,
    "transfer": 1414142,
    "validation": 1414143,
    "final": 1414144,
}
FIT_FAMILIES = tuple(range(1489, 1521))
STAGE_FAMILIES = {
    "dev": tuple(range(1521, 1545)),
    "transfer": tuple(range(1545, 1569)),
    "validation": tuple(range(1569, 1593)),
    "final": tuple(range(1593, 1617)),
}
STAGE_DOMAINS = {
    "dev": v1.DEV_DOMAINS,
    "transfer": v1.TRANSFER_DOMAINS,
    "validation": v1.VALIDATION_DOMAINS,
    "final": v1.FINAL_DOMAINS,
}
FIT_DOMAINS = v1.SCALE_FIT_DOMAINS

GATE_THRESHOLDS = {
    "natural_normalized_residual_coverage": 0.985,
    "natural_empirical_containment": 0.99,
    "natural_admission_fraction": 0.50,
    "latency_normalized_residual_coverage": 0.95,
    "latency_empirical_containment": 0.97,
    "latency_admission_fraction": 0.30,
}


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _strata(families: tuple[int, ...]) -> dict[str, tuple[int, ...]]:
    if len(families) % 4 != 0:
        raise RuntimeError("Phase 14 family count must divide evenly into four strata")
    per = len(families) // 4
    names = ("bootstrap5", "gap3", "gap7", "gap12")
    return {name: families[i * per : (i + 1) * per] for i, name in enumerate(names)}


def _validate_phase12_candidate(path: Path) -> dict[str, object]:
    if _sha256_file(path) != FROZEN_PHASE12_CANDIDATE_SHA256:
        raise RuntimeError("Phase 14 requires the exact frozen Phase 12 iteration-3 candidate")
    candidate = json.loads(path.read_text(encoding="utf-8"))
    if candidate.get("schema") != v3.CANDIDATE_SCHEMA:
        raise RuntimeError("Phase 14 predecessor candidate schema mismatch")
    if candidate.get("scientific_git_sha") != FROZEN_PHASE12_SCIENTIFIC_SHA:
        raise RuntimeError("Phase 14 predecessor scientific SHA mismatch")
    if candidate.get("simulation_only") is not True:
        raise RuntimeError("Phase 14 predecessor must remain simulation-only")
    if candidate.get("safety_acceptance") is not False:
        raise RuntimeError("Phase 14 predecessor safety boundary mismatch")
    if candidate.get("controller_tuning_allowed") is not False:
        raise RuntimeError("Phase 14 predecessor controller boundary mismatch")
    return candidate


def _finite_upper_quantile(values: np.ndarray, q: float) -> float:
    x = np.asarray(values, dtype=float)
    if x.ndim != 1 or x.size == 0 or not np.all(np.isfinite(x)):
        raise RuntimeError("Phase 14 conformal score vector must be finite and nonempty")
    if not (0.0 < q < 1.0):
        raise RuntimeError("Phase 14 conformal quantile must be in (0,1)")
    x = np.sort(x)
    rank = min(x.size, int(math.ceil((x.size + 1) * q)))
    return float(x[rank - 1])


def _signed_errors(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    lat = (
        df["p14_estimate_lateral_x_m"].to_numpy(float)
        - df["truth_lateral_x_m"].to_numpy(float)
    )
    alt = (
        df["p14_estimate_altitude_m"].to_numpy(float)
        - df["truth_altitude_m"].to_numpy(float)
    )
    return lat, alt


def _transition_table(df: pd.DataFrame, phase12_candidate: dict[str, object]) -> pd.DataFrame:
    required = {
        "sequence_id",
        "frame_index",
        "truth_visible",
        "p14_available",
        "p14_estimate_lateral_x_m",
        "p14_estimate_altitude_m",
        "truth_lateral_x_m",
        "truth_altitude_m",
    }
    missing = required.difference(df.columns)
    if missing:
        raise RuntimeError(f"Phase 14 event missing columns: {sorted(missing)}")

    work = df.copy(deep=True)
    work["phase14_available"] = v1.p11._available(work).astype(bool)
    lat, alt = _signed_errors(work)
    work["phase14_error_lateral_m"] = lat
    work["phase14_error_altitude_m"] = alt
    work["phase14_hw_lateral_m"] = v3._halfwidths(work, phase12_candidate, "lateral", 0.95)
    work["phase14_hw_altitude_m"] = v3._halfwidths(work, phase12_candidate, "altitude", 0.95)

    rows: list[dict[str, object]] = []
    for sequence_id, group in work.groupby("sequence_id", sort=False):
        g = group.sort_values("frame_index", kind="stable")
        idx = g.index.to_numpy()
        if len(idx) < 2:
            continue
        for j in range(len(idx) - 1):
            i0 = idx[j]
            i1 = idx[j + 1]
            f0 = int(work.at[i0, "frame_index"])
            f1 = int(work.at[i1, "frame_index"])
            if f1 != f0 + 1:
                continue
            if not bool(work.at[i0, "phase14_available"]) or not bool(work.at[i1, "phase14_available"]):
                continue
            e0_lat = float(work.at[i0, "phase14_error_lateral_m"])
            e1_lat = float(work.at[i1, "phase14_error_lateral_m"])
            e0_alt = float(work.at[i0, "phase14_error_altitude_m"])
            e1_alt = float(work.at[i1, "phase14_error_altitude_m"])
            hw_lat = float(work.at[i0, "phase14_hw_lateral_m"])
            hw_alt = float(work.at[i0, "phase14_hw_altitude_m"])
            values = (e0_lat, e1_lat, e0_alt, e1_alt, hw_lat, hw_alt)
            if not all(np.isfinite(v) for v in values):
                continue
            rows.append(
                {
                    "sequence_id": str(sequence_id),
                    "frame_index": f0,
                    "next_frame_index": f1,
                    "e0_lateral_m": e0_lat,
                    "e1_lateral_m": e1_lat,
                    "e0_altitude_m": e0_alt,
                    "e1_altitude_m": e1_alt,
                    "hw_lateral_m": hw_lat,
                    "hw_altitude_m": hw_alt,
                    "inside_lateral": abs(e0_lat) <= RECOVERABLE_HALF_WIDTH_M["lateral"],
                    "inside_altitude": abs(e0_alt) <= RECOVERABLE_HALF_WIDTH_M["altitude"],
                }
            )
    out = pd.DataFrame(rows)
    if out.empty:
        raise RuntimeError("Phase 14 produced no adjacent usable transitions")
    out["inside_box"] = out["inside_lateral"].astype(bool) & out["inside_altitude"].astype(bool)
    return out


def _fit_axis(transitions: pd.DataFrame, axis: str) -> dict[str, object]:
    r = float(RECOVERABLE_HALF_WIDTH_M[axis])
    d = transitions[transitions[f"inside_{axis}"].astype(bool)].copy()
    if len(d) < 100:
        raise RuntimeError(f"Phase 14 underpowered fit transitions for {axis}: {len(d)}")
    e0 = d[f"e0_{axis}_m"].to_numpy(float)
    e1 = d[f"e1_{axis}_m"].to_numpy(float)
    denominator = float(np.dot(e0, e0))
    if not np.isfinite(denominator) or denominator <= 1.0e-12:
        raise RuntimeError(f"Phase 14 degenerate OLS denominator for {axis}")
    a = float(np.dot(e0, e1) / denominator)
    if not np.isfinite(a) or abs(a) >= 1.0:
        raise RuntimeError(f"Phase 14 non-contractive fitted surrogate for {axis}: {a}")

    residual = e1 - a * e0
    hw = d[f"hw_{axis}_m"].to_numpy(float)
    if not np.all(np.isfinite(hw)) or np.any(hw < 0.0):
        raise RuntimeError(f"Phase 14 invalid Phase 12 half-widths for {axis}")
    score = np.abs(residual) / np.maximum(hw, HALFWIDTH_FLOOR_M)
    gamma = _finite_upper_quantile(score, NORMALIZED_RESIDUAL_QUANTILE)
    if not np.isfinite(gamma) or gamma <= 0.0:
        raise RuntimeError(f"Phase 14 invalid normalized-residual multiplier for {axis}: {gamma}")

    contraction_budget = (1.0 - abs(a)) * r
    h_cap = RESERVE_FRACTION * contraction_budget / gamma
    disturbance_at_cap = gamma * h_cap
    image = abs(a) * r + disturbance_at_cap
    margin = r - image
    if not np.isfinite(h_cap) or h_cap <= 0.0:
        raise RuntimeError(f"Phase 14 invalid uncertainty cap for {axis}: {h_cap}")
    if image > r + 1.0e-12 or margin < -1.0e-12:
        raise RuntimeError(f"Phase 14 analytic invariance construction failed for {axis}")

    return {
        "a": a,
        "abs_a": abs(a),
        "fit_rows": int(len(d)),
        "normalized_residual_quantile": NORMALIZED_RESIDUAL_QUANTILE,
        "gamma": gamma,
        "recoverable_half_width_m": r,
        "contraction_budget_m": contraction_budget,
        "reserve_fraction": RESERVE_FRACTION,
        "halfwidth_cap_m": h_cap,
        "disturbance_bound_at_cap_m": disturbance_at_cap,
        "one_step_image_half_width_m": image,
        "analytic_margin_m": margin,
        "fit_normalized_residual_coverage": float(np.mean(np.abs(residual) <= gamma * hw)),
    }


def _build_bridge_candidate(
    phase12_candidate_path: Path,
    scientific_git_sha: str,
) -> tuple[dict[str, object], pd.DataFrame]:
    phase12_candidate = _validate_phase12_candidate(phase12_candidate_path)
    strata = _strata(FIT_FAMILIES)
    fit_event = v1._event(
        "phase14_surrogate_fit",
        FIT_SEED,
        FIT_FAMILIES,
        FIT_DOMAINS,
        strata,
        phase12_candidate,
    )
    transitions = _transition_table(fit_event, phase12_candidate)
    axis_models = {
        axis: _fit_axis(transitions, axis) for axis in ("lateral", "altitude")
    }
    candidate = {
        "schema": BRIDGE_SCHEMA,
        "method": "diagonal_error_surrogate_phase12_halfwidth_normalized_disturbance",
        "phase14_name": PHASE14_NAME,
        "scientific_git_sha": scientific_git_sha,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "phase12_candidate_sha256": FROZEN_PHASE12_CANDIDATE_SHA256,
        "phase12_scientific_sha": FROZEN_PHASE12_SCIENTIFIC_SHA,
        "phase13c_predecessor_head": "8aa2f7c274b6824b765e7a46e2d9ec4c4767e635",
        "recoverable_set_half_width_m": RECOVERABLE_HALF_WIDTH_M,
        "reserve_fraction": RESERVE_FRACTION,
        "normalized_residual_quantile": NORMALIZED_RESIDUAL_QUANTILE,
        "fit_evidence": {
            "seed": FIT_SEED,
            "families": list(FIT_FAMILIES),
            "domains": list(FIT_DOMAINS),
            "transition_rows": int(len(transitions)),
        },
        "axis_models": axis_models,
        "latency_challenge": {
            "profile": LATENCY_PROFILE,
            "base_domain": LATENCY_BASE_DOMAIN,
        },
    }
    return candidate, transitions


def _validate_bridge_candidate(path: Path) -> dict[str, object]:
    candidate = json.loads(path.read_text(encoding="utf-8"))
    if candidate.get("schema") != BRIDGE_SCHEMA:
        raise RuntimeError("Phase 14 bridge candidate schema mismatch")
    if candidate.get("phase12_candidate_sha256") != FROZEN_PHASE12_CANDIDATE_SHA256:
        raise RuntimeError("Phase 14 bridge predecessor digest mismatch")
    if candidate.get("recoverable_set_half_width_m") != RECOVERABLE_HALF_WIDTH_M:
        raise RuntimeError("Phase 14 recoverable set changed")
    if candidate.get("fit_evidence", {}).get("seed") != FIT_SEED:
        raise RuntimeError("Phase 14 fit seed mismatch")
    if candidate.get("fit_evidence", {}).get("families") != list(FIT_FAMILIES):
        raise RuntimeError("Phase 14 fit families mismatch")
    if candidate.get("simulation_only") is not True:
        raise RuntimeError("Phase 14 simulation boundary mismatch")
    if candidate.get("safety_acceptance") is not False:
        raise RuntimeError("Phase 14 safety boundary mismatch")
    if candidate.get("controller_tuning_allowed") is not False:
        raise RuntimeError("Phase 14 controller boundary mismatch")
    for axis in ("lateral", "altitude"):
        model = candidate["axis_models"][axis]
        if not np.isfinite(float(model["a"])) or abs(float(model["a"])) >= 1.0:
            raise RuntimeError(f"Phase 14 bridge is non-contractive for {axis}")
        if float(model["gamma"]) <= 0.0 or float(model["halfwidth_cap_m"]) <= 0.0:
            raise RuntimeError(f"Phase 14 bridge has invalid bound for {axis}")
    return candidate


def _event_for_stage(
    stage: str,
    phase12_candidate: dict[str, object],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    seed = STAGE_SEEDS[stage]
    families = STAGE_FAMILIES[stage]
    strata = _strata(families)
    natural = v1._event(
        f"phase14_{stage}_natural",
        seed,
        families,
        STAGE_DOMAINS[stage],
        strata,
        phase12_candidate,
    )
    latency_base = v1._event(
        f"phase14_{stage}_latency_base",
        seed,
        families,
        (LATENCY_BASE_DOMAIN,),
        strata,
        phase12_candidate,
    )
    latency = p13.apply_shift(latency_base, LATENCY_PROFILE, seed)
    return natural, latency


def _score_cohort(
    transitions: pd.DataFrame,
    bridge_candidate: dict[str, object],
) -> dict[str, object]:
    eligible = transitions[transitions["inside_box"].astype(bool)].copy()
    if eligible.empty:
        raise RuntimeError("Phase 14 cohort has no transitions beginning inside recoverable box")

    lat_cap = float(bridge_candidate["axis_models"]["lateral"]["halfwidth_cap_m"])
    alt_cap = float(bridge_candidate["axis_models"]["altitude"]["halfwidth_cap_m"])
    eligible["admitted"] = (
        (eligible["hw_lateral_m"].to_numpy(float) <= lat_cap)
        & (eligible["hw_altitude_m"].to_numpy(float) <= alt_cap)
    )
    admitted = eligible[eligible["admitted"].astype(bool)].copy()
    if admitted.empty:
        return {
            "eligible_transitions": int(len(eligible)),
            "admitted_transitions": 0,
            "admission_fraction": 0.0,
            "axes": {
                axis: {
                    "normalized_residual_coverage": 0.0,
                    "empirical_next_state_containment": 0.0,
                    "rows": 0,
                }
                for axis in ("lateral", "altitude")
            },
        }

    axes: dict[str, object] = {}
    for axis in ("lateral", "altitude"):
        model = bridge_candidate["axis_models"][axis]
        a = float(model["a"])
        gamma = float(model["gamma"])
        r = float(model["recoverable_half_width_m"])
        e0 = admitted[f"e0_{axis}_m"].to_numpy(float)
        e1 = admitted[f"e1_{axis}_m"].to_numpy(float)
        hw = admitted[f"hw_{axis}_m"].to_numpy(float)
        residual = e1 - a * e0
        envelope = gamma * hw
        axes[axis] = {
            "rows": int(len(admitted)),
            "normalized_residual_coverage": float(np.mean(np.abs(residual) <= envelope)),
            "empirical_next_state_containment": float(np.mean(np.abs(e1) <= r)),
            "p95_normalized_residual": float(np.percentile(np.abs(residual) / np.maximum(hw, HALFWIDTH_FLOOR_M), 95)),
            "p99_normalized_residual": float(np.percentile(np.abs(residual) / np.maximum(hw, HALFWIDTH_FLOOR_M), 99)),
            "p95_next_abs_error_m": float(np.percentile(np.abs(e1), 95)),
        }

    return {
        "eligible_transitions": int(len(eligible)),
        "admitted_transitions": int(len(admitted)),
        "admission_fraction": float(len(admitted) / len(eligible)),
        "axes": axes,
    }


def _analytic_gate(candidate: dict[str, object]) -> tuple[bool, dict[str, object]]:
    detail: dict[str, object] = {}
    passed = True
    for axis in ("lateral", "altitude"):
        model = candidate["axis_models"][axis]
        r = float(model["recoverable_half_width_m"])
        image = float(model["abs_a"]) * r + float(model["gamma"]) * float(model["halfwidth_cap_m"])
        margin = r - image
        axis_pass = bool(image <= r + 1.0e-12 and margin >= -1.0e-12)
        passed = passed and axis_pass
        detail[axis] = {"image_half_width_m": image, "margin_m": margin, "pass": axis_pass}
    return bool(passed), detail


def _evaluate_stage(
    stage: str,
    phase12_candidate_path: Path,
    bridge_candidate_path: Path,
    scientific_git_sha: str,
) -> tuple[dict[str, object], pd.DataFrame, pd.DataFrame]:
    phase12_candidate = _validate_phase12_candidate(phase12_candidate_path)
    bridge = _validate_bridge_candidate(bridge_candidate_path)
    if bridge.get("scientific_git_sha") != scientific_git_sha:
        raise RuntimeError("Phase 14 downstream scientific SHA mismatch")

    natural_df, latency_df = _event_for_stage(stage, phase12_candidate)
    natural_transitions = _transition_table(natural_df, phase12_candidate)
    latency_transitions = _transition_table(latency_df, phase12_candidate)
    natural = _score_cohort(natural_transitions, bridge)
    latency = _score_cohort(latency_transitions, bridge)

    analytic_pass, analytic_detail = _analytic_gate(bridge)
    models = bridge["axis_models"]
    contractive_pass = all(
        np.isfinite(float(models[a]["a"]))
        and abs(float(models[a]["a"])) < 1.0
        and float(models[a]["gamma"]) > 0.0
        and float(models[a]["halfwidth_cap_m"]) > 0.0
        for a in ("lateral", "altitude")
    )

    natural_envelope_pass = all(
        float(natural["axes"][a]["normalized_residual_coverage"])
        >= GATE_THRESHOLDS["natural_normalized_residual_coverage"]
        for a in ("lateral", "altitude")
    )
    natural_containment_pass = all(
        float(natural["axes"][a]["empirical_next_state_containment"])
        >= GATE_THRESHOLDS["natural_empirical_containment"]
        for a in ("lateral", "altitude")
    )
    natural_admission_pass = float(natural["admission_fraction"]) >= GATE_THRESHOLDS["natural_admission_fraction"]

    latency_envelope_pass = all(
        float(latency["axes"][a]["normalized_residual_coverage"])
        >= GATE_THRESHOLDS["latency_normalized_residual_coverage"]
        for a in ("lateral", "altitude")
    )
    latency_containment_pass = all(
        float(latency["axes"][a]["empirical_next_state_containment"])
        >= GATE_THRESHOLDS["latency_empirical_containment"]
        for a in ("lateral", "altitude")
    )
    latency_admission_pass = float(latency["admission_fraction"]) >= GATE_THRESHOLDS["latency_admission_fraction"]

    gates = {
        "p14_1_candidate_and_lineage_integrity": True,
        "p14_2_contractive_fitted_surrogate": bool(contractive_pass),
        "p14_3_conditional_analytic_rpi": bool(analytic_pass),
        "p14_4_natural_normalized_residual_envelope": bool(natural_envelope_pass),
        "p14_5_natural_empirical_containment": bool(natural_containment_pass),
        "p14_6_natural_nontrivial_admission": bool(natural_admission_pass),
        "p14_7_latency_normalized_residual_envelope": bool(latency_envelope_pass),
        "p14_8_latency_empirical_containment": bool(latency_containment_pass),
        "p14_9_latency_nonvacuous_admission": bool(latency_admission_pass),
        "p14_10_zero_adaptation_and_claim_boundary": True,
    }
    result = {
        "schema": f"aegisland.phase14.uncertainty-recoverability.{stage}-result.v1",
        "phase14_name": PHASE14_NAME,
        "stage": stage,
        "evaluated_seed_seen_after_run": STAGE_SEEDS[stage],
        "families": list(STAGE_FAMILIES[stage]),
        "natural_domains": list(STAGE_DOMAINS[stage]),
        "latency_profile": LATENCY_PROFILE,
        "latency_base_domain": LATENCY_BASE_DOMAIN,
        "scientific_git_sha": scientific_git_sha,
        "phase12_candidate_sha256": FROZEN_PHASE12_CANDIDATE_SHA256,
        "bridge_candidate_sha256": _sha256_file(bridge_candidate_path),
        "recoverable_set_half_width_m": RECOVERABLE_HALF_WIDTH_M,
        "axis_models": bridge["axis_models"],
        "analytic_rpi": analytic_detail,
        "natural": natural,
        "latency": latency,
        "gate_thresholds": GATE_THRESHOLDS,
        "gates": gates,
        "phase14_pass": bool(all(gates.values())),
        "zero_adaptation": True,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "interpretation": "conditional surrogate invariance under frozen uncertainty-admission rule; not a physical-flight or full-simulator safety proof",
    }
    return result, natural_transitions, latency_transitions


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=PHASE14_NAME)
    p.add_argument("--stage", choices=("fit", "dev", "transfer", "validation", "final"), required=True)
    p.add_argument("--phase12-candidate", type=Path, required=True)
    p.add_argument("--bridge-candidate", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--git-sha", required=True)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    if args.stage == "fit":
        candidate, transitions = _build_bridge_candidate(args.phase12_candidate, args.git_sha)
        candidate_path = args.out / "bridge_candidate.json"
        candidate_path.write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        transitions.to_csv(args.out / "fit_transitions.csv", index=False)
        print("PHASE14_BRIDGE_CANDIDATE_SHA256=" + _sha256_file(candidate_path))
        print("PHASE14_FIT_AXIS_MODELS=" + json.dumps(candidate["axis_models"], sort_keys=True))
        return

    if args.bridge_candidate is None:
        raise SystemExit("--bridge-candidate is required for Phase 14 evaluation stages")

    result, natural_transitions, latency_transitions = _evaluate_stage(
        args.stage,
        args.phase12_candidate,
        args.bridge_candidate,
        args.git_sha,
    )
    result_path = args.out / f"{args.stage}_result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    natural_transitions.to_csv(args.out / f"{args.stage}_natural_transitions.csv", index=False)
    latency_transitions.to_csv(args.out / f"{args.stage}_latency_transitions.csv", index=False)
    (args.out / "bridge_candidate.json").write_text(
        args.bridge_candidate.read_text(encoding="utf-8"), encoding="utf-8"
    )
    print(f"PHASE14_{args.stage.upper()}_RESULT_SHA256=" + _sha256_file(result_path))
    print(f"PHASE14_{args.stage.upper()}_PASS=" + str(bool(result["phase14_pass"])).lower())
    print(json.dumps(result["gates"], indent=2, sort_keys=True))
    print(json.dumps({"natural": result["natural"], "latency": result["latency"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
