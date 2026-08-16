from __future__ import annotations

import json

import numpy as np

from scripts import run_phase11_p7_robust_anchor_continuity as p7


def test_freeze_does_not_touch_protected_validation(tmp_path, monkeypatch):
    seen: list[int] = []
    original = p7._raw

    def guarded(name, seed, families, domains):
        seen.append(seed)
        assert seed != p7.VALIDATION_SEED
        return original(name, seed, families, domains)

    monkeypatch.setattr(p7, "_raw", guarded)
    result = p7.freeze(tmp_path, "p7-freeze-test")

    assert p7.VALIDATION_SEED not in seen
    assert result["evidence_role"] == "phase11_p7_seen_transfer_calibration"
    assert not (tmp_path / "validation_frames.csv").exists()
    assert not (tmp_path / "validation_result.json").exists()


def test_candidate_freezes_exact_robust_continuity_rules(tmp_path):
    p7.freeze(tmp_path, "p7-candidate-test")
    candidate = json.loads((tmp_path / "candidate_freeze.json").read_text())
    constants = candidate["continuity_constants"]

    assert candidate["schema"] == "aegisland.phase11.p7.candidate-freeze.v1"
    assert candidate["simulation_only"] is True
    assert candidate["safety_acceptance"] is False
    assert candidate["controller_tuning_allowed"] is False
    assert candidate["validation_seed_unseen_at_freeze"] == p7.VALIDATION_SEED
    assert constants["max_continuity_gap"] == 7
    assert constants["damping"] == 0.85
    assert constants["velocity_cap_quantile"] == 0.99
    assert constants["anchor_window"] == 3
    assert constants["robust_slope"] == "median_all_pairwise"
    assert constants["robust_intercept"] == "median_anchor_intercepts"
    assert candidate["ridge_lambda"] == 4.0
    assert candidate["continuity_correction_model"]["rows"] >= p7.MIN_ADAPTATION_CONTINUITY_ROWS
    assert candidate["transfer_group_rows"]["robust_continuity"] >= p7.MIN_TRANSFER_CONTINUITY_ROWS
    assert candidate["transfer_group_rows"]["base_output"] >= p7.MIN_TRANSFER_BASE_ROWS


def test_robust_state_is_not_forced_through_bad_newest_anchor():
    # A deliberately inconsistent newest anchor should not become the sole intercept.
    values = [(0, 0.0), (1, 1.0), (2, 10.0)]
    slope, trend_latest = p7._robust_axis_state(values, cap=100.0)

    assert np.isfinite(slope)
    assert np.isfinite(trend_latest)
    assert trend_latest != 10.0


def test_robust_continuity_uses_only_missing_frontend_rows_and_bounded_horizon():
    fit_raw = p7._raw("fit", p7.FIT_SEED, p7.FIT_FAMILIES, p7.FIT_DOMAINS)
    caps = p7._fit_velocity_caps(fit_raw)
    raw = p7._raw(
        "adaptation", p7.ADAPTATION_SEED, p7.ADAPTATION_FAMILIES, p7.ADAPTATION_DOMAINS
    )
    out = p7.add_p7_continuity(raw, caps)
    robust = out[out["p7_source"] == "robust_continuity"]

    assert len(robust) >= p7.MIN_ADAPTATION_CONTINUITY_ROWS
    assert (robust["candidate_available"] == False).all()  # noqa: E712
    assert (robust["p1_available"] == False).all()  # noqa: E712
    assert (robust["p7_continuity_horizon"] >= 3).all()
    assert (robust["p7_continuity_horizon"] <= 7).all()
    assert (robust["p7_lateral_slope_cap_utilization"].between(0.0, 1.0)).all()
    assert (robust["p7_altitude_slope_cap_utilization"].between(0.0, 1.0)).all()
    assert np.isfinite(robust["p7_estimate_lateral_x_m"]).all()
    assert np.isfinite(robust["p7_estimate_altitude_m"]).all()
