from __future__ import annotations

import numpy as np

from scripts import run_phase11_p6_horizon_calibration as p6


def test_p6_evidence_is_new_and_disjoint():
    prior = {33033, 63333, 44044, 55055, 66066, 77077, 88088, 99099, 101101, 112112, 121121, 132132, 143143, 154154, 165165, 176176, 187187, 198198, 209209, 220220, 231231, 242242}
    assert {p6.FIT_SEED, p6.CALIBRATION_SEED, p6.TRANSFER_SEED, p6.DEVELOPMENT_SEED, p6.VALIDATION_SEED}.isdisjoint(prior)
    groups = [set(p6.FIT_FAMILIES), set(p6.CALIBRATION_FAMILIES), set(p6.TRANSFER_FAMILIES), set(p6.DEVELOPMENT_FAMILIES), set(p6.VALIDATION_FAMILIES)]
    for i, left in enumerate(groups):
        for right in groups[i + 1:]:
            assert left.isdisjoint(right)


def test_p6_freeze_does_not_touch_development_or_validation(tmp_path, monkeypatch):
    calls = []
    original = p6.p1.generate_split

    def guarded(name, seed, families, domains, frames=p6.FRAMES_PER_SEQUENCE):
        calls.append(seed)
        assert seed not in {p6.DEVELOPMENT_SEED, p6.VALIDATION_SEED}
        return original(name, seed, families, domains, frames=frames)

    monkeypatch.setattr(p6.p1, "generate_split", guarded)
    candidate = p6.freeze(tmp_path, "test-sha")
    assert p6.DEVELOPMENT_SEED not in calls
    assert p6.VALIDATION_SEED not in calls
    assert candidate["development_seed_unseen_at_freeze"] == p6.DEVELOPMENT_SEED
    assert candidate["validation_seed_unseen_at_freeze"] == p6.VALIDATION_SEED


def test_p6_horizon_groups_are_causal_bridge_state_only():
    raw = p6._raw("fit", p6.FIT_SEED, p6.FIT_FAMILIES[:1], p6.FIT_DOMAINS[:2])
    caps = p6.p5.fit_velocity_caps(raw)
    prepared = p6._prepare(raw, caps)
    groups = p6._group(prepared)
    expected = np.where(prepared["bridge_horizon"].to_numpy(int) >= 3, "long", "direct_short")
    assert np.array_equal(groups.to_numpy(str), expected)


def test_p6_frozen_intervals_are_nested(tmp_path):
    candidate = p6.freeze(tmp_path, "test-sha")
    caps = candidate["velocity_caps"]
    transfer = p6._prepare(p6._raw("transfer", p6.TRANSFER_SEED, p6.TRANSFER_FAMILIES, p6.TRANSFER_DOMAINS), caps)
    sample = transfer[p6._available(transfer)].head(60)
    for axis in ("lateral", "altitude"):
        widths = p6.halfwidths(sample, candidate, axis)
        matrix = np.column_stack([widths[f"{q:.2f}"] for q in p6.TARGETS])
        assert np.all(np.diff(matrix, axis=1) >= -1e-12)


def test_p6_long_group_has_preregistered_minimum_on_transfer():
    fit_raw = p6._raw("fit", p6.FIT_SEED, p6.FIT_FAMILIES, p6.FIT_DOMAINS)
    caps = p6.p5.fit_velocity_caps(fit_raw)
    transfer = p6._prepare(p6._raw("transfer", p6.TRANSFER_SEED, p6.TRANSFER_FAMILIES, p6.TRANSFER_DOMAINS), caps)
    available = transfer[p6._available(transfer)].copy()
    counts = p6._group(available).value_counts().to_dict()
    assert counts.get("long", 0) >= p6.MIN_GROUP_COUNT
    assert counts.get("direct_short", 0) >= p6.MIN_GROUP_COUNT
