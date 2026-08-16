from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import run_phase11_p1_adaptive_reliability as p1


def test_p1_freeze_constants_and_split_separation() -> None:
    assert p1.FIT_SEED == 44044
    assert p1.CALIBRATION_SEED == 55055
    assert p1.DEVELOPMENT_SEED == 66066
    assert p1.VALIDATION_SEED == 77077
    assert len({p1.FIT_SEED, p1.CALIBRATION_SEED, p1.DEVELOPMENT_SEED, p1.VALIDATION_SEED}) == 4

    family_sets = [
        set(p1.FIT_FAMILIES),
        set(p1.CALIBRATION_FAMILIES),
        set(p1.DEVELOPMENT_FAMILIES),
        set(p1.VALIDATION_FAMILIES),
    ]
    for i, left in enumerate(family_sets):
        for right in family_sets[i + 1 :]:
            assert left.isdisjoint(right)

    assert set(p1.DEVELOPMENT_DOMAINS).isdisjoint(set(p1.VALIDATION_DOMAINS))
    assert sum(p1.RISK_WEIGHTS.values()) == pytest.approx(1.0)
    assert p1.MAX_BRIDGE_GAP == 2
    assert p1.COACTIVATION_THRESHOLD == pytest.approx(0.45)
    assert p1.SEVERITY_COACTIVATION_WEIGHT == pytest.approx(0.75)
    assert p1.SEVERITY_BRIDGE_WEIGHT == pytest.approx(0.25)
    assert p1.ACCEPTANCE_THRESHOLD == pytest.approx(0.40078671864763)
    assert p1.RIDGE_LAMBDA == pytest.approx(1.0)
    assert p1.MULTIPLIER_COACTIVATION == pytest.approx(3.0)
    assert p1.MULTIPLIER_RISK == pytest.approx(6.0)
    assert p1.MULTIPLIER_BRIDGE == pytest.approx(2.0)


def test_p1_generation_is_deterministic_without_validation_exposure() -> None:
    a = p1.generate_split("probe", 123456, (31,), ("edge+dim",), frames=5)
    b = p1.generate_split("probe", 123456, (31,), ("edge+dim",), frames=5)
    pd.testing.assert_frame_equal(a, b, check_exact=True)
    assert set(a["seed"]) == {123456}
    assert set(a["family"]) == {31}
    assert set(a["domain"]) == {"edge+dim"}


def test_temporal_bridge_is_short_horizon_and_nonrecursive() -> None:
    rows = []
    for frame in range(5):
        available = frame in (0, 1)
        rows.append(
            {
                "sequence_id": "s",
                "frame_index": frame,
                "candidate_available": available,
                "candidate_source": "known_aruco_refined" if available else None,
                "estimate_lateral_x_m": float(frame) if available else np.nan,
                "estimate_altitude_m": 2.0 + float(frame) if available else np.nan,
                "truth_lateral_x_m": float(frame),
                "truth_altitude_m": 2.0 + float(frame),
            }
        )
    bridged = p1.add_temporal_bridge(pd.DataFrame(rows))

    assert list(bridged["p1_available"]) == [True, True, True, True, False]
    assert list(bridged["bridge_horizon"]) == [0, 0, 1, 2, 0]
    assert bridged.loc[2, "p1_source"] == "temporal_bridge"
    assert bridged.loc[3, "p1_source"] == "temporal_bridge"
    assert bridged.loc[2, "p1_estimate_lateral_x_m"] == pytest.approx(2.0)
    assert bridged.loc[3, "p1_estimate_lateral_x_m"] == pytest.approx(3.0)
    assert np.isnan(bridged.loc[4, "p1_estimate_lateral_x_m"])


def test_validation_cli_is_blocked_without_explicit_exposure_ack(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "run_phase11_p1_adaptive_reliability.py"
    out = tmp_path / "blocked-validation"
    proc = subprocess.run(
        [sys.executable, str(script), "--stage", "validation", "--out", str(out)],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode != 0
    assert "validation blocked" in (proc.stdout + proc.stderr)
    assert not out.exists()


def test_seen_development_checkpoint_reproduces_exact_frozen_candidate(tmp_path: Path) -> None:
    result = p1.write_outputs(tmp_path / "p1-dev", "development", "test-freeze")
    gates = result["gates"]

    h1 = gates["h1_selective_coverage_transfer"]
    assert h1["pass"] is True
    assert h1["lateral_95_coverage"] == pytest.approx(0.9365079365079365, abs=1e-12)
    assert h1["altitude_95_coverage"] == pytest.approx(0.9454365079365079, abs=1e-12)

    h2 = gates["h2_interval_efficiency"]
    assert h2["pass"] is True
    assert h2["lateral_efficiency_ratio"] == pytest.approx(1.1011, rel=5e-4)
    assert h2["altitude_efficiency_ratio"] == pytest.approx(1.2867, rel=5e-4)

    h3 = gates["h3_useful_selective_reliability"]
    assert h3["pass"] is True
    assert h3["lateral_p95_improvement"] == pytest.approx(0.468026, rel=5e-4)
    assert h3["altitude_p95_improvement"] == pytest.approx(0.421259, rel=5e-4)
    assert h3["usable_availability"] == pytest.approx(0.70, abs=1e-12)

    h4 = gates["h4_shift_discrimination"]
    assert h4["pass"] is True
    assert h4["trajectory_level_auroc"] == pytest.approx(0.953125, abs=1e-12)
    assert result["all_primary_gates_pass"] is True
