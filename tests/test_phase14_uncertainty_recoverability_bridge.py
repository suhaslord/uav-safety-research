from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import run_phase14_uncertainty_recoverability_bridge as p14


def test_locked_recoverable_set_and_lineage_constants():
    assert p14.RECOVERABLE_HALF_WIDTH_M == {"lateral": 0.30, "altitude": 0.85}
    assert p14.RESERVE_FRACTION == 0.90
    assert p14.NORMALIZED_RESIDUAL_QUANTILE == 0.99
    assert p14.FIT_SEED == 1414140
    assert p14.FIT_FAMILIES == tuple(range(1489, 1521))
    assert p14.STAGE_SEEDS == {
        "dev": 1414141,
        "transfer": 1414142,
        "validation": 1414143,
        "final": 1414144,
    }
    assert p14.LATENCY_PROFILE == "fixed_latency_2f"
    assert p14.LATENCY_BASE_DOMAIN == "small_scale+temporal_dropout"


def test_finite_upper_quantile_uses_preregistered_finite_sample_rank():
    x = np.arange(1.0, 201.0)
    # ceil((200 + 1) * .99) = 199
    assert p14._finite_upper_quantile(x, 0.99) == 199.0


def test_uncertainty_cap_reserves_ten_percent_of_contraction_budget():
    r = 0.30
    a = 0.65
    gamma = 2.0
    h_cap = p14.RESERVE_FRACTION * ((1.0 - abs(a)) * r) / gamma
    image = abs(a) * r + gamma * h_cap
    expected_margin = (1.0 - p14.RESERVE_FRACTION) * (1.0 - abs(a)) * r
    assert np.isclose(r - image, expected_margin)
    assert image <= r


def _fixture() -> pd.DataFrame:
    rows = []
    for seq in ("s1", "s2"):
        for frame in range(5):
            truth_lat = 0.0
            truth_alt = 1.0
            est_lat = 0.02 * frame
            est_alt = 1.0 + 0.03 * frame
            rows.append(
                {
                    "sequence_id": seq,
                    "frame_index": frame,
                    "truth_visible": True,
                    "p14_available": True,
                    "p14_estimate_lateral_x_m": est_lat,
                    "p14_estimate_altitude_m": est_alt,
                    "truth_lateral_x_m": truth_lat,
                    "truth_altitude_m": truth_alt,
                }
            )
    return pd.DataFrame(rows)


def test_transition_table_requires_adjacent_available_rows(monkeypatch):
    df = _fixture()
    monkeypatch.setattr(p14.v1.p11, "_available", lambda frame: np.ones(len(frame), dtype=bool))
    monkeypatch.setattr(
        p14.v3,
        "_halfwidths",
        lambda frame, candidate, axis, q: np.full(len(frame), 0.05 if axis == "lateral" else 0.10),
    )
    out = p14._transition_table(df, {})
    assert len(out) == 8
    assert out["inside_box"].all()
    assert np.all(out["next_frame_index"].to_numpy() == out["frame_index"].to_numpy() + 1)


def test_score_cohort_uses_both_axis_uncertainty_caps():
    transitions = pd.DataFrame(
        {
            "inside_box": [True, True, True],
            "e0_lateral_m": [0.0, 0.0, 0.0],
            "e1_lateral_m": [0.01, 0.01, 0.01],
            "e0_altitude_m": [0.0, 0.0, 0.0],
            "e1_altitude_m": [0.02, 0.02, 0.02],
            "hw_lateral_m": [0.01, 0.03, 0.01],
            "hw_altitude_m": [0.02, 0.02, 0.08],
        }
    )
    candidate = {
        "axis_models": {
            "lateral": {
                "a": 0.5,
                "gamma": 2.0,
                "recoverable_half_width_m": 0.30,
                "halfwidth_cap_m": 0.02,
            },
            "altitude": {
                "a": 0.5,
                "gamma": 2.0,
                "recoverable_half_width_m": 0.85,
                "halfwidth_cap_m": 0.05,
            },
        }
    }
    result = p14._score_cohort(transitions, candidate)
    assert result["eligible_transitions"] == 3
    assert result["admitted_transitions"] == 1
    assert np.isclose(result["admission_fraction"], 1.0 / 3.0)


def test_analytic_gate_rejects_image_outside_box():
    candidate = {
        "axis_models": {
            "lateral": {
                "abs_a": 0.9,
                "gamma": 2.0,
                "halfwidth_cap_m": 0.02,
                "recoverable_half_width_m": 0.30,
            },
            "altitude": {
                "abs_a": 0.7,
                "gamma": 1.0,
                "halfwidth_cap_m": 0.10,
                "recoverable_half_width_m": 0.85,
            },
        }
    }
    passed, detail = p14._analytic_gate(candidate)
    assert passed is False
    assert detail["lateral"]["pass"] is False
    assert detail["altitude"]["pass"] is True
