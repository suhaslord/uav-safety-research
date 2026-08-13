from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from uav_safety.nakahira_metrics import recovery_outcome, terminal_failure, wilson_interval


def test_non_recovery_is_null_not_fake_large_time():
    t = np.arange(0.0, 2.0, 0.1)
    degraded = t >= 0.5
    recovery = np.zeros_like(degraded, dtype=bool)
    result = recovery_outcome(t, degraded, recovery, onset_s=0.0, dwell_s=0.3)
    assert result["degraded_entered"] is True
    assert result["recovered"] is False
    assert result["non_recovery"] is True
    assert result["recovery_time_s"] is None


def test_sustained_recovery_uses_first_full_dwell():
    t = np.arange(0.0, 2.1, 0.1)
    degraded = t >= 0.4
    recovery = (t >= 0.8) & (t <= 1.5)
    result = recovery_outcome(t, degraded, recovery, onset_s=0.0, dwell_s=0.5)
    assert result["recovered"] is True
    assert result["non_recovery"] is False
    assert abs(result["recovery_time_s"] - 0.4) < 1e-9


def test_never_degraded_has_zero_recovery_time_and_is_not_censored():
    t = np.arange(0.0, 1.0, 0.1)
    result = recovery_outcome(
        t,
        np.zeros_like(t, dtype=bool),
        np.ones_like(t, dtype=bool),
        onset_s=0.0,
        dwell_s=0.2,
    )
    assert result["degraded_entered"] is False
    assert result["recovered"] is True
    assert result["non_recovery"] is False
    assert result["recovery_time_s"] == 0.0


def test_terminal_failure_definition_keeps_safe_abort_separate():
    failure_outcomes = ["unsafe_touchdown", "timeout"]
    assert terminal_failure("unsafe_touchdown", failure_outcomes)
    assert terminal_failure("timeout", failure_outcomes)
    assert not terminal_failure("safe_abort", failure_outcomes)
    assert not terminal_failure("success", failure_outcomes)


def test_wilson_interval_bounds():
    low, high = wilson_interval(2, 10)
    assert 0.0 <= low <= 0.2 <= high <= 1.0


def test_frozen_config_separates_evidence_and_excludes_combinations():
    cfg = json.loads(Path("configs/nakahira_uncertainty_frozen_v1.json").read_text())
    dev = set(cfg["evidence"]["development_seeds"])
    held = set(cfg["evidence"]["heldout_seeds"])
    assert dev
    assert held
    assert dev.isdisjoint(held)
    assert cfg["frozen_before_heldout"] is True
    assert cfg["analysis"]["combinations_in_final_sweep"] is False
    assert cfg["failure_definition"]["safe_abort_is_failure"] is False
    assert cfg["mandatory_separate_outcome"] == "non_recovery_probability"
    assert cfg["simulation_only"] is True
    assert cfg["safety_acceptance"] is False


def test_exact_frozen_cell_shape():
    cfg = json.loads(Path("configs/nakahira_uncertainty_frozen_v1.json").read_text())
    cells = cfg["cells"]
    assert len(cells) == 13
    nominal = [c for c in cells if c["dimension"] == "nominal"]
    assert len(nominal) == 1
    for dimension in (
        "pose_perception_noise",
        "partial_observability",
        "sensor_latency",
        "stale_reference",
    ):
        levels = sorted(c["severity_level"] for c in cells if c["dimension"] == dimension)
        assert levels == [1, 2, 3]
