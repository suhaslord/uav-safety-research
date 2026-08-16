from __future__ import annotations

import numpy as np

from scripts import run_phase11_p3_learned_scale_transfer as p3


def test_p3_evidence_is_disjoint_from_seen_phase11_seeds():
    seen = {33033, 63333, 44044, 55055, 66066, 77077, 88088, 99099, 101101, 112112}
    assert {p3.FIT_SEED, p3.CALIBRATION_SEED, p3.TRANSFER_SEED, p3.VALIDATION_SEED}.isdisjoint(seen)
    groups = [set(p3.FIT_FAMILIES), set(p3.CALIBRATION_FAMILIES), set(p3.TRANSFER_FAMILIES), set(p3.VALIDATION_FAMILIES)]
    for i, left in enumerate(groups):
        for right in groups[i + 1 :]:
            assert left.isdisjoint(right)


def test_p3_basis_has_no_hand_multiplier_and_expected_low_capacity_shape():
    fit = p3._prepare("fit", p3.FIT_SEED, p3.FIT_FAMILIES[:1], p3.FIT_DOMAINS[:2])
    available = fit[p3._available(fit)].head(8)
    basis = p3._scale_basis(available)
    assert basis.shape[1] == 21
    assert np.all(np.isfinite(basis))


def test_p3_freeze_does_not_touch_validation_seed(tmp_path, monkeypatch):
    calls: list[int] = []
    original = p3.p1.generate_split

    def guarded(name, seed, families, domains, frames=p3.FRAMES_PER_SEQUENCE):
        calls.append(seed)
        assert seed != p3.VALIDATION_SEED
        return original(name, seed, families, domains, frames=frames)

    monkeypatch.setattr(p3.p1, "generate_split", guarded)
    candidate = p3.freeze(tmp_path, "test-sha")
    assert p3.VALIDATION_SEED not in calls
    assert candidate["validation_seed_unseen_at_freeze"] == p3.VALIDATION_SEED


def test_p3_final_intervals_are_nested():
    fit = p3._prepare("fit", p3.FIT_SEED, p3.FIT_FAMILIES[:1], p3.FIT_DOMAINS[:2])
    calibration = p3._prepare("calibration", p3.CALIBRATION_SEED, p3.CALIBRATION_FAMILIES[:1], p3.FIT_DOMAINS[:2])
    transfer = p3._prepare("transfer", p3.TRANSFER_SEED, p3.TRANSFER_FAMILIES[:1], p3.TRANSFER_DOMAINS[:2])
    candidate = p3._build_candidate(fit, calibration, transfer, "test-sha")
    subset = transfer[p3._available(transfer)].head(20)
    for axis in ("lateral", "altitude"):
        widths = p3.final_halfwidths(subset, candidate, axis)
        matrix = np.column_stack([widths[f"{q:.2f}"] for q in p3.TARGETS])
        assert np.all(np.diff(matrix, axis=1) >= -1e-12)
