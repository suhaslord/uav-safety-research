import csv
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_phase24_outputs_reconcile_to_phase23_aggregates():
    path = ROOT / "results/phase23_robust_detector/robustness_comparison.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        source = list(csv.DictReader(handle))
    result = json.loads((ROOT / "results/phase24_robustness_audit/summary.json").read_text())
    web = json.loads((ROOT / "deploy/vercel/data/phase24-results.json").read_text())

    assert result == web
    assert [row["condition"] for row in result["conditions"]] == [row["condition"] for row in source]
    for raw, row in zip(source, result["conditions"], strict=True):
        assert abs(float(raw["baseline_recall"]) - row["baseline"]["recall"]) < 1e-12
        assert abs(float(raw["phase23_recall"]) - row["phase23"]["recall"]) < 1e-12
        assert abs(float(raw["baseline_map50"]) - row["baseline"]["map50"]) < 1e-12
        assert abs(float(raw["phase23_map50"]) - row["phase23"]["map50"]) < 1e-12


def test_phase24_surfaces_macro_gain_and_severe_tail_regression():
    result = json.loads((ROOT / "results/phase24_robustness_audit/summary.json").read_text())
    summary = result["summary"]
    assert summary["map50_improved_conditions"] == ["clean", "blur", "low_light", "noise"]
    assert summary["map50_regressed_conditions"] == ["occlusion", "mixed"]
    assert abs(summary["macro_map50"]["delta"] - 0.0343847121) < 1e-9
    assert abs(summary["macro_recall"]["delta"] - 0.0723458363) < 1e-9
    assert abs(summary["severe_tail"]["macro_map50_delta"] + 0.1329199277) < 1e-9
    assert summary["severe_tail"]["macro_map50_relative_percent"] < -49
    assert summary["severe_tail"]["macro_recall_relative_percent"] < -36


def test_phase24_labels_reanalysis_and_reuses_one_holdout():
    result = json.loads((ROOT / "results/phase24_robustness_audit/summary.json").read_text())
    assert result["analysis_type"] == "descriptive_reanalysis"
    assert result["new_model_training"] is False
    assert result["new_predictions_generated"] is False
    assert result["dataset"]["heldout_test_frames"] == 86
    assert result["dataset"]["same_temporal_holdout_reused_across_conditions"] is True
    assert result["dataset"]["condition_views_are_independent_samples"] is False
    assert result["method"]["confidence_intervals"] is None
    assert result["limits"]["safety_acceptance"] is False
    assert result["limits"]["controller_tuning_allowed"] is False


def test_phase24_analyzer_is_reproducible():
    run = subprocess.run(
        [sys.executable, str(ROOT / "scripts/analyze_phase24_robustness_frontier.py"), "--root", str(ROOT)],
        check=True, capture_output=True, text=True,
    )
    assert "Wrote Phase 24 audit" in run.stdout
