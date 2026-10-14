from __future__ import annotations

import inspect

import numpy as np

from scripts import run_phase13_external_validity_gauntlet as p13
from scripts import run_phase13b_paired_degradation_audit as p13b


def _paired_fixture(
    *,
    control_lat: float = 0.92,
    shifted_lat: float = 0.88,
    control_alt: float = 0.93,
    shifted_alt: float = 0.90,
    integrity: bool = True,
):
    return {
        name: {
            "integrity": {"pass": integrity},
            "control": {
                "lateral_95_coverage": control_lat,
                "altitude_95_coverage": control_alt,
            },
            "shifted": {
                "lateral_95_coverage": shifted_lat,
                "altitude_95_coverage": shifted_alt,
            },
            "coverage_delta_shift_minus_control": {
                "lateral": shifted_lat - control_lat,
                "altitude": shifted_alt - control_alt,
            },
        }
        for name in [str(p["name"]) for p in p13.DOMAIN_PROFILES]
    }


def test_phase13b_preserves_exactly_thirteen_frozen_domain_names():
    names = [str(p["name"]) for p in p13.DOMAIN_PROFILES]
    assert len(names) == 13
    assert len(set(names)) == 13
    assert names[-1] == p13b.COMPOUND_DOMAIN


def test_phase13b_evidence_is_fresh_and_disjoint():
    assert p13b.STAGE_SEEDS == {
        "dev": 1313131,
        "transfer": 1313132,
        "validation": 1313133,
        "final": 1313134,
    }
    all_families = []
    for stage, families in p13b.STAGE_FAMILIES.items():
        assert len(families) == 24
        assert len(set(families)) == 24
        all_families.extend(families)
        if stage == "dev":
            assert families == tuple(range(1297, 1321))
    assert len(all_families) == len(set(all_families))
    assert set(p13b.STAGE_SEEDS.values()).isdisjoint(set(p13.STAGE_SEEDS.values()))
    assert min(all_families) > 1296


def test_phase13b_thresholds_are_locked_to_preregistration():
    assert p13b.CATASTROPHIC_COVERAGE_FLOOR == 0.80
    assert p13b.MAX_PAIRED_COVERAGE_LOSS == 0.08
    assert p13b.INNOVATION_ERROR_SPEARMAN_FLOOR == 0.20


def test_manual_spearman_has_no_scipy_dependency_and_is_correct_for_monotone_data():
    x = np.arange(1.0, 21.0)
    y = x**2
    assert np.isclose(p13b._manual_spearman(x, y), 1.0)
    source = inspect.getsource(p13b._manual_spearman)
    assert "scipy" not in source.lower()
    assert "rank(" in source


def test_phase13b_gate_fixture_passes_all_seven_gates():
    paired = _paired_fixture()
    rescue = {"rows": 100, "lateral_95_coverage": 0.90, "altitude_95_coverage": 0.91}
    gates = p13b._gates(paired, rescue, 0.35)
    assert len(gates) == 7
    assert all(bool(g["pass"]) for g in gates.values())


def test_phase13b_compound_domain_cannot_be_hidden_by_other_domains():
    paired = _paired_fixture()
    paired[p13b.COMPOUND_DOMAIN]["shifted"]["lateral_95_coverage"] = 0.79
    paired[p13b.COMPOUND_DOMAIN]["coverage_delta_shift_minus_control"]["lateral"] = -0.13
    rescue = {"rows": 100, "lateral_95_coverage": 0.90, "altitude_95_coverage": 0.91}
    gates = p13b._gates(paired, rescue, 0.35)
    assert gates["g13b_2_no_catastrophic_shifted_domain"]["pass"] is False
    assert gates["g13b_3_bounded_paired_coverage_degradation"]["pass"] is False
    assert gates["g13b_6_compound_domain_stands_alone"]["pass"] is False


def test_phase13b_does_not_define_any_model_fit_or_recalibration_path():
    source = inspect.getsource(p13b)
    forbidden = (
        "fit_reliability_models(",
        "build_calibration(",
        "_fit_group_radii(",
        "CONTINUITY_SCALE_SHRINKAGE =",
    )
    for token in forbidden:
        assert token not in source
    assert '"recalibration_performed": False' in source
    assert '"phase13_stress_manifest_changed": False' in source
