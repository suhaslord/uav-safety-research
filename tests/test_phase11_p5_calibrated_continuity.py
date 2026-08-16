from __future__ import annotations

import numpy as np

from scripts import run_phase11_p5_calibrated_continuity as p5


def test_p5_evidence_is_new_and_disjoint():
    prior = {33033, 63333, 44044, 55055, 66066, 77077, 88088, 99099, 101101, 112112, 121121, 132132, 143143, 154154, 165165, 176176, 187187, 198198}
    assert {p5.FIT_SEED, p5.CALIBRATION_SEED, p5.TRANSFER_SEED, p5.VALIDATION_SEED}.isdisjoint(prior)
    groups = [set(p5.FIT_FAMILIES), set(p5.CALIBRATION_FAMILIES), set(p5.TRANSFER_FAMILIES), set(p5.VALIDATION_FAMILIES)]
    for i, left in enumerate(groups):
        for right in groups[i + 1:]:
            assert left.isdisjoint(right)


def test_p5_freeze_never_generates_validation(tmp_path, monkeypatch):
    calls = []
    original = p5.p1.generate_split
    def guarded(name, seed, families, domains, frames=p5.FRAMES_PER_SEQUENCE):
        calls.append(seed)
        assert seed != p5.VALIDATION_SEED
        return original(name, seed, families, domains, frames=frames)
    monkeypatch.setattr(p5.p1, "generate_split", guarded)
    c = p5.freeze(tmp_path, "test-sha")
    assert p5.VALIDATION_SEED not in calls
    assert c["validation_seed_unseen_at_freeze"] == p5.VALIDATION_SEED


def test_bridge_never_exceeds_five_and_does_not_feed_itself():
    raw = p5._raw("fit", p5.FIT_SEED, p5.FIT_FAMILIES[:1], p5.FIT_DOMAINS[:2])
    caps = p5.fit_velocity_caps(raw)
    bridged = p5.add_continuity_bridge(raw, caps)
    assert bridged["bridge_horizon"].max() <= 5
    assert set(bridged.loc[bridged["bridge_horizon"] > 0, "p1_source"].unique()) <= {"temporal_bridge"}
    direct_count = int(raw["candidate_available"].sum())
    assert direct_count == int((bridged["candidate_available"]).sum())


def test_velocity_caps_are_finite_positive():
    raw = p5._raw("fit", p5.FIT_SEED, p5.FIT_FAMILIES[:1], p5.FIT_DOMAINS[:2])
    caps = p5.fit_velocity_caps(raw)
    assert caps["lateral_per_frame"] > 0
    assert caps["altitude_per_frame"] > 0
    assert np.isfinite(list(caps.values())).all()
