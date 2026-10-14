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
except ModuleNotFoundError:
    import run_phase12_adaptive_normalized_conformal as v1
    import run_phase12_adaptive_normalized_conformal_v3 as v3
    import run_phase13c_compound_attribution as p13c
    import run_phase14_uncertainty_recoverability_bridge as p14

PHASE17_NAME = "Context-Conditional Coefficient Mismatch Audit"
FIT_SCHEMA = "aegisland.phase17.context-conditional-coefficient-mismatch.fit-candidate.v1"
RESULT_SCHEMA_PREFIX = "aegisland.phase17.context-conditional-coefficient-mismatch"

FROZEN_PHASE12_CANDIDATE_SHA256 = p14.FROZEN_PHASE12_CANDIDATE_SHA256
FROZEN_PHASE14_BRIDGE_SHA256 = "0443d4e45a1966c77544c5c9965de8caec6e622c79ef8c2ce47aee82a3c95981"
REFERENCE_HALF_WIDTH_M = {"lateral": 0.30, "altitude": 0.85}
LATENCY_CONTRAST = "latency_only"
LATENCY_COMPONENTS = frozenset({"A"})
COHORTS = ("control", "latency")
AXES = ("lateral", "altitude")
CONTEXTS = {
    "simple": "small_scale+temporal_dropout",
    "hard": "edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout",
}

FIT_SEED = 1717170
FIT_FAMILIES = tuple(range(1809, 1833))
STAGE_SEEDS = {
    "dev": 1717171,
    "transfer": 1717172,
    "validation": 1717173,
    "final": 1717174,
}
STAGE_FAMILIES = {
    "dev": tuple(range(1833, 1857)),
    "transfer": tuple(range(1857, 1881)),
    "validation": tuple(range(1881, 1905)),
    "final": tuple(range(1905, 1929)),
}

FIT_THRESHOLDS = {
    "minimum_matched_transitions": 500,
    "max_abs_coefficient": 0.98,
    "simple_latency_minus_control_min": 0.15,
    "simple_phase14_mismatch_min": 0.15,
    "hard_phase14_mismatch_max": 0.10,
    "mismatch_heterogeneity_min": 0.10,
}

DEV_THRESHOLDS = {
    "coefficient_transfer_max_abs_error": 0.10,
    "simple_latency_minus_control_min": 0.15,
    "simple_phase14_mismatch_min": 0.15,
    "hard_phase14_mismatch_max": 0.10,
    "mismatch_heterogeneity_min": 0.10,
    "simple_latencyfit_over_phase14_q90_max": 0.90,
    "simple_latencyfit_over_controlfit_q90_max": 0.95,
    "hard_latencyfit_over_phase14_q90_min": 0.90,
    "hard_latencyfit_over_phase14_q90_max": 1.10,
    "simple_minus_hard_relative_improvement_min": 0.08,
    "simple_p95_error_inflation_min": 1.10,
    "simple_coverage_delta_max": -0.01,
    "hard_p95_error_inflation_min": 1.10,
    "hard_coverage_delta_max": -0.05,
}


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _strata(families: tuple[int, ...]) -> dict[str, tuple[int, ...]]:
    if len(families) != 24:
        raise RuntimeError("Phase 17 requires exactly 24 families per role")
    names = ("bootstrap5", "gap3", "gap7", "gap12")
    return {name: families[i * 6 : (i + 1) * 6] for i, name in enumerate(names)}


def _validate_phase12(path: Path) -> dict[str, object]:
    return p14._validate_phase12_candidate(path)


def _validate_phase14_bridge(path: Path) -> dict[str, object]:
    if _sha256_file(path) != FROZEN_PHASE14_BRIDGE_SHA256:
        raise RuntimeError("Phase 17 requires the exact frozen Phase 14 bridge candidate")
    bridge = p14._validate_bridge_candidate(path)
    if bridge.get("recoverable_set_half_width_m") != REFERENCE_HALF_WIDTH_M:
        raise RuntimeError("Phase 17 historical reference box mismatch")
    return bridge


def _pair_id(df: pd.DataFrame) -> pd.Series:
    return df["sequence_id"].astype(str) + "|frame:" + df["frame_index"].astype(int).astype(str)


def _generate_context(
    seed: int,
    families: tuple[int, ...],
    role: str,
    context: str,
    candidate: dict[str, object],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = v1._event(
        f"phase17_{role}_{context}_base",
        seed,
        families,
        (CONTEXTS[context],),
        _strata(families),
        candidate,
    ).copy(deep=True)
    base["phase17_pair_id"] = _pair_id(base)
    base["phase17_context"] = context
    base["phase17_latency_applied"] = False

    control = base.copy(deep=True)
    latency = p13c._apply_component_subset(
        base,
        LATENCY_CONTRAST,
        LATENCY_COMPONENTS,
        seed,
    )
    latency["phase17_context"] = context
    latency["phase17_latency_applied"] = True
    return control, latency


def _available(df: pd.DataFrame) -> np.ndarray:
    return v1.p11._available(df).astype(bool)


def _integrity_and_width_identity(
    control: pd.DataFrame,
    latency: pd.DataFrame,
    candidate: dict[str, object],
) -> dict[str, object]:
    if len(control) != len(latency):
        return {"same_rows": False, "pass": False, "width_identity_pass": False}

    same_pair_ids = bool(
        np.array_equal(
            control["phase17_pair_id"].astype(str).to_numpy(),
            latency["phase17_pair_id"].astype(str).to_numpy(),
        )
    )
    same_truth_visible = bool(
        np.array_equal(
            control["truth_visible"].astype(bool).to_numpy(),
            latency["truth_visible"].astype(bool).to_numpy(),
        )
    )
    same_availability = bool(np.array_equal(_available(control), _available(latency)))
    same_lat_truth = bool(
        np.array_equal(
            control["truth_lateral_x_m"].to_numpy(float),
            latency["truth_lateral_x_m"].to_numpy(float),
            equal_nan=True,
        )
    )
    same_alt_truth = bool(
        np.array_equal(
            control["truth_altitude_m"].to_numpy(float),
            latency["truth_altitude_m"].to_numpy(float),
            equal_nan=True,
        )
    )
    same_severity = bool(
        np.array_equal(
            control["severity"].to_numpy(float),
            latency["severity"].to_numpy(float),
            equal_nan=True,
        )
    )
    same_innovation = bool(
        np.array_equal(
            control["p9_anchor_innovation_lateral_abs"].to_numpy(float),
            latency["p9_anchor_innovation_lateral_abs"].to_numpy(float),
            equal_nan=True,
        )
    )

    mask = _available(control) & _available(latency)
    c = control[mask].copy()
    l = latency[mask].copy()
    width_diffs: dict[str, float] = {}
    width_identity = True
    for axis in AXES:
        cw = v3._halfwidths(c, candidate, axis, 0.95)
        lw = v3._halfwidths(l, candidate, axis, 0.95)
        diff = float(np.max(np.abs(cw - lw))) if len(cw) else float("inf")
        width_diffs[axis] = diff
        width_identity = width_identity and bool(diff <= 1.0e-12)

    construction = bool(
        same_pair_ids
        and same_truth_visible
        and same_availability
        and same_lat_truth
        and same_alt_truth
        and same_severity
        and same_innovation
    )
    return {
        "same_rows": True,
        "same_pair_ids": same_pair_ids,
        "same_truth_visible": same_truth_visible,
        "same_useful_availability": same_availability,
        "same_lateral_truth": same_lat_truth,
        "same_altitude_truth": same_alt_truth,
        "same_severity": same_severity,
        "same_anchor_innovation": same_innovation,
        "max_halfwidth_abs_diff_m": width_diffs,
        "width_identity_pass": bool(width_identity),
        "pass": construction,
    }


def _normalized_sequence_id(values: pd.Series) -> pd.Series:
    return values.astype(str).str.replace("|phase13c:latency_only", "", regex=False)


def _transition_frame(
    df: pd.DataFrame,
    candidate: dict[str, object],
    prefix: str,
) -> pd.DataFrame:
    t = p14._transition_table(df, candidate).copy()
    t["pair_sequence"] = _normalized_sequence_id(t["sequence_id"])
    keep = [
        "pair_sequence",
        "frame_index",
        "inside_box",
        "e0_lateral_m",
        "e1_lateral_m",
        "e0_altitude_m",
        "e1_altitude_m",
    ]
    rename = {c: f"{prefix}_{c}" for c in keep if c not in ("pair_sequence", "frame_index")}
    return t[keep].rename(columns=rename)


def _matched_transitions(
    control: pd.DataFrame,
    latency: pd.DataFrame,
    candidate: dict[str, object],
) -> pd.DataFrame:
    ct = _transition_frame(control, candidate, "control")
    lt = _transition_frame(latency, candidate, "latency")
    m = ct.merge(lt, on=["pair_sequence", "frame_index"], how="inner", validate="one_to_one")
    m = m[
        m["control_inside_box"].astype(bool)
        & m["latency_inside_box"].astype(bool)
    ].copy()
    if len(m) < FIT_THRESHOLDS["minimum_matched_transitions"]:
        raise RuntimeError(f"Phase 17 underpowered matched temporal subset: {len(m)}")
    return m


def _ols_no_intercept(e0: np.ndarray, e1: np.ndarray) -> float:
    x = np.asarray(e0, dtype=float)
    y = np.asarray(e1, dtype=float)
    if x.ndim != 1 or y.ndim != 1 or len(x) != len(y) or len(x) == 0:
        raise RuntimeError("Phase 17 OLS requires equal nonempty vectors")
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise RuntimeError("Phase 17 OLS vectors must be finite")
    denom = float(np.dot(x, x))
    if denom <= 1.0e-12 or not np.isfinite(denom):
        raise RuntimeError("Phase 17 degenerate OLS denominator")
    a = float(np.dot(x, y) / denom)
    if not np.isfinite(a):
        raise RuntimeError("Phase 17 OLS coefficient is non-finite")
    return a


def _fit_context_coefficients(matched: pd.DataFrame) -> dict[str, object]:
    out: dict[str, object] = {}
    for cohort in COHORTS:
        out[cohort] = {}
        for axis in AXES:
            e0 = matched[f"{cohort}_e0_{axis}_m"].to_numpy(float)
            e1 = matched[f"{cohort}_e1_{axis}_m"].to_numpy(float)
            a = _ols_no_intercept(e0, e1)
            out[cohort][axis] = {
                "a": a,
                "abs_a": abs(a),
                "rows": int(len(e0)),
                "adjacent_error_correlation": float(np.corrcoef(e0, e1)[0, 1]),
            }
    return out


def _fit_gates(
    contexts: dict[str, dict[str, object]],
    phase14_lateral_a: float,
) -> dict[str, bool]:
    min_rows = FIT_THRESHOLDS["minimum_matched_transitions"]
    max_a = FIT_THRESHOLDS["max_abs_coefficient"]

    construction = all(
        bool(c["integrity"]["pass"])
        and bool(c["integrity"]["width_identity_pass"])
        and int(c["matched_transitions"]) >= min_rows
        for c in contexts.values()
    )
    finite_contract = all(
        np.isfinite(float(c["coefficients"][cohort][axis]["a"]))
        and abs(float(c["coefficients"][cohort][axis]["a"])) < max_a
        for c in contexts.values()
        for cohort in COHORTS
        for axis in AXES
    )

    s_control = float(contexts["simple"]["coefficients"]["control"]["lateral"]["a"])
    s_latency = float(contexts["simple"]["coefficients"]["latency"]["lateral"]["a"])
    h_latency = float(contexts["hard"]["coefficients"]["latency"]["lateral"]["a"])

    simple_shift = bool(
        s_latency - s_control >= FIT_THRESHOLDS["simple_latency_minus_control_min"]
        and abs(s_latency - phase14_lateral_a) >= FIT_THRESHOLDS["simple_phase14_mismatch_min"]
    )
    hard_proximity = bool(
        abs(h_latency - phase14_lateral_a) <= FIT_THRESHOLDS["hard_phase14_mismatch_max"]
    )
    heterogeneity = bool(
        abs(s_latency - phase14_lateral_a) - abs(h_latency - phase14_lateral_a)
        >= FIT_THRESHOLDS["mismatch_heterogeneity_min"]
    )

    return {
        "f17_1_construction_integrity": construction,
        "f17_2_finite_unclipped_coefficient_candidate": finite_contract,
        "f17_3_simple_context_large_latency_shift": simple_shift,
        "f17_4_hard_context_phase14_proximity": hard_proximity,
        "f17_5_mismatch_heterogeneity": heterogeneity,
    }


def build_fit_candidate(
    phase12_candidate_path: Path,
    phase14_bridge_path: Path,
    scientific_git_sha: str,
) -> tuple[dict[str, object], dict[str, pd.DataFrame]]:
    candidate = _validate_phase12(phase12_candidate_path)
    bridge = _validate_phase14_bridge(phase14_bridge_path)
    phase14_lateral_a = float(bridge["axis_models"]["lateral"]["a"])

    context_results: dict[str, dict[str, object]] = {}
    matched_frames: dict[str, pd.DataFrame] = {}
    for context in CONTEXTS:
        control, latency = _generate_context(
            FIT_SEED,
            FIT_FAMILIES,
            "fit",
            context,
            candidate,
        )
        integrity = _integrity_and_width_identity(control, latency, candidate)
        matched = _matched_transitions(control, latency, candidate)
        coeffs = _fit_context_coefficients(matched)
        context_results[context] = {
            "base_domain": CONTEXTS[context],
            "integrity": integrity,
            "matched_transitions": int(len(matched)),
            "coefficients": coeffs,
        }
        matched_frames[context] = matched

    gates = _fit_gates(context_results, phase14_lateral_a)
    fit_eligible = bool(all(gates.values()))
    fit_candidate = {
        "schema": FIT_SCHEMA,
        "phase17_name": PHASE17_NAME,
        "method": "matched_context_specific_no_intercept_error_ar1_coefficient_audit",
        "scientific_git_sha": scientific_git_sha,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "phase12_candidate_sha256": FROZEN_PHASE12_CANDIDATE_SHA256,
        "phase14_bridge_sha256": FROZEN_PHASE14_BRIDGE_SHA256,
        "phase14_lateral_a": phase14_lateral_a,
        "latency_intervention": {
            "lag_frames": 2,
            "phase13c_component": "A",
            "innovation_response": False,
            "severity_response": False,
            "bias": False,
            "wind": False,
            "measurement_noise": False,
        },
        "fit_evidence": {
            "seed": FIT_SEED,
            "families": list(FIT_FAMILIES),
            "contexts": CONTEXTS,
        },
        "thresholds": FIT_THRESHOLDS,
        "contexts": context_results,
        "gates": gates,
        "fit_eligible_for_development": fit_eligible,
        "zero_adaptation": True,
    }
    return fit_candidate, matched_frames


def _validate_fit_candidate(path: Path) -> dict[str, object]:
    fit = json.loads(path.read_text(encoding="utf-8"))
    if fit.get("schema") != FIT_SCHEMA:
        raise RuntimeError("Phase 17 fit candidate schema mismatch")
    if fit.get("phase12_candidate_sha256") != FROZEN_PHASE12_CANDIDATE_SHA256:
        raise RuntimeError("Phase 17 fit predecessor Phase 12 digest mismatch")
    if fit.get("phase14_bridge_sha256") != FROZEN_PHASE14_BRIDGE_SHA256:
        raise RuntimeError("Phase 17 fit predecessor Phase 14 digest mismatch")
    if fit.get("fit_evidence", {}).get("seed") != FIT_SEED:
        raise RuntimeError("Phase 17 fit seed mismatch")
    if fit.get("fit_evidence", {}).get("families") != list(FIT_FAMILIES):
        raise RuntimeError("Phase 17 fit families mismatch")
    if fit.get("fit_eligible_for_development") is not True:
        raise RuntimeError("Phase 17 development prohibited because fit eligibility failed")
    if fit.get("simulation_only") is not True:
        raise RuntimeError("Phase 17 simulation boundary mismatch")
    if fit.get("safety_acceptance") is not False:
        raise RuntimeError("Phase 17 safety boundary mismatch")
    if fit.get("controller_tuning_allowed") is not False:
        raise RuntimeError("Phase 17 controller boundary mismatch")
    return fit


def _static_metrics(df: pd.DataFrame, candidate: dict[str, object]) -> dict[str, object]:
    d = df[_available(df)].copy()
    out: dict[str, object] = {"rows": int(len(df)), "useful_rows": int(len(d))}
    for axis in AXES:
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


def _residual_metrics(e0: np.ndarray, e1: np.ndarray, a: float) -> dict[str, float]:
    signed = np.asarray(e1, dtype=float) - float(a) * np.asarray(e0, dtype=float)
    absolute = np.abs(signed)
    return {
        "a": float(a),
        "q90_abs_residual_m": p14._finite_upper_quantile(absolute, 0.90),
        "rmse_signed_residual_m": float(np.sqrt(np.mean(np.square(signed)))),
        "median_abs_residual_m": float(np.median(absolute)),
    }


def _development_context(
    control: pd.DataFrame,
    latency: pd.DataFrame,
    phase12_candidate: dict[str, object],
    fit: dict[str, object],
    context: str,
) -> dict[str, object]:
    integrity = _integrity_and_width_identity(control, latency, phase12_candidate)
    matched = _matched_transitions(control, latency, phase12_candidate)
    diag = _fit_context_coefficients(matched)
    control_static = _static_metrics(control, phase12_candidate)
    latency_static = _static_metrics(latency, phase12_candidate)

    e0 = matched["latency_e0_lateral_m"].to_numpy(float)
    e1 = matched["latency_e1_lateral_m"].to_numpy(float)
    phase14_a = float(fit["phase14_lateral_a"])
    control_a = float(fit["contexts"][context]["coefficients"]["control"]["lateral"]["a"])
    latency_a = float(fit["contexts"][context]["coefficients"]["latency"]["lateral"]["a"])

    residuals = {
        "phase14": _residual_metrics(e0, e1, phase14_a),
        "phase17_control_fit": _residual_metrics(e0, e1, control_a),
        "phase17_latency_fit": _residual_metrics(e0, e1, latency_a),
    }
    q14 = float(residuals["phase14"]["q90_abs_residual_m"])
    qc = float(residuals["phase17_control_fit"]["q90_abs_residual_m"])
    ql = float(residuals["phase17_latency_fit"]["q90_abs_residual_m"])
    residuals["latencyfit_over_phase14_q90"] = ql / q14
    residuals["latencyfit_over_controlfit_q90"] = ql / qc
    residuals["relative_improvement_vs_phase14"] = 1.0 - ql / q14

    paired_effect = {
        "lateral": {
            "p95_error_inflation": float(
                latency_static["lateral"]["p95_abs_error_m"]
                / control_static["lateral"]["p95_abs_error_m"]
            ),
            "coverage_delta": float(
                latency_static["lateral"]["coverage95"]
                - control_static["lateral"]["coverage95"]
            ),
            "median_error_inflation": float(
                latency_static["lateral"]["median_abs_error_m"]
                / control_static["lateral"]["median_abs_error_m"]
            ),
        }
    }
    transfer_error = {
        cohort: {
            axis: abs(
                float(diag[cohort][axis]["a"])
                - float(fit["contexts"][context]["coefficients"][cohort][axis]["a"])
            )
            for axis in AXES
        }
        for cohort in COHORTS
    }

    return {
        "base_domain": CONTEXTS[context],
        "integrity": integrity,
        "matched_transitions": int(len(matched)),
        "control": control_static,
        "latency": latency_static,
        "development_diagnostic_coefficients": diag,
        "fit_coefficient_transfer_abs_error": transfer_error,
        "latency_lateral_residuals": residuals,
        "paired_effects": paired_effect,
    }


def _development_gates(
    contexts: dict[str, dict[str, object]],
    fit: dict[str, object],
) -> dict[str, bool]:
    phase14_a = float(fit["phase14_lateral_a"])
    min_rows = FIT_THRESHOLDS["minimum_matched_transitions"]

    lineage_integrity = all(
        bool(c["integrity"]["pass"])
        and bool(c["integrity"]["width_identity_pass"])
        and int(c["matched_transitions"]) >= min_rows
        for c in contexts.values()
    )

    transfer = all(
        float(c["fit_coefficient_transfer_abs_error"][cohort][axis])
        <= DEV_THRESHOLDS["coefficient_transfer_max_abs_error"]
        for c in contexts.values()
        for cohort in COHORTS
        for axis in AXES
    )

    s = contexts["simple"]
    h = contexts["hard"]
    s_control = float(s["development_diagnostic_coefficients"]["control"]["lateral"]["a"])
    s_latency = float(s["development_diagnostic_coefficients"]["latency"]["lateral"]["a"])
    h_latency = float(h["development_diagnostic_coefficients"]["latency"]["lateral"]["a"])

    simple_replication = bool(
        s_latency - s_control >= DEV_THRESHOLDS["simple_latency_minus_control_min"]
        and abs(s_latency - phase14_a) >= DEV_THRESHOLDS["simple_phase14_mismatch_min"]
    )
    hard_replication = bool(
        abs(h_latency - phase14_a) <= DEV_THRESHOLDS["hard_phase14_mismatch_max"]
    )
    heterogeneity = bool(
        abs(s_latency - phase14_a) - abs(h_latency - phase14_a)
        >= DEV_THRESHOLDS["mismatch_heterogeneity_min"]
    )

    s_ratio_14 = float(s["latency_lateral_residuals"]["latencyfit_over_phase14_q90"])
    s_ratio_c = float(s["latency_lateral_residuals"]["latencyfit_over_controlfit_q90"])
    h_ratio_14 = float(h["latency_lateral_residuals"]["latencyfit_over_phase14_q90"])
    simple_penalty = bool(
        s_ratio_14 <= DEV_THRESHOLDS["simple_latencyfit_over_phase14_q90_max"]
        and s_ratio_c <= DEV_THRESHOLDS["simple_latencyfit_over_controlfit_q90_max"]
    )
    hard_limited = bool(
        h_ratio_14 >= DEV_THRESHOLDS["hard_latencyfit_over_phase14_q90_min"]
        and h_ratio_14 <= DEV_THRESHOLDS["hard_latencyfit_over_phase14_q90_max"]
    )
    improvement_gap = bool(
        float(s["latency_lateral_residuals"]["relative_improvement_vs_phase14"])
        - float(h["latency_lateral_residuals"]["relative_improvement_vs_phase14"])
        >= DEV_THRESHOLDS["simple_minus_hard_relative_improvement_min"]
    )

    level = bool(
        float(s["paired_effects"]["lateral"]["p95_error_inflation"])
        >= DEV_THRESHOLDS["simple_p95_error_inflation_min"]
        and float(s["paired_effects"]["lateral"]["coverage_delta"])
        <= DEV_THRESHOLDS["simple_coverage_delta_max"]
        and float(h["paired_effects"]["lateral"]["p95_error_inflation"])
        >= DEV_THRESHOLDS["hard_p95_error_inflation_min"]
        and float(h["paired_effects"]["lateral"]["coverage_delta"])
        <= DEV_THRESHOLDS["hard_coverage_delta_max"]
    )

    return {
        "m17_1_lineage_and_matched_construction_integrity": lineage_integrity,
        "m17_2_coefficient_transfer": transfer,
        "m17_3_simple_context_mismatch_replication": simple_replication,
        "m17_4_hard_context_proximity_replication": hard_replication,
        "m17_5_context_heterogeneity_replication": heterogeneity,
        "m17_6_simple_context_out_of_sample_mismatch_penalty": simple_penalty,
        "m17_7_hard_context_limited_coefficient_advantage": hard_limited,
        "m17_8_simple_advantage_exceeds_hard_advantage": improvement_gap,
        "m17_9_latency_level_error_degradation_remains_present": level,
        "m17_10_zero_adaptation_and_claim_boundary": True,
    }


def evaluate_stage(
    stage: str,
    phase12_candidate_path: Path,
    phase14_bridge_path: Path,
    fit_candidate_path: Path,
    scientific_git_sha: str,
) -> dict[str, object]:
    phase12 = _validate_phase12(phase12_candidate_path)
    _validate_phase14_bridge(phase14_bridge_path)
    fit = _validate_fit_candidate(fit_candidate_path)

    seed = STAGE_SEEDS[stage]
    families = STAGE_FAMILIES[stage]
    contexts: dict[str, dict[str, object]] = {}
    for context in CONTEXTS:
        control, latency = _generate_context(seed, families, stage, context, phase12)
        contexts[context] = _development_context(control, latency, phase12, fit, context)

    gates = _development_gates(contexts, fit)
    return {
        "schema": f"{RESULT_SCHEMA_PREFIX}.{stage}-result.v1",
        "phase17_name": PHASE17_NAME,
        "stage": stage,
        "evaluated_seed_seen_after_run": seed,
        "families": list(families),
        "contexts": contexts,
        "scientific_git_sha": scientific_git_sha,
        "phase12_candidate_sha256": FROZEN_PHASE12_CANDIDATE_SHA256,
        "phase14_bridge_sha256": FROZEN_PHASE14_BRIDGE_SHA256,
        "phase17_fit_candidate_sha256": _sha256_file(fit_candidate_path),
        "phase14_lateral_a": float(fit["phase14_lateral_a"]),
        "latency_intervention": fit["latency_intervention"],
        "development_thresholds": DEV_THRESHOLDS,
        "gates": gates,
        "phase17_pass": bool(all(gates.values())),
        "zero_adaptation": True,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "interpretation": "simulation-only context-conditional coefficient-mismatch mechanism audit; not physical latency causality or a safety proof",
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=PHASE17_NAME)
    p.add_argument("--stage", choices=("fit", "dev", "transfer", "validation", "final"), required=True)
    p.add_argument("--phase12-candidate", type=Path, required=True)
    p.add_argument("--phase14-bridge", type=Path, required=True)
    p.add_argument("--fit-candidate", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--git-sha", required=True)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    if args.stage == "fit":
        fit, matched = build_fit_candidate(
            args.phase12_candidate,
            args.phase14_bridge,
            args.git_sha,
        )
        fit_path = args.out / "fit_candidate.json"
        fit_path.write_text(json.dumps(fit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        for context, frame in matched.items():
            frame.to_csv(args.out / f"fit_{context}_matched_transitions.csv", index=False)
        print("PHASE17_FIT_CANDIDATE_SHA256=" + _sha256_file(fit_path))
        print("PHASE17_FIT_ELIGIBLE_FOR_DEVELOPMENT=" + str(bool(fit["fit_eligible_for_development"])).lower())
        print(json.dumps(fit["gates"], sort_keys=True))
        print(json.dumps({k: v["coefficients"] for k, v in fit["contexts"].items()}, sort_keys=True))
        return

    if args.fit_candidate is None:
        raise SystemExit("--fit-candidate is required outside fit stage")
    result = evaluate_stage(
        args.stage,
        args.phase12_candidate,
        args.phase14_bridge,
        args.fit_candidate,
        args.git_sha,
    )
    result_path = args.out / f"{args.stage}_result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"PHASE17_{args.stage.upper()}_RESULT_SHA256=" + _sha256_file(result_path))
    print(f"PHASE17_{args.stage.upper()}_PASS=" + str(bool(result["phase17_pass"])).lower())
    print(json.dumps(result["gates"], sort_keys=True))
    print(json.dumps(result["contexts"], sort_keys=True))


if __name__ == "__main__":
    main()
