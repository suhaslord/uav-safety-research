from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scripts import run_phase12_adaptive_normalized_conformal as v1
    from scripts import run_phase12_adaptive_normalized_conformal_v3 as v3
    from scripts import run_phase13c_compound_attribution as p13c
    from scripts import run_phase14_uncertainty_recoverability_bridge as p14
    from scripts import run_phase15_recoverability_feasibility_frontier as p15
except ModuleNotFoundError:
    import run_phase12_adaptive_normalized_conformal as v1
    import run_phase12_adaptive_normalized_conformal_v3 as v3
    import run_phase13c_compound_attribution as p13c
    import run_phase14_uncertainty_recoverability_bridge as p14
    import run_phase15_recoverability_feasibility_frontier as p15

PHASE16_NAME = "Matched Latency Level-Error / Local-Dynamics Decomposition"
FROZEN_PHASE12_CANDIDATE_SHA256 = p14.FROZEN_PHASE12_CANDIDATE_SHA256
FROZEN_PHASE14_BRIDGE_SHA256 = p15.FROZEN_PHASE14_BRIDGE_SHA256
REFERENCE_HALF_WIDTH_M = {"lateral": 0.30, "altitude": 0.85}
LATENCY_CONTRAST = "latency_only"
LATENCY_COMPONENTS = frozenset({"A"})
CONTEXTS = {
    "simple": "small_scale+temporal_dropout",
    "hard": "edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout",
}
STAGE_SEEDS = {
    "dev": 1616161,
    "transfer": 1616162,
    "validation": 1616163,
    "final": 1616164,
}
STAGE_FAMILIES = {
    "dev": tuple(range(1713, 1737)),
    "transfer": tuple(range(1737, 1761)),
    "validation": tuple(range(1761, 1785)),
    "final": tuple(range(1785, 1809)),
}


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _strata(families: tuple[int, ...]) -> dict[str, tuple[int, ...]]:
    if len(families) != 24:
        raise RuntimeError("Phase 16 requires 24 families per stage")
    names = ("bootstrap5", "gap3", "gap7", "gap12")
    return {name: families[i * 6 : (i + 1) * 6] for i, name in enumerate(names)}


def _validate_bridge(path: Path) -> dict[str, object]:
    if _sha256_file(path) != FROZEN_PHASE14_BRIDGE_SHA256:
        raise RuntimeError("Phase 16 requires exact frozen Phase 14 bridge candidate")
    bridge = json.loads(path.read_text(encoding="utf-8"))
    if bridge.get("schema") != p14.BRIDGE_SCHEMA:
        raise RuntimeError("Phase 16 Phase 14 bridge schema mismatch")
    if bridge.get("recoverable_set_half_width_m") != REFERENCE_HALF_WIDTH_M:
        raise RuntimeError("Phase 16 historical box mismatch")
    return bridge


def _pair_id(df: pd.DataFrame) -> pd.Series:
    return df["sequence_id"].astype(str) + "|frame:" + df["frame_index"].astype(int).astype(str)


def _generate_context(
    stage: str,
    context: str,
    candidate: dict[str, object],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    seed = STAGE_SEEDS[stage]
    families = STAGE_FAMILIES[stage]
    base = v1._event(
        f"phase16_{stage}_{context}_base",
        seed,
        families,
        (CONTEXTS[context],),
        _strata(families),
        candidate,
    )
    base = base.copy(deep=True)
    base["phase16_pair_id"] = _pair_id(base)
    base["phase16_context"] = context
    base["phase16_latency_applied"] = False

    control = base.copy(deep=True)
    shifted = p13c._apply_component_subset(
        base,
        LATENCY_CONTRAST,
        LATENCY_COMPONENTS,
        seed,
    )
    shifted["phase16_context"] = context
    shifted["phase16_latency_applied"] = True
    return control, shifted


def _available(df: pd.DataFrame) -> np.ndarray:
    return v1.p11._available(df).astype(bool)


def _static_metrics(df: pd.DataFrame, candidate: dict[str, object]) -> dict[str, object]:
    mask = _available(df)
    d = df[mask].copy()
    out: dict[str, object] = {
        "rows": int(len(df)),
        "useful_rows": int(len(d)),
    }
    for axis in ("lateral", "altitude"):
        err = d[f"p14_{axis}_abs_error_m"].to_numpy(float)
        hw = v3._halfwidths(d, candidate, axis, 0.95)
        out[axis] = {
            "median_abs_error_m": float(np.median(err)),
            "p95_abs_error_m": float(np.percentile(err, 95)),
            "coverage95": float(np.mean(err <= hw)),
            "median_halfwidth95_m": float(np.median(hw)),
            "p95_halfwidth95_m": float(np.percentile(hw, 95)),
        }
    return out


def _integrity_and_width_identity(
    control: pd.DataFrame,
    latency: pd.DataFrame,
    candidate: dict[str, object],
) -> dict[str, object]:
    if len(control) != len(latency):
        return {"pass": False, "same_rows": False}
    pair_same = bool(np.array_equal(control["phase16_pair_id"].to_numpy(), latency["phase16_pair_id"].to_numpy()))
    truth_visible_same = bool(np.array_equal(control["truth_visible"].astype(bool).to_numpy(), latency["truth_visible"].astype(bool).to_numpy()))
    available_same = bool(np.array_equal(_available(control), _available(latency)))
    truth_lat_same = bool(np.array_equal(control["truth_lateral_x_m"].to_numpy(float), latency["truth_lateral_x_m"].to_numpy(float), equal_nan=True))
    truth_alt_same = bool(np.array_equal(control["truth_altitude_m"].to_numpy(float), latency["truth_altitude_m"].to_numpy(float), equal_nan=True))

    mask = _available(control) & _available(latency)
    c = control[mask].copy()
    l = latency[mask].copy()
    width_diffs: dict[str, float] = {}
    width_same = True
    for axis in ("lateral", "altitude"):
        cw = v3._halfwidths(c, candidate, axis, 0.95)
        lw = v3._halfwidths(l, candidate, axis, 0.95)
        diff = float(np.max(np.abs(cw - lw))) if len(cw) else float("inf")
        width_diffs[axis] = diff
        width_same = width_same and bool(diff <= 1.0e-12)

    return {
        "same_rows": True,
        "same_pair_ids": pair_same,
        "same_truth_visible": truth_visible_same,
        "same_useful_availability": available_same,
        "same_lateral_truth": truth_lat_same,
        "same_altitude_truth": truth_alt_same,
        "max_halfwidth_abs_diff_m": width_diffs,
        "width_identity_pass": bool(width_same),
        "pass": bool(pair_same and truth_visible_same and available_same and truth_lat_same and truth_alt_same),
    }


def _normalized_sequence_id(values: pd.Series) -> pd.Series:
    return values.astype(str).str.replace("|phase13c:latency_only", "", regex=False)


def _transition_frame(df: pd.DataFrame, candidate: dict[str, object], prefix: str) -> pd.DataFrame:
    t = p14._transition_table(df, candidate).copy()
    t["pair_sequence"] = _normalized_sequence_id(t["sequence_id"])
    keep = [
        "pair_sequence", "frame_index", "inside_box",
        "e0_lateral_m", "e1_lateral_m", "e0_altitude_m", "e1_altitude_m",
    ]
    return t[keep].rename(columns={c: f"{prefix}_{c}" for c in keep if c not in ("pair_sequence", "frame_index")})


def _matched_temporal(
    control: pd.DataFrame,
    latency: pd.DataFrame,
    candidate: dict[str, object],
    bridge: dict[str, object],
) -> dict[str, object]:
    ct = _transition_frame(control, candidate, "control")
    lt = _transition_frame(latency, candidate, "latency")
    m = ct.merge(lt, on=["pair_sequence", "frame_index"], how="inner", validate="one_to_one")
    m = m[m["control_inside_box"].astype(bool) & m["latency_inside_box"].astype(bool)].copy()
    if len(m) < 10:
        raise RuntimeError("Phase 16 matched temporal subset is empty/underpowered")

    axes: dict[str, object] = {}
    for axis in ("lateral", "altitude"):
        frozen_a = float(bridge["axis_models"][axis]["a"])
        axis_result: dict[str, object] = {"frozen_phase14_a": frozen_a}
        vectors: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        for cohort in ("control", "latency"):
            e0 = m[f"{cohort}_e0_{axis}_m"].to_numpy(float)
            e1 = m[f"{cohort}_e1_{axis}_m"].to_numpy(float)
            vectors[cohort] = (e0, e1)
            denom = float(np.dot(e0, e0))
            adiag = float(np.dot(e0, e1) / denom) if denom > 1.0e-12 else float("nan")
            corr = float(np.corrcoef(e0, e1)[0, 1]) if len(e0) > 1 else float("nan")
            increment = np.abs(e1 - e0)
            residual = np.abs(e1 - frozen_a * e0)
            q90_increment = p15._finite_conformal(increment, 0.90)
            q90_residual = p15._finite_conformal(residual, 0.90)
            r90 = q90_residual / (1.0 - abs(frozen_a))
            axis_result[cohort] = {
                "diagnostic_a": adiag,
                "adjacent_error_correlation": corr,
                "q90_abs_increment_m": q90_increment,
                "q90_frozen_residual_m": q90_residual,
                "q90_diagnostic_rpi_half_width_m": r90,
                "median_abs_error_at_transition_start_m": float(np.median(np.abs(e0))),
            }
        c = axis_result["control"]
        l = axis_result["latency"]
        axis_result["latency_minus_control_diagnostic_a"] = float(l["diagnostic_a"] - c["diagnostic_a"])
        axis_result["latency_minus_control_correlation"] = float(l["adjacent_error_correlation"] - c["adjacent_error_correlation"])
        axis_result["increment_q90_ratio"] = float(l["q90_abs_increment_m"] / c["q90_abs_increment_m"])
        axis_result["frozen_residual_q90_ratio"] = float(l["q90_frozen_residual_m"] / c["q90_frozen_residual_m"])
        axis_result["rpi_q90_ratio"] = float(l["q90_diagnostic_rpi_half_width_m"] / c["q90_diagnostic_rpi_half_width_m"])
        axes[axis] = axis_result

    return {"matched_transitions": int(len(m)), "axes": axes}


def _context_result(
    control: pd.DataFrame,
    latency: pd.DataFrame,
    candidate: dict[str, object],
    bridge: dict[str, object],
) -> dict[str, object]:
    integrity = _integrity_and_width_identity(control, latency, candidate)
    control_static = _static_metrics(control, candidate)
    latency_static = _static_metrics(latency, candidate)
    temporal = _matched_temporal(control, latency, candidate, bridge)

    primary = {}
    for axis in ("lateral", "altitude"):
        cs = control_static[axis]
        ls = latency_static[axis]
        primary[axis] = {
            "p95_error_inflation": float(ls["p95_abs_error_m"] / cs["p95_abs_error_m"]),
            "coverage_delta": float(ls["coverage95"] - cs["coverage95"]),
            "median_error_inflation": float(ls["median_abs_error_m"] / cs["median_abs_error_m"]),
        }
    return {
        "integrity": integrity,
        "control": control_static,
        "latency": latency_static,
        "paired_effects": primary,
        "temporal": temporal,
    }


def _gates(contexts: dict[str, dict[str, object]]) -> dict[str, bool]:
    s = contexts["simple"]
    h = contexts["hard"]
    integrity = all(
        c["integrity"]["pass"]
        and c["integrity"]["width_identity_pass"]
        and int(c["temporal"]["matched_transitions"]) >= 500
        for c in contexts.values()
    )
    width_identity = all(c["integrity"]["width_identity_pass"] for c in contexts.values())

    level = (
        float(s["paired_effects"]["lateral"]["p95_error_inflation"]) >= 1.15
        and float(s["paired_effects"]["lateral"]["coverage_delta"]) <= -0.01
        and float(h["paired_effects"]["lateral"]["p95_error_inflation"]) >= 1.15
        and float(h["paired_effects"]["lateral"]["coverage_delta"]) <= -0.05
    )
    persistence = all(
        float(c["temporal"]["axes"]["lateral"]["latency_minus_control_diagnostic_a"]) >= 0.10
        and float(c["temporal"]["axes"]["lateral"]["latency_minus_control_correlation"]) >= 0.10
        for c in contexts.values()
    )
    increments = all(
        float(c["temporal"]["axes"]["lateral"]["increment_q90_ratio"]) <= 0.90
        for c in contexts.values()
    )
    residuals = all(
        float(c["temporal"]["axes"]["lateral"]["frozen_residual_q90_ratio"]) <= 0.90
        for c in contexts.values()
    )
    rpi = all(
        float(c["temporal"]["axes"]["lateral"]["rpi_q90_ratio"]) <= 0.90
        for c in contexts.values()
    )
    divergence = all(
        float(c["paired_effects"]["lateral"]["p95_error_inflation"]) > 1.0
        and float(c["temporal"]["axes"]["lateral"]["frozen_residual_q90_ratio"]) < 1.0
        for c in contexts.values()
    )
    return {
        "l16_1_paired_construction_integrity": bool(integrity),
        "l16_2_phase12_width_identity_under_pure_lag": bool(width_identity),
        "l16_3_lateral_level_error_degradation": bool(level),
        "l16_4_lateral_persistence_increase": bool(persistence),
        "l16_5_lateral_raw_increment_compression": bool(increments),
        "l16_6_lateral_frozen_residual_compression": bool(residuals),
        "l16_7_lateral_q90_frontier_compression": bool(rpi),
        "l16_8_context_stable_divergence": bool(divergence),
        "l16_9_no_refit_no_adaptation": True,
        "l16_10_claim_boundary": True,
    }


def evaluate(
    stage: str,
    phase12_candidate_path: Path,
    bridge_path: Path,
    scientific_git_sha: str,
) -> dict[str, object]:
    phase12_candidate = p14._validate_phase12_candidate(phase12_candidate_path)
    bridge = _validate_bridge(bridge_path)
    contexts: dict[str, dict[str, object]] = {}
    for context in CONTEXTS:
        control, latency = _generate_context(stage, context, phase12_candidate)
        contexts[context] = _context_result(control, latency, phase12_candidate, bridge)
    gates = _gates(contexts)
    return {
        "schema": f"aegisland.phase16.matched-latency-level-dynamics.{stage}-result.v1",
        "phase16_name": PHASE16_NAME,
        "stage": stage,
        "evaluated_seed_seen_after_run": STAGE_SEEDS[stage],
        "families": list(STAGE_FAMILIES[stage]),
        "contexts": CONTEXTS,
        "latency_intervention": {
            "source": "Phase 13C component A",
            "lag_frames": 2,
            "innovation_response": False,
            "severity_response": False,
        },
        "scientific_git_sha": scientific_git_sha,
        "phase12_candidate_sha256": FROZEN_PHASE12_CANDIDATE_SHA256,
        "phase14_bridge_sha256": FROZEN_PHASE14_BRIDGE_SHA256,
        "context_results": contexts,
        "gates": gates,
        "phase16_pass": bool(all(gates.values())),
        "phase15_failure_preserved": True,
        "zero_adaptation": True,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "interpretation": "matched simulation-only decomposition of latency level error versus local temporal residuals",
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=PHASE16_NAME)
    p.add_argument("--stage", choices=("dev", "transfer", "validation", "final"), required=True)
    p.add_argument("--phase12-candidate", type=Path, required=True)
    p.add_argument("--phase14-bridge", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--git-sha", required=True)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    result = evaluate(args.stage, args.phase12_candidate, args.phase14_bridge, args.git_sha)
    result_path = args.out / f"{args.stage}_result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"PHASE16_{args.stage.upper()}_RESULT_SHA256=" + _sha256_file(result_path))
    print(f"PHASE16_{args.stage.upper()}_PASS=" + str(bool(result["phase16_pass"])).lower())
    print(json.dumps(result["gates"], indent=2, sort_keys=True))
    print(json.dumps(result["context_results"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
