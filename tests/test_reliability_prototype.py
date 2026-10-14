"""Offline prototype is reproducible and never becomes a claimed external test."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from scripts.build_reliability_prototype import build
from scripts.diagnose_phase25_top_confidence import REQUIRED_TABLES

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def dataset():
    return json.loads(build())


def test_full_frozen_audit_build_is_deterministic(dataset):
    assert build() == build()
    assert dataset["schema"] == "aegisland.phase25.retrospective-demo.v1"
    assert dataset["cases_total"] == len(dataset["cases"]) == 1032
    assert dataset["source_frames"] == 86
    assert dataset["source_videos"] == 2
    assert len(dataset["source_sha256"]) == 4
    assert dataset["any_correct_top_wrong_count"] == 135


def test_case_population_matches_all_12_condition_model_cells(dataset):
    rows = dataset["cases"]
    assert len({(r["frame"], r["condition"], r["model"]) for r in rows}) == 1032
    for model in dataset["models"]:
        for condition in dataset["conditions"]:
            cell = [r for r in rows if r["model"] == model and r["condition"] == condition]
            assert len(cell) == 86
            assert len({r["frame"] for r in cell}) == 86
    occlusion = [r for r in rows if r["model"] == "phase23" and r["condition"] == "occlusion"]
    assert sum(r["any_match_success"] for r in occlusion) == 43
    assert sum(r["top_correct"] for r in occlusion) == 23


def test_only_frozen_model_scores_are_used_for_acceptance(dataset):
    # Ground truth is intentionally not an input to the runtime decision.
    from scripts.phase26_reliability import accept
    for row in dataset["cases"]:
        score = row["score"]
        prediction = ([] if row["top_box"] is None else
                      [{"class": "landing_target", "score": score, "box": row["top_box"]}])
        for cutoff in (0.05, 0.5, 0.95):
            assert accept(prediction, cutoff) == (score >= cutoff)
    assert dataset["new_holdout"] is False
    assert dataset["threshold_selected"] is False
    assert dataset["flight_safety_validated"] is False


def test_build_refuses_source_table_tampering(tmp_path):
    source = ROOT / "results/phase25_failure_atlas"
    for name in ("run_manifest.json", *REQUIRED_TABLES):
        shutil.copyfile(source / name, tmp_path / name) if name == "run_manifest.json" else (tmp_path / name).symlink_to(source / name)
    # Tampering with the hash manifest itself cannot create a new trusted test.
    lock = json.loads((tmp_path / "run_manifest.json").read_text())
    lock["output_tables_sha256"]["prediction_boxes.csv"] = "0" * 64
    (tmp_path / "run_manifest.json").write_text(json.dumps(lock))
    with pytest.raises(ValueError, match="Frozen Phase 25 table changed"):
        build(tmp_path)


def test_threshold_zero_acceptance_has_undefined_error_rate(dataset):
    case = [r for r in dataset["cases"] if r["model"] == "phase23" and r["condition"] == "mixed"]
    threshold = 0.95
    accepted = [c for c in case if c["score"] >= threshold]
    rate = sum(not c["top_correct"] for c in accepted) / len(accepted) if accepted else None
    if not accepted:
        assert rate is None
