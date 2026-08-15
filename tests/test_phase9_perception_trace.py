from __future__ import annotations

from pathlib import Path
import json

import pandas as pd
import pytest

from scripts.generate_phase9_perception_fixture import generate_fixture
from uav_safety.perception_trace import PHASE9_PERCEPTION_TRACE_SCHEMA, validate_perception_trace


def _fixture(tmp_path: Path) -> tuple[Path, pd.DataFrame]:
    out = tmp_path / "fixture"
    generate_fixture(out, rows=24, seed=909090)
    return out, pd.read_csv(out / "perception_trace.csv")


def test_phase9_fixture_verifies_raw_frame_hashes(tmp_path: Path) -> None:
    root, frame = _fixture(tmp_path)
    normalized, report = validate_perception_trace(frame, frame_root=root, verify_frame_hashes=True)
    assert len(normalized) == 24
    assert report.verified_frame_hashes == 24
    assert report.duration_s > 1.0
    assert report.paired_observation_samples > 0

    metadata = json.loads((root / "fixture_metadata.json").read_text(encoding="utf-8"))
    assert metadata["schema"] == PHASE9_PERCEPTION_TRACE_SCHEMA
    assert metadata["external_perception_evidence_status"] == "fixture_non_authoritative"
    assert metadata["claim_level"] == "pipeline_validation_only"
    assert metadata["controller_tuning_allowed"] is False
    assert metadata["safety_acceptance"] is False
    assert metadata["simulation_only"] is True


def test_unavailable_observation_cannot_hide_zero_sentinels(tmp_path: Path) -> None:
    _, frame = _fixture(tmp_path)
    row = frame.index[~frame["observation_available"].astype(bool)][0]
    frame.loc[row, "observed_lateral_x_m"] = 0.0
    with pytest.raises(ValueError, match="must be missing when observation_available is false"):
        validate_perception_trace(frame)


def test_visible_truth_requires_pixel_geometry(tmp_path: Path) -> None:
    _, frame = _fixture(tmp_path)
    row = frame.index[frame["truth_target_visible"].astype(bool)][0]
    frame.loc[row, "truth_center_x_px"] = float("nan")
    with pytest.raises(ValueError, match="truth_center_x_px must be present"):
        validate_perception_trace(frame)


def test_frame_path_must_be_safe_relative_path(tmp_path: Path) -> None:
    _, frame = _fixture(tmp_path)
    frame.loc[0, "frame_path"] = "../outside.pgm"
    with pytest.raises(ValueError, match="safe relative path"):
        validate_perception_trace(frame)


def test_frame_hash_tampering_is_detected(tmp_path: Path) -> None:
    root, frame = _fixture(tmp_path)
    frame.loc[0, "frame_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        validate_perception_trace(frame, frame_root=root, verify_frame_hashes=True)


def test_hash_verification_requires_frame_root(tmp_path: Path) -> None:
    _, frame = _fixture(tmp_path)
    with pytest.raises(ValueError, match="frame_root is required"):
        validate_perception_trace(frame, verify_frame_hashes=True)


def test_perception_trace_rejects_nonmonotonic_frame_indices(tmp_path: Path) -> None:
    _, frame = _fixture(tmp_path)
    frame.loc[1, "frame_index"] = frame.loc[0, "frame_index"]
    with pytest.raises(ValueError, match="frame_index must be strictly increasing"):
        validate_perception_trace(frame)
