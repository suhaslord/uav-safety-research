from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import run_phase16_matched_latency_level_dynamics as p16


def test_phase16_roles_and_contexts_locked():
    assert p16.CONTEXTS == {
        "simple": "small_scale+temporal_dropout",
        "hard": "edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout",
    }
    assert p16.STAGE_SEEDS == {
        "dev": 1616161,
        "transfer": 1616162,
        "validation": 1616163,
        "final": 1616164,
    }
    assert p16.STAGE_FAMILIES["dev"] == tuple(range(1713, 1737))
    assert p16.LATENCY_CONTRAST == "latency_only"
    assert p16.LATENCY_COMPONENTS == frozenset({"A"})


def test_latency_component_a_has_no_reliability_response():
    assert p16.p13c.CONTRAST_COMPONENTS["latency_only"] == frozenset({"A"})
    assert "E" not in p16.LATENCY_COMPONENTS
    assert "F" not in p16.LATENCY_COMPONENTS


def test_sequence_normalization_removes_only_latency_suffix():
    s = pd.Series([
        "seq-a|phase13c:latency_only",
        "seq-b",
    ])
    out = p16._normalized_sequence_id(s).tolist()
    assert out == ["seq-a", "seq-b"]


def _passing_context(simple: bool = True) -> dict:
    coverage_delta = -0.02 if simple else -0.06
    return {
        "integrity": {"pass": True, "width_identity_pass": True},
        "paired_effects": {
            "lateral": {
                "p95_error_inflation": 1.20,
                "coverage_delta": coverage_delta,
            }
        },
        "temporal": {
            "matched_transitions": 600,
            "axes": {
                "lateral": {
                    "latency_minus_control_diagnostic_a": 0.15,
                    "latency_minus_control_correlation": 0.15,
                    "increment_q90_ratio": 0.80,
                    "frozen_residual_q90_ratio": 0.80,
                    "rpi_q90_ratio": 0.80,
                }
            },
        },
    }


def test_gate_logic_requires_both_contexts():
    contexts = {"simple": _passing_context(True), "hard": _passing_context(False)}
    gates = p16._gates(contexts)
    assert all(gates.values())
    contexts["hard"]["temporal"]["axes"]["lateral"]["increment_q90_ratio"] = 0.95
    gates = p16._gates(contexts)
    assert gates["l16_5_lateral_raw_increment_compression"] is False
    assert gates["l16_8_context_stable_divergence"] is True


def test_pure_lag_fixture_keeps_reliability_features_unchanged():
    rows = []
    for frame in range(6):
        rows.append({
            "sequence_id": "fixture",
            "frame_index": frame,
            "p14_available": True,
            "truth_visible": True,
            "truth_lateral_x_m": 0.0,
            "truth_altitude_m": 1.0,
            "p14_estimate_lateral_x_m": 0.1 * frame,
            "p14_estimate_altitude_m": 1.0 + 0.2 * frame,
            "p14_lateral_abs_error_m": abs(0.1 * frame),
            "p14_altitude_abs_error_m": abs(0.2 * frame),
            "p9_anchor_innovation_lateral_abs": 0.5 + 0.1 * frame,
            "severity": 0.4 + 0.01 * frame,
        })
    df = pd.DataFrame(rows)
    shifted = p16.p13c._apply_component_subset(
        df,
        p16.LATENCY_CONTRAST,
        p16.LATENCY_COMPONENTS,
        123,
    )
    assert np.allclose(
        shifted["p9_anchor_innovation_lateral_abs"].to_numpy(float),
        df["p9_anchor_innovation_lateral_abs"].to_numpy(float),
    )
    assert np.allclose(
        shifted["severity"].to_numpy(float),
        df["severity"].to_numpy(float),
    )
    assert shifted.loc[2, "p14_estimate_lateral_x_m"] == df.loc[0, "p14_estimate_lateral_x_m"]
    assert shifted.loc[3, "p14_estimate_lateral_x_m"] == df.loc[1, "p14_estimate_lateral_x_m"]
