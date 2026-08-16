from __future__ import annotations

import json

import numpy as np

from scripts import run_phase11_p5_perception_continuity as p5


def test_freeze_never_generates_protected_validation(tmp_path, monkeypatch):
    seen = []
    original = p5._generate_raw

    def guarded(name, seed, families, domains):
        seen.append(seed)
        assert seed != p5.VALIDATION_SEED
        return original(name, seed, families, domains)

    monkeypatch.setattr(p5, "_generate_raw", guarded)
    result = p5.freeze(tmp_path, "test-freeze-sha")

    assert p5.VALIDATION_SEED not in seen
    assert not (tmp_path / "validation_frames.csv").exists()
    assert not (tmp_path / "validation_result.json").exists()
    assert result["evidence_role"] == "phase11_p5_seen_transfer_calibration"


def test_candidate_freezes_claim_boundaries_and_continuity_constants(tmp_path):
    p5.freeze(tmp_path, "candidate-test-sha")
    candidate = json.loads((tmp_path / "candidate_freeze.json").read_text())

    assert candidate["schema"] == "aegisland.phase11.p5.candidate-freeze.v1"
    assert candidate["simulation_only"] is True
    assert candidate["safety_acceptance"] is False
    assert candidate["controller_tuning_allowed"] is False
    assert candidate["validation_seed_unseen_at_freeze"] == p5.VALIDATION_SEED
    assert candidate["max_continuity_gap"] == 5
    assert candidate["damping"] == 0.85
    assert candidate["velocity_cap_quantile"] == 0.99
    assert candidate["ridge_lambda"] == 4.0


def test_continuity_extension_is_bounded_and_non_genuine():
    fit_raw = p5._generate_raw("fit", p5.FIT_SEED, p5.FIT_FAMILIES, p5.FIT_DOMAINS)
    caps = p5._fit_velocity_caps(fit_raw)
    raw = p5._generate_raw(
        "transfer", p5.TRANSFER_SEED, p5.TRANSFER_FAMILIES, p5.TRANSFER_DOMAINS
    )
    out = p5.add_p5_continuity(raw, caps)
    ext = out[out["p5_source"] == "continuity_extension"]

    assert len(ext) > 0
    assert (ext["candidate_available"] == False).all()  # noqa: E712
    assert (ext["p1_available"] == False).all()  # noqa: E712
    assert (ext["p5_continuity_horizon"] > 2).all()
    assert (ext["p5_continuity_horizon"] <= p5.MAX_CONTINUITY_GAP).all()
    assert np.isfinite(ext["p5_estimate_lateral_x_m"]).all()
    assert np.isfinite(ext["p5_estimate_altitude_m"]).all()


def test_velocity_caps_are_fit_derived_positive_and_respected():
    raw = p5._generate_raw("fit", p5.FIT_SEED, p5.FIT_FAMILIES, p5.FIT_DOMAINS)
    caps = p5._fit_velocity_caps(raw)
    out = p5.add_p5_continuity(raw, caps)

    assert caps["lateral"] > 0
    assert caps["altitude"] > 0
    assert out["p5_local_lateral_slope_abs"].max() <= caps["lateral"] + 1e-12
    assert out["p5_local_altitude_slope_abs"].max() <= caps["altitude"] + 1e-12
