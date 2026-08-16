from __future__ import annotations

import numpy as np

from scripts import run_phase11_p7_powered_horizon_calibration as p7


def test_p7_evidence_is_new_and_disjoint():
    prior = {33033, 63333, 44044, 55055, 66066, 77077, 88088, 99099, 101101, 112112, 121121, 132132, 143143, 154154, 165165, 176176, 187187, 198198, 209209, 220220, 231231, 242242, 253253, 264264, 275275, 286286, 297297}
    assert {p7.FIT_SEED, p7.CALIBRATION_SEED, p7.TRANSFER_SEED, p7.DEVELOPMENT_SEED, p7.VALIDATION_SEED}.isdisjoint(prior)
    groups = [set(p7.FIT_FAMILIES), set(p7.CALIBRATION_FAMILIES), set(p7.TRANSFER_FAMILIES), set(p7.DEVELOPMENT_FAMILIES), set(p7.VALIDATION_FAMILIES)]
    for i, left in enumerate(groups):
        for right in groups[i + 1:]:
            assert left.isdisjoint(right)


def test_p7_freeze_never_touches_development_or_validation(tmp_path, monkeypatch):
    calls = []
    original = p7.p6.p1.generate_split

    def guarded(name, seed, families, domains, frames=p7.FRAMES_PER_SEQUENCE):
        calls.append(seed)
        assert seed not in {p7.DEVELOPMENT_SEED, p7.VALIDATION_SEED}
        return original(name, seed, families, domains, frames=frames)

    monkeypatch.setattr(p7.p6.p1, "generate_split", guarded)
    candidate = p7.freeze(tmp_path, "test-sha")
    assert p7.DEVELOPMENT_SEED not in calls
    assert p7.VALIDATION_SEED not in calls
    assert candidate["development_seed_unseen_at_freeze"] == p7.DEVELOPMENT_SEED
    assert candidate["validation_seed_unseen_at_freeze"] == p7.VALIDATION_SEED


def test_p7_transfer_has_minimum_long_bridge_support():
    fit_raw = p7._raw("fit", p7.FIT_SEED, p7.FIT_FAMILIES, p7.FIT_DOMAINS)
    caps = p7.p6.p5.fit_velocity_caps(fit_raw)
    transfer = p7._prepare(p7._raw("transfer", p7.TRANSFER_SEED, p7.TRANSFER_FAMILIES, p7.TRANSFER_DOMAINS), caps)
    available = transfer[p7._available(transfer)].copy()
    counts = p7.p6._group(available).value_counts().to_dict()
    assert counts.get("long", 0) >= p7.MIN_GROUP_COUNT
    assert counts.get("direct_short", 0) >= p7.MIN_GROUP_COUNT


def test_p7_intervals_are_nested(tmp_path):
    candidate = p7.freeze(tmp_path, "test-sha")
    caps = candidate["velocity_caps"]
    transfer = p7._prepare(p7._raw("transfer", p7.TRANSFER_SEED, p7.TRANSFER_FAMILIES, p7.TRANSFER_DOMAINS), caps)
    sample = transfer[p7._available(transfer)].head(80)
    for axis in ("lateral", "altitude"):
        widths = p7.p6.halfwidths(sample, candidate, axis)
        matrix = np.column_stack([widths[f"{q:.2f}"] for q in p7.p6.TARGETS])
        assert np.all(np.diff(matrix, axis=1) >= -1e-12)
