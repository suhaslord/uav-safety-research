from __future__ import annotations

import inspect

import numpy as np
import pandas as pd

from scripts import run_phase13_external_validity_gauntlet as p13
from scripts import run_phase13c_compound_attribution as p13c


def _fixture(n: int = 16) -> pd.DataFrame:
    frame = np.arange(n, dtype=int)
    truth_lat = 0.1 * np.sin(frame / 3.0)
    truth_alt = 2.0 + 0.05 * np.cos(frame / 4.0)
    est_lat = truth_lat + np.linspace(-0.03, 0.04, n)
    est_alt = truth_alt + np.linspace(-0.06, 0.08, n)
    return pd.DataFrame(
        {
            "sequence_id": ["fixture-seq"] * n,
            "frame_index": frame,
            "p14_available": [True] * n,
            "truth_visible": [True] * n,
            "truth_lateral_x_m": truth_lat,
            "truth_altitude_m": truth_alt,
            "p14_estimate_lateral_x_m": est_lat,
            "p14_estimate_altitude_m": est_alt,
            "p14_lateral_abs_error_m": np.abs(est_lat - truth_lat),
            "p14_altitude_abs_error_m": np.abs(est_alt - truth_alt),
            "p9_anchor_innovation_lateral_abs": np.linspace(0.1, 2.0, n),
            "severity": np.linspace(0.2, 0.7, n),
        }
    )


def test_exactly_thirteen_locked_contrasts_with_six_components():
    assert p13c.COMPONENTS == ("A", "B", "C", "D", "E", "F")
    assert len(p13c.CONTRAST_COMPONENTS) == 13
    assert len(set(p13c.CONTRAST_COMPONENTS)) == 13
    assert p13c.CONTRAST_COMPONENTS["full_compound"] == frozenset(p13c.COMPONENTS)
    assert sum(len(v) == 1 for v in p13c.CONTRAST_COMPONENTS.values()) == 6
    assert sum(len(v) == 5 for v in p13c.CONTRAST_COMPONENTS.values()) == 6
    assert sum(len(v) == 6 for v in p13c.CONTRAST_COMPONENTS.values()) == 1


def test_phase13c_evidence_partitions_are_fresh_and_disjoint():
    assert p13c.STAGE_SEEDS == {
        "dev": 1313135,
        "transfer": 1313136,
        "validation": 1313137,
        "final": 1313138,
    }
    all_families = []
    for families in p13c.STAGE_FAMILIES.values():
        assert len(families) == 24
        all_families.extend(families)
    assert len(all_families) == len(set(all_families))
    assert p13c.STAGE_FAMILIES["dev"] == tuple(range(1393, 1417))
    assert min(all_families) > 1392


def test_full_compound_uses_exact_frozen_phase13_execution_path():
    df = _fixture()
    expected = p13.apply_shift(df, p13c.ORIGINAL_COMPOUND_NAME, p13c.STAGE_SEEDS["dev"])
    actual = p13c._apply_component_subset(
        df,
        "full_compound",
        frozenset(p13c.COMPONENTS),
        p13c.STAGE_SEEDS["dev"],
    )
    scientific_columns = [
        "p14_estimate_lateral_x_m",
        "p14_estimate_altitude_m",
        "p14_lateral_abs_error_m",
        "p14_altitude_abs_error_m",
        "p9_anchor_innovation_lateral_abs",
        "severity",
        "truth_lateral_x_m",
        "truth_altitude_m",
        "p14_available",
        "truth_visible",
    ]
    for col in scientific_columns:
        a = expected[col].to_numpy()
        b = actual[col].to_numpy()
        if np.issubdtype(a.dtype, np.number):
            assert np.array_equal(a, b, equal_nan=True)
        else:
            assert np.array_equal(a, b)


def test_inference_response_singletons_do_not_change_estimates_or_truth():
    df = _fixture()
    for name in ("innovation_response_only", "severity_response_only"):
        out = p13c._apply_component_subset(
            df,
            name,
            p13c.CONTRAST_COMPONENTS[name],
            p13c.STAGE_SEEDS["dev"],
        )
        assert np.array_equal(
            df["p14_estimate_lateral_x_m"].to_numpy(float),
            out["p14_estimate_lateral_x_m"].to_numpy(float),
            equal_nan=True,
        )
        assert np.array_equal(
            df["p14_estimate_altitude_m"].to_numpy(float),
            out["p14_estimate_altitude_m"].to_numpy(float),
            equal_nan=True,
        )
        assert np.array_equal(df["truth_lateral_x_m"], out["truth_lateral_x_m"])
        assert np.array_equal(df["truth_altitude_m"], out["truth_altitude_m"])


def test_physical_component_subsets_preserve_truth_and_availability():
    df = _fixture()
    for name in ("latency_only", "bias_only", "wind_only", "noise_only"):
        out = p13c._apply_component_subset(
            df,
            name,
            p13c.CONTRAST_COMPONENTS[name],
            p13c.STAGE_SEEDS["dev"],
        )
        assert np.array_equal(df["truth_lateral_x_m"], out["truth_lateral_x_m"])
        assert np.array_equal(df["truth_altitude_m"], out["truth_altitude_m"])
        assert np.array_equal(df["p14_available"], out["p14_available"])
        assert bool(
            np.any(
                np.abs(
                    out["p14_estimate_lateral_x_m"].to_numpy(float)
                    - df["p14_estimate_lateral_x_m"].to_numpy(float)
                )
                > 0.0
            )
            or np.any(
                np.abs(
                    out["p14_estimate_altitude_m"].to_numpy(float)
                    - df["p14_estimate_altitude_m"].to_numpy(float)
                )
                > 0.0
            )
        )


def test_component_ranking_tie_break_is_alphabetical():
    values = {component: 0.1 for component in p13c.COMPONENTS}
    assert p13c._rank_component(values) == "A"
    values["D"] = 0.2
    assert p13c._rank_component(values) == "D"


def test_phase13c_contains_no_model_fit_or_recalibration_path():
    source = inspect.getsource(p13c)
    for forbidden in (
        "fit_reliability_models(",
        "build_calibration(",
        "_fit_group_radii(",
        "CONTINUITY_SCALE_SHRINKAGE =",
    ):
        assert forbidden not in source
    assert '"interval_recalibration": False' in source
    assert '"controller_tuning": False' in source
