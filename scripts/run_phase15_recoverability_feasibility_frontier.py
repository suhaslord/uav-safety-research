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
    from scripts import run_phase13_external_validity_gauntlet as p13
    from scripts import run_phase14_uncertainty_recoverability_bridge as p14
except ModuleNotFoundError:
    import run_phase12_adaptive_normalized_conformal as v1
    import run_phase13_external_validity_gauntlet as p13
    import run_phase14_uncertainty_recoverability_bridge as p14

PHASE15_NAME = "Recoverability Feasibility Frontier"
FRONTIER_SCHEMA = "aegisland.phase15.recoverability-feasibility.frontier-candidate.v1"
FROZEN_PHASE12_CANDIDATE_SHA256 = p14.FROZEN_PHASE12_CANDIDATE_SHA256
FROZEN_PHASE14_BRIDGE_SHA256 = "0443d4e45a1966c77544c5c9965de8caec6e622c79ef8c2ce47aee82a3c95981"
FROZEN_PHASE14_SCIENTIFIC_SHA = "a80cd02d0781e7b3dde9ea523b2fe17ecd44002c"
REFERENCE_HALF_WIDTH_M = {"lateral": 0.30, "altitude": 0.85}
QUANTILES = (0.90, 0.95, 0.975, 0.99)
LATENCY_PROFILE = "fixed_latency_2f"
LATENCY_BASE_DOMAIN = "small_scale+temporal_dropout"

STAGE_SEEDS = {
    "dev": 1515151,
    "transfer": 1515152,
    "validation": 1515153,
    "final": 1515154,
}
STAGE_FAMILIES = {
    "dev": tuple(range(1617, 1641)),
    "transfer": tuple(range(1641, 1665)),
    "validation": tuple(range(1665, 1689)),
    "final": tuple(range(1689, 1713)),
}
STAGE_DOMAINS = {
    "dev": v1.DEV_DOMAINS,
    "transfer": v1.TRANSFER_DOMAINS,
    "validation": v1.VALIDATION_DOMAINS,
    "final": v1.FINAL_DOMAINS,
}
NATURAL_COVERAGE_FLOORS = {0.90: 0.87, 0.95: 0.92, 0.975: 0.945, 0.99: 0.96}
LATENCY_COVERAGE_FLOORS = {0.90: 0.85, 0.95: 0.90, 0.975: 0.925, 0.99: 0.94}
STATE_CONTAINMENT_FLOOR = 0.25


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _qkey(q: float) -> str:
    return f"{q:.3f}".rstrip("0").rstrip(".")


def _finite_conformal(values: np.ndarray, q: float) -> float:
    x = np.asarray(values, dtype=float)
    if x.ndim != 1 or x.size == 0 or not np.all(np.isfinite(x)):
        raise RuntimeError("Phase 15 residual vector must be finite and nonempty")
    x = np.sort(x)
    rank = min(x.size, int(math.ceil((x.size + 1) * q)))
    return float(x[rank - 1])


def _strata(families: tuple[int, ...]) -> dict[str, tuple[int, ...]]:
    if len(families) != 24:
        raise RuntimeError("Phase 15 expects exactly 24 families per evaluation stage")
    names = ("bootstrap5", "gap3", "gap7", "gap12")
    return {name: families[i * 6 : (i + 1) * 6] for i, name in enumerate(names)}


def _validate_phase14_bridge(path: Path) -> dict[str, object]:
    if _sha256_file(path) != FROZEN_PHASE14_BRIDGE_SHA256:
        raise RuntimeError("Phase 15 requires the exact frozen Phase 14 bridge candidate")
    candidate = json.loads(path.read_text(encoding="utf-8"))
    if candidate.get("schema") != p14.BRIDGE_SCHEMA:
        raise RuntimeError("Phase 15 Phase 14 bridge schema mismatch")
    if candidate.get("scientific_git_sha") != FROZEN_PHASE14_SCIENTIFIC_SHA:
        raise RuntimeError("Phase 15 Phase 14 scientific SHA mismatch")
    if candidate.get("recoverable_set_half_width_m") != REFERENCE_HALF_WIDTH_M:
        raise RuntimeError("Phase 15 historical reference box mismatch")
    return candidate


def _build_frontier_candidate(
    bridge_path: Path,
    fit_transitions_path: Path,
    scientific_git_sha: str,
) -> dict[str, object]:
    bridge = _validate_phase14_bridge(bridge_path)
    transitions = pd.read_csv(fit_transitions_path)
    required = {
        "inside_lateral", "inside_altitude",
        "e0_lateral_m", "e1_lateral_m",
        "e0_altitude_m", "e1_altitude_m",
        "hw_lateral_m", "hw_altitude_m",
    }
    missing = required.difference(transitions.columns)
    if missing:
        raise RuntimeError(f"Phase 15 Phase 14 fit transitions missing: {sorted(missing)}")

    axes: dict[str, object] = {}
    for axis in ("lateral", "altitude"):
        model = bridge["axis_models"][axis]
        a = float(model["a"])
        if not np.isfinite(a) or abs(a) >= 1.0:
            raise RuntimeError(f"Phase 15 requires contractive frozen a for {axis}")
        d = transitions[transitions[f"inside_{axis}"].astype(bool)].copy()
        if len(d) < 100:
            raise RuntimeError(f"Phase 15 underpowered frozen fit rows for {axis}")
        e0 = d[f"e0_{axis}_m"].to_numpy(float)
        e1 = d[f"e1_{axis}_m"].to_numpy(float)
        residual = np.abs(e1 - a * e0)
        bounds: dict[str, float] = {}
        rmins: dict[str, float] = {}
        for q in QUANTILES:
            key = _qkey(q)
            wq = _finite_conformal(residual, q)
            rmin = wq / (1.0 - abs(a))
            if not np.isfinite(wq) or wq <= 0.0 or not np.isfinite(rmin) or rmin <= 0.0:
                raise RuntimeError(f"Phase 15 invalid frontier value for {axis}/{q}")
            bounds[key] = wq
            rmins[key] = rmin
        if list(bounds.values()) != sorted(bounds.values()):
            raise RuntimeError(f"Phase 15 nonmonotone residual frontier for {axis}")
        if list(rmins.values()) != sorted(rmins.values()):
            raise RuntimeError(f"Phase 15 nonmonotone RPI frontier for {axis}")
        axes[axis] = {
            "a": a,
            "abs_a": abs(a),
            "fit_rows": int(len(d)),
            "residual_bounds_m": bounds,
            "minimal_rpi_half_width_m": rmins,
            "reference_half_width_m": float(REFERENCE_HALF_WIDTH_M[axis]),
            "q90_reference_ratio": float(rmins[_qkey(0.90)] / REFERENCE_HALF_WIDTH_M[axis]),
        }

    return {
        "schema": FRONTIER_SCHEMA,
        "phase15_name": PHASE15_NAME,
        "scientific_git_sha": scientific_git_sha,
        "source_phase14_bridge_sha256": FROZEN_PHASE14_BRIDGE_SHA256,
        "source_phase14_scientific_sha": FROZEN_PHASE14_SCIENTIFIC_SHA,
        "source_phase14_fit_run": 34010431456,
        "source_phase14_fit_seed": 1414140,
        "source_phase14_fit_families": list(range(1489, 1521)),
        "phase12_candidate_sha256": FROZEN_PHASE12_CANDIDATE_SHA256,
        "reference_half_width_m": REFERENCE_HALF_WIDTH_M,
        "quantiles": list(QUANTILES),
        "axes": axes,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "interpretation": "residual-based surrogate RPI feasibility frontier; not a full-simulator or physical-flight invariance proof",
    }


def _validate_frontier(path: Path) -> dict[str, object]:
    candidate = json.loads(path.read_text(encoding="utf-8"))
    if candidate.get("schema") != FRONTIER_SCHEMA:
        raise RuntimeError("Phase 15 frontier candidate schema mismatch")
    if candidate.get("source_phase14_bridge_sha256") != FROZEN_PHASE14_BRIDGE_SHA256:
        raise RuntimeError("Phase 15 frontier Phase 14 bridge mismatch")
    if candidate.get("phase12_candidate_sha256") != FROZEN_PHASE12_CANDIDATE_SHA256:
        raise RuntimeError("Phase 15 frontier Phase 12 candidate mismatch")
    if candidate.get("reference_half_width_m") != REFERENCE_HALF_WIDTH_M:
        raise RuntimeError("Phase 15 frontier reference box mismatch")
    if candidate.get("quantiles") != list(QUANTILES):
        raise RuntimeError("Phase 15 frontier quantile list mismatch")
    if candidate.get("simulation_only") is not True or candidate.get("safety_acceptance") is not False:
        raise RuntimeError("Phase 15 frontier claim boundary mismatch")
    if candidate.get("controller_tuning_allowed") is not False:
        raise RuntimeError("Phase 15 frontier controller boundary mismatch")
    for axis in ("lateral", "altitude"):
        model = candidate["axes"][axis]
        if abs(float(model["a"])) >= 1.0:
            raise RuntimeError(f"Phase 15 noncontractive frozen model for {axis}")
        vals = [float(model["residual_bounds_m"][_qkey(q)]) for q in QUANTILES]
        rvals = [float(model["minimal_rpi_half_width_m"][_qkey(q)]) for q in QUANTILES]
        if vals != sorted(vals) or rvals != sorted(rvals):
            raise RuntimeError(f"Phase 15 nonmonotone frozen frontier for {axis}")
    return candidate


def _generate_stage_events(stage: str, phase12_candidate: dict[str, object]) -> tuple[pd.DataFrame, pd.DataFrame]:
    seed = STAGE_SEEDS[stage]
    families = STAGE_FAMILIES[stage]
    strata = _strata(families)
    natural = v1._event(
        f"phase15_{stage}_natural",
        seed,
        families,
        STAGE_DOMAINS[stage],
        strata,
        phase12_candidate,
    )
    latency_base = v1._event(
        f"phase15_{stage}_latency_base",
        seed,
        families,
        (LATENCY_BASE_DOMAIN,),
        strata,
        phase12_candidate,
    )
    latency = p13.apply_shift(latency_base, LATENCY_PROFILE, seed)
    return natural, latency


def _score_cohort(transitions: pd.DataFrame, frontier: dict[str, object]) -> dict[str, object]:
    eligible = transitions[transitions["inside_box"].astype(bool)].copy()
    if eligible.empty:
        raise RuntimeError("Phase 15 cohort has no transitions beginning inside reference box")

    state_contained = (
        (eligible["hw_lateral_m"].to_numpy(float) <= REFERENCE_HALF_WIDTH_M["lateral"])
        & (eligible["hw_altitude_m"].to_numpy(float) <= REFERENCE_HALF_WIDTH_M["altitude"])
    )

    axes: dict[str, object] = {}
    for axis in ("lateral", "altitude"):
        model = frontier["axes"][axis]
        a = float(model["a"])
        e0 = eligible[f"e0_{axis}_m"].to_numpy(float)
        e1 = eligible[f"e1_{axis}_m"].to_numpy(float)
        residual = np.abs(e1 - a * e0)
        frozen_coverage: dict[str, float] = {}
        fresh_bounds: dict[str, float] = {}
        fresh_rmins: dict[str, float] = {}
        for q in QUANTILES:
            key = _qkey(q)
            bound = float(model["residual_bounds_m"][key])
            frozen_coverage[key] = float(np.mean(residual <= bound))
            fresh = _finite_conformal(residual, q)
            fresh_bounds[key] = fresh
            fresh_rmins[key] = fresh / (1.0 - abs(a))
        axes[axis] = {
            "rows": int(len(eligible)),
            "frozen_residual_coverage": frozen_coverage,
            "fresh_diagnostic_residual_bounds_m": fresh_bounds,
            "fresh_diagnostic_minimal_rpi_half_width_m": fresh_rmins,
            "fresh_q90_reference_ratio": float(fresh_rmins[_qkey(0.90)] / REFERENCE_HALF_WIDTH_M[axis]),
        }

    return {
        "eligible_transitions": int(len(eligible)),
        "state_uncertainty_contained_rows": int(np.sum(state_contained)),
        "state_uncertainty_containment_fraction": float(np.mean(state_contained)),
        "axes": axes,
    }


def _coverage_gate(cohort: dict[str, object], floors: dict[float, float]) -> bool:
    for axis in ("lateral", "altitude"):
        coverage = cohort["axes"][axis]["frozen_residual_coverage"]
        for q in QUANTILES:
            if float(coverage[_qkey(q)]) < float(floors[q]):
                return False
    return True


def _q90_infeasible(cohort: dict[str, object]) -> bool:
    return all(
        float(cohort["axes"][axis]["fresh_diagnostic_minimal_rpi_half_width_m"][_qkey(0.90)])
        > REFERENCE_HALF_WIDTH_M[axis]
        for axis in ("lateral", "altitude")
    )


def _direction_stable(cohort: dict[str, object]) -> bool:
    for axis in ("lateral", "altitude"):
        r = cohort["axes"][axis]["fresh_diagnostic_minimal_rpi_half_width_m"]
        vals = [float(r[_qkey(q)]) for q in QUANTILES]
        if vals != sorted(vals):
            return False
    return True


def _evaluate(
    stage: str,
    phase12_candidate_path: Path,
    frontier_path: Path,
    scientific_git_sha: str,
) -> tuple[dict[str, object], pd.DataFrame, pd.DataFrame]:
    phase12_candidate = p14._validate_phase12_candidate(phase12_candidate_path)
    frontier = _validate_frontier(frontier_path)
    if frontier.get("scientific_git_sha") != scientific_git_sha:
        raise RuntimeError("Phase 15 scientific SHA mismatch")

    natural_event, latency_event = _generate_stage_events(stage, phase12_candidate)
    natural_transitions = p14._transition_table(natural_event, phase12_candidate)
    latency_transitions = p14._transition_table(latency_event, phase12_candidate)
    natural = _score_cohort(natural_transitions, frontier)
    latency = _score_cohort(latency_transitions, frontier)

    gates = {
        "f15_1_lineage_integrity": True,
        "f15_2_frontier_construction_integrity": True,
        "f15_3_natural_residual_envelope_replication": _coverage_gate(natural, NATURAL_COVERAGE_FLOORS),
        "f15_4_natural_q90_infeasibility_replication": _q90_infeasible(natural),
        "f15_5_natural_state_uncertainty_nontrivial": float(natural["state_uncertainty_containment_fraction"]) >= STATE_CONTAINMENT_FLOOR,
        "f15_6_latency_residual_envelope_replication": _coverage_gate(latency, LATENCY_COVERAGE_FLOORS),
        "f15_7_latency_q90_infeasibility_replication": _q90_infeasible(latency),
        "f15_8_latency_state_uncertainty_nontrivial": float(latency["state_uncertainty_containment_fraction"]) >= STATE_CONTAINMENT_FLOOR,
        "f15_9_frontier_direction_stable": _direction_stable(natural) and _direction_stable(latency),
        "f15_10_zero_adaptation_and_claim_boundary": True,
    }

    result = {
        "schema": f"aegisland.phase15.recoverability-feasibility.{stage}-result.v1",
        "phase15_name": PHASE15_NAME,
        "stage": stage,
        "evaluated_seed_seen_after_run": STAGE_SEEDS[stage],
        "families": list(STAGE_FAMILIES[stage]),
        "natural_domains": list(STAGE_DOMAINS[stage]),
        "latency_profile": LATENCY_PROFILE,
        "latency_base_domain": LATENCY_BASE_DOMAIN,
        "scientific_git_sha": scientific_git_sha,
        "phase12_candidate_sha256": FROZEN_PHASE12_CANDIDATE_SHA256,
        "frontier_candidate_sha256": _sha256_file(frontier_path),
        "reference_half_width_m": REFERENCE_HALF_WIDTH_M,
        "quantiles": list(QUANTILES),
        "natural": natural,
        "latency": latency,
        "natural_coverage_floors": {_qkey(k): v for k, v in NATURAL_COVERAGE_FLOORS.items()},
        "latency_coverage_floors": {_qkey(k): v for k, v in LATENCY_COVERAGE_FLOORS.items()},
        "state_uncertainty_containment_floor": STATE_CONTAINMENT_FLOOR,
        "gates": gates,
        "phase15_pass": bool(all(gates.values())),
        "phase14_failure_preserved": True,
        "zero_adaptation": True,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "interpretation": "replication of surrogate recoverability feasibility frontier; not a claim that the historical box is invariant",
    }
    return result, natural_transitions, latency_transitions


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=PHASE15_NAME)
    p.add_argument("--stage", choices=("freeze", "dev", "transfer", "validation", "final"), required=True)
    p.add_argument("--phase14-bridge", type=Path)
    p.add_argument("--phase14-fit-transitions", type=Path)
    p.add_argument("--phase12-candidate", type=Path)
    p.add_argument("--frontier", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--git-sha", required=True)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    if args.stage == "freeze":
        if args.phase14_bridge is None or args.phase14_fit_transitions is None:
            raise SystemExit("--phase14-bridge and --phase14-fit-transitions are required for freeze")
        candidate = _build_frontier_candidate(args.phase14_bridge, args.phase14_fit_transitions, args.git_sha)
        path = args.out / "frontier_candidate.json"
        path.write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("PHASE15_FRONTIER_CANDIDATE_SHA256=" + _sha256_file(path))
        print(json.dumps(candidate["axes"], indent=2, sort_keys=True))
        return

    if args.phase12_candidate is None or args.frontier is None:
        raise SystemExit("--phase12-candidate and --frontier are required for evaluation")
    result, natural, latency = _evaluate(args.stage, args.phase12_candidate, args.frontier, args.git_sha)
    result_path = args.out / f"{args.stage}_result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    natural.to_csv(args.out / f"{args.stage}_natural_transitions.csv", index=False)
    latency.to_csv(args.out / f"{args.stage}_latency_transitions.csv", index=False)
    (args.out / "frontier_candidate.json").write_text(args.frontier.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"PHASE15_{args.stage.upper()}_RESULT_SHA256=" + _sha256_file(result_path))
    print(f"PHASE15_{args.stage.upper()}_PASS=" + str(bool(result["phase15_pass"])).lower())
    print(json.dumps(result["gates"], indent=2, sort_keys=True))
    print(json.dumps({"natural": result["natural"], "latency": result["latency"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
