"""Automated verification tests for Phase 23 frame-level reconstruction and paired failure atlas study."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_BUNDLE_SHA = "a55531930988deeadf81853d00b63c7e589c6b7fd2270f57653abdb5cdd3e55d"
EXPECTED_CKPT_SHA = "43240be969708c32b3e11340c9846b3a588baf361378398677c794d16a455310"
EXPECTED_MANIFEST_SHA = "8605cf1cbf9e8769c0324bf066078f9964f232ac3128131c8bd0b689bb7b64b7"
CONDITIONS = ("clean", "blur", "low_light", "noise", "occlusion", "mixed")

ATLAS_DIR = ROOT / "results/phase25_failure_atlas"
PROTOCOL_PATH = ROOT / "docs/phase25_paired_study_protocol.json"


@pytest.fixture(scope="module")
def protocol() -> dict:
    assert PROTOCOL_PATH.is_file(), f"Protocol file missing: {PROTOCOL_PATH}"
    return json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def paired_rows() -> list[dict[str, str]]:
    path = ATLAS_DIR / "paired_frame_outcomes.csv"
    assert path.is_file(), f"Paired outcomes file missing: {path}"
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def p23_frame_metrics() -> list[dict[str, str]]:
    path = ATLAS_DIR / "phase23_frame_metrics.csv"
    assert path.is_file(), f"Phase 23 frame metrics missing: {path}"
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def reconciliation() -> dict:
    path = ATLAS_DIR / "phase23_frame_reconciliation.json"
    assert path.is_file(), f"Reconciliation file missing: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def statistics() -> dict:
    path = ATLAS_DIR / "paired_statistics.json"
    assert path.is_file(), f"Statistics file missing: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def test_frozen_protocol_integrity(protocol: dict):
    assert protocol["status"] == "frozen"
    assert protocol["phase23_release"]["checkpoint_sha256"] == EXPECTED_CKPT_SHA
    assert protocol["phase23_release"]["bundle_sha256"] == EXPECTED_BUNDLE_SHA
    assert protocol["dataset"]["manifest_sha256"] == EXPECTED_MANIFEST_SHA
    assert protocol["dataset"]["source_frame_count"] == 86
    assert protocol["dataset"]["total_views"] == 516
    assert set(protocol["dataset"]["conditions"]) == set(CONDITIONS)


def test_exactly_86_unique_source_frames(paired_rows: list[dict[str, str]]):
    frames = {r["frame_id"] for r in paired_rows}
    assert len(frames) == 86, f"Expected 86 unique source frames, got {len(frames)}"


def test_exactly_516_paired_views_all_conditions(paired_rows: list[dict[str, str]]):
    assert len(paired_rows) == 516, f"Expected 516 views, got {len(paired_rows)}"
    counts = {}
    for r in paired_rows:
        counts[r["condition"]] = counts.get(r["condition"], 0) + 1
    assert set(counts.keys()) == set(CONDITIONS)
    for c in CONDITIONS:
        assert counts[c] == 86, f"Condition {c} has {counts[c]} views, expected 86"


def test_no_duplicate_frame_condition_keys(
    paired_rows: list[dict[str, str]],
    p23_frame_metrics: list[dict[str, str]],
):
    paired_keys = [(r["frame_id"], r["condition"]) for r in paired_rows]
    assert len(paired_keys) == len(set(paired_keys)), "Duplicate (frame_id, condition) in paired_frame_outcomes.csv"

    metric_keys = [(r["frame_id"], r["condition"]) for r in p23_frame_metrics]
    assert len(metric_keys) == len(set(metric_keys)), "Duplicate (frame_id, condition) in phase23_frame_metrics.csv"
    assert set(paired_keys) == set(metric_keys), "Key mismatch between paired outcomes and Phase 23 frame metrics"


def test_predictions_map_to_protected_frames(paired_rows: list[dict[str, str]]):
    valid_frames = {r["frame_id"] for r in paired_rows}
    pred_path = ATLAS_DIR / "phase23_frame_predictions.csv"
    assert pred_path.is_file(), f"Predictions file missing: {pred_path}"

    with pred_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for r in reader:
            count += 1
            assert r["frame_id"] in valid_frames, f"Prediction frame {r['frame_id']} not in protected test set"
            assert r["condition"] in CONDITIONS, f"Invalid condition {r['condition']}"
            assert 0.0 <= float(r["confidence"]) <= 1.0, f"Confidence out of range: {r['confidence']}"
            assert 0.0 <= float(r["match_iou"]) <= 1.0, f"IoU out of range: {r['match_iou']}"
    assert count > 0, "No predictions found in phase23_frame_predictions.csv"


def test_outcome_labels_follow_definitions(paired_rows: list[dict[str, str]]):
    counts = {"RECOVERED": 0, "REGRESSED": 0, "BOTH PASS": 0, "BOTH FAIL": 0}
    for r in paired_rows:
        b_pass = r["baseline_pass"].lower() == "true"
        p_pass = r["phase23_pass"].lower() == "true"
        outcome = r["paired_outcome"]

        if not b_pass and p_pass:
            assert outcome == "RECOVERED", f"Expected RECOVERED, got {outcome}"
        elif b_pass and not p_pass:
            assert outcome == "REGRESSED", f"Expected REGRESSED, got {outcome}"
        elif b_pass and p_pass:
            assert outcome == "BOTH PASS", f"Expected BOTH PASS, got {outcome}"
        else:
            assert outcome == "BOTH FAIL", f"Expected BOTH FAIL, got {outcome}"
        counts[outcome] += 1

    assert counts["BOTH PASS"] == 223
    assert counts["BOTH FAIL"] == 179
    assert counts["REGRESSED"] == 65
    assert counts["RECOVERED"] == 49
    assert sum(counts.values()) == 516


def test_no_impossible_tp_fp_fn_values(p23_frame_metrics: list[dict[str, str]]):
    for r in p23_frame_metrics:
        gt = int(r["gt_count"])
        tp = int(r["tp"])
        fp = int(r["fp"])
        fn = int(r["fn"])
        succ = r["frame_success"].lower() == "true"

        assert gt == 1, f"Expected 1 GT target per frame, got {gt}"
        assert tp in (0, 1), f"Impossible TP: {tp}"
        assert fn in (0, 1), f"Impossible FN: {fn}"
        assert tp + fn == gt, f"TP + FN ({tp} + {fn}) != GT ({gt})"
        assert fp >= 0, f"Negative FP: {fp}"
        assert succ == (tp == 1 and fn == 0)


def test_reconciliation_exact_zero_delta(reconciliation: dict):
    assert reconciliation["status"] == "PASS"
    assert reconciliation["checkpoint_sha256"] == EXPECTED_CKPT_SHA
    assert reconciliation["bundle_sha256"] == EXPECTED_BUNDLE_SHA
    assert reconciliation["total_cells_checked"] == 24
    assert reconciliation["cells_matched"] == 24
    assert reconciliation["max_absolute_delta"] <= 0.001

    for c in CONDITIONS:
        cond_data = reconciliation["conditions"][c]
        assert cond_data["status"] == "MATCHED_EXACT"
        delta = cond_data["delta"]
        for metric, d in delta.items():
            assert abs(d) <= 0.001, f"Metric {metric} in condition {c} has delta {d}"


def test_statistics_and_deterministic_seed(statistics: dict):
    meta = statistics["metadata"]
    assert meta["total_views"] == 516
    assert meta["unique_source_frames"] == 86
    assert meta["bootstrap_seed"] == 20260922
    assert meta["bootstrap_replicates"] == 1000

    overall = statistics["overall"]
    assert overall["recovered_count"] == 49
    assert overall["regressed_count"] == 65
    assert overall["both_pass_count"] == 223
    assert overall["both_fail_count"] == 179
    assert overall["phase23_pass_count"] == 272
    assert overall["baseline_pass_count"] == 288

    ci = overall["success_rate_delta_ci95"]
    assert len(ci) == 2
    assert ci[0] < ci[1]
    # Check that CI spans zero
    assert ci[0] <= 0.0 <= ci[1]


def test_top_failure_examples_structure():
    path = ATLAS_DIR / "top_failure_examples.json"
    assert path.is_file(), f"Top failure examples missing: {path}"
    data = json.loads(path.read_text(encoding="utf-8"))

    expected_cats = [
        "strongest_recoveries",
        "strongest_regressions",
        "both_fail_cases",
        "high_confidence_localization_failures",
        "occlusion_failures",
    ]
    for cat in expected_cats:
        assert cat in data, f"Missing category {cat}"
        assert len(data[cat]) > 0, f"Category {cat} is empty"


def test_publication_figures_and_report_exist():
    fig_dir = ATLAS_DIR / "figures"
    assert fig_dir.is_dir(), f"Figures directory missing: {fig_dir}"

    expected_figs = [
        "paired_outcome_counts_by_condition.png",
        "success_rate_comparison.png",
        "recovered_vs_regressed.png",
        "iou_change_distribution.png",
        "confidence_change_distribution.png",
        "performance_vs_target_area.png",
        "performance_vs_brightness.png",
        "performance_vs_sharpness.png",
        "occlusion_failure_analysis.png",
        "paired_transition_matrix.png",
    ]
    for fig_name in expected_figs:
        fig_path = fig_dir / fig_name
        assert fig_path.is_file(), f"Figure missing: {fig_name}"
        assert fig_path.stat().st_size > 1000, f"Figure {fig_name} is too small / empty"

    report_path = ATLAS_DIR / "paired_study_report.md"
    assert report_path.is_file(), f"Report missing: {report_path}"
    text = report_path.read_text(encoding="utf-8")
    assert "Observations" in text
    assert "Interpretations" in text
    assert "Unproven Hypotheses" in text
    assert "Limitations" in text
