from __future__ import annotations

import inspect
import json

import numpy as np
import pandas as pd
import pytest

from scripts import run_phase13_external_validity_gauntlet as p13


def _fixture(n: int = 20) -> pd.DataFrame:
    frame = np.arange(n)
    truth_lat = 0.2 * np.sin(frame / 4.0)
    truth_alt = 2.0 + 0.1 * np.cos(frame / 5.0)
    est_lat = truth_lat + 0.01 * np.sin(frame / 3.0)
    est_alt = truth_alt + 0.02 * np.cos(frame / 3.0)
    return pd.DataFrame(
        {
            "sequence_id": ["fixture"] * n,
            "frame_index": frame,
            "p14_available": [True] * n,
            "truth_visible": [True] * n,
            "truth_lateral_x_m": truth_lat,
            "truth_altitude_m": truth_alt,
            "p14_estimate_lateral_x_m": est_lat,
            "p14_estimate_altitude_m": est_alt,
            "p14_lateral_abs_error_m": np.abs(est_lat - truth_lat),
            "p14_altitude_abs_error_m": np.abs(est_alt - truth_alt),
            "p9_anchor_innovation_lateral_abs": np.linspace(0.01, 0.2, n),
            "severity": np.linspace(0.2, 0.6, n),
        }
    )


def test_phase13_is_exactly_thirteen_locked_domains():
    assert len(p13.DOMAIN_PROFILES) == 13
    names = [str(x["name"]) for x in p13.DOMAIN_PROFILES]
    assert len(set(names)) == 13
    assert {str(x["category"]) for x in p13.DOMAIN_PROFILES} == {
        "sensing",
        "timing",
        "dynamics",
        "compound",
    }


def test_phase13_fresh_evidence_seeds_and_families_are_disjoint():
    seeds = [
        p13.DEV_SEED,
        p13.TRANSFER_SEED,
        p13.VALIDATION_SEED,
        p13.FINAL_SEED,
    ]
    assert len(set(seeds)) == 4
    assert not set(seeds).intersection({907907, 913913, 924924, 935935, 858858, 869869})

    family_sets = [set(v) for v in p13.STAGE_FAMILIES.values()]
    assert all(len(v) == 24 for v in family_sets)
    for i, a in enumerate(family_sets):
        for b in family_sets[i + 1 :]:
            assert a.isdisjoint(b)


def test_shift_overlay_is_deterministic_for_every_domain():
    df = _fixture()
    for profile in p13.DOMAIN_PROFILES:
        name = str(profile["name"])
        a = p13.apply_shift(df, name, p13.DEV_SEED)
        b = p13.apply_shift(df.copy(), name, p13.DEV_SEED)
        pd.testing.assert_frame_equal(a, b)


def test_shift_overlay_never_changes_truth_or_availability():
    df = _fixture()
    truth_cols = ["truth_visible", "truth_lateral_x_m", "truth_altitude_m", "p14_available"]
    for profile in p13.DOMAIN_PROFILES:
        shifted = p13.apply_shift(df, str(profile["name"]), p13.DEV_SEED)
        for col in truth_cols:
            if df[col].dtype == bool:
                assert shifted[col].equals(df[col])
            else:
                assert np.array_equal(shifted[col].to_numpy(), df[col].to_numpy())


def test_shift_overlay_recomputes_error_from_shifted_estimate():
    df = _fixture()
    shifted = p13.apply_shift(df, "latency_wind_calibration_compound", p13.DEV_SEED)
    expected_lat = np.abs(
        shifted["p14_estimate_lateral_x_m"].to_numpy(float)
        - shifted["truth_lateral_x_m"].to_numpy(float)
    )
    expected_alt = np.abs(
        shifted["p14_estimate_altitude_m"].to_numpy(float)
        - shifted["truth_altitude_m"].to_numpy(float)
    )
    assert np.allclose(shifted["p14_lateral_abs_error_m"], expected_lat, equal_nan=True)
    assert np.allclose(shifted["p14_altitude_abs_error_m"], expected_alt, equal_nan=True)


def test_phase13_inference_cues_remain_finite_and_nonnegative():
    df = _fixture()
    for profile in p13.DOMAIN_PROFILES:
        shifted = p13.apply_shift(df, str(profile["name"]), p13.DEV_SEED)
        assert np.all(np.isfinite(shifted["severity"].to_numpy(float)))
        assert np.all((shifted["severity"] >= 0.0) & (shifted["severity"] <= 1.0))
        innovation = shifted["p9_anchor_innovation_lateral_abs"].to_numpy(float)
        assert np.all(np.isfinite(innovation))
        assert np.all(innovation >= 0.0)


def test_phase13_has_no_fitting_or_recalibration_path():
    source = inspect.getsource(p13)
    forbidden = (
        "_fit_reliability_models(",
        "_fit_scale_models(",
        "_fit_normalized_radii(",
        "build_calibration(",
        "recalibrate",
    )
    for token in forbidden:
        assert token not in source
    assert p13.FROZEN_PHASE12_CANDIDATE_SHA256 == (
        "e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991"
    )
    assert p13.FROZEN_PHASE12_SCIENTIFIC_SHA == "8d0617a83d699cd14eae6194ce3a86a5c034dfbc"


def test_phase13_development_workflow_never_mentions_downstream_phase13_seeds():
    workflow = open(".github/workflows/phase13-development.yml", encoding="utf-8").read()
    for forbidden in (
        str(p13.TRANSFER_SEED),
        str(p13.VALIDATION_SEED),
        str(p13.FINAL_SEED),
    ):
        assert forbidden not in workflow


def test_phase13_domain_manifest_matches_code():
    manifest = json.load(open("docs/phase13_domain_manifest.json", encoding="utf-8"))
    assert manifest["domain_count"] == 13
    assert manifest["domains"] == list(p13.DOMAIN_PROFILES)
    assert manifest["frozen_phase12_candidate_sha256"] == p13.FROZEN_PHASE12_CANDIDATE_SHA256
    assert manifest["simulation_only"] is True
    assert manifest["safety_acceptance"] is False
    assert manifest["controller_tuning_allowed"] is False


def test_phase13_candidate_validation_rejects_wrong_digest(tmp_path):
    bad = tmp_path / "candidate.json"
    bad.write_text("{}\n", encoding="utf-8")
    with pytest.raises(RuntimeError):
        p13._validate_candidate(bad)
