from __future__ import annotations

import numpy as np

from scripts import run_phase11_p4_all_available_calibration as p4


def test_p4_seeds_and_families_are_new():
    prior = {33033, 63333, 44044, 55055, 66066, 77077, 88088, 99099, 101101, 112112, 121121, 132132, 143143, 154154}
    assert {p4.FIT_SEED, p4.CALIBRATION_SEED, p4.TRANSFER_SEED, p4.VALIDATION_SEED}.isdisjoint(prior)
    groups = [set(p4.FIT_FAMILIES), set(p4.CALIBRATION_FAMILIES), set(p4.TRANSFER_FAMILIES), set(p4.VALIDATION_FAMILIES)]
    for i, left in enumerate(groups):
        for right in groups[i + 1 :]:
            assert left.isdisjoint(right)


def test_p4_freeze_cannot_touch_validation_seed(tmp_path, monkeypatch):
    calls: list[int] = []
    original = p4.p1.generate_split

    def guarded(name, seed, families, domains, frames=p4.FRAMES_PER_SEQUENCE):
        calls.append(seed)
        assert seed != p4.VALIDATION_SEED
        return original(name, seed, families, domains, frames=frames)

    monkeypatch.setattr(p4.p1, "generate_split", guarded)
    candidate = p4.freeze(tmp_path, "test-sha")
    assert p4.VALIDATION_SEED not in calls
    assert candidate["validation_seed_unseen_at_freeze"] == p4.VALIDATION_SEED


def test_p4_standardized_design_is_finite_and_low_capacity():
    fit = p4._prepare("fit", p4.FIT_SEED, p4.FIT_FAMILIES[:1], p4.FIT_DOMAINS[:2])
    d = fit[p4._available(fit)].head(20)
    standardizer = p4._fit_standardizer(d)
    x = p4._design(d, standardizer)
    assert x.shape[1] == 18
    assert np.all(np.isfinite(x))


def test_p4_intervals_are_nested():
    fit = p4._prepare("fit", p4.FIT_SEED, p4.FIT_FAMILIES[:1], p4.FIT_DOMAINS[:2])
    cal = p4._prepare("calibration", p4.CALIBRATION_SEED, p4.CALIBRATION_FAMILIES[:1], p4.FIT_DOMAINS[:2])
    transfer = p4._prepare("transfer", p4.TRANSFER_SEED, p4.TRANSFER_FAMILIES[:1], p4.TRANSFER_DOMAINS[:2])
    candidate = p4._build_candidate(fit, cal, transfer, "test-sha")
    d = transfer[p4._available(transfer)].head(20)
    for axis in ("lateral", "altitude"):
        widths = p4.final_halfwidths(d, candidate, axis)
        matrix = np.column_stack([widths[f"{q:.2f}"] for q in p4.TARGETS])
        assert np.all(np.diff(matrix, axis=1) >= -1e-12)
