"""Smoke tests for the VASE offline reliability signal analysis."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.analyze_vase_signals import compute_auroc


def test_compute_auroc_perfect_separation():
    """A perfect signal should yield AUROC = 1.0."""
    scores = [0.9, 0.8, 0.7, 0.1, 0.05, 0.01]
    labels = [1, 1, 1, 0, 0, 0]
    assert compute_auroc(scores, labels) == 1.0


def test_compute_auroc_inverse_separation():
    """A perfectly inverted signal should yield AUROC = 0.0."""
    scores = [0.01, 0.05, 0.1, 0.7, 0.8, 0.9]
    labels = [1, 1, 1, 0, 0, 0]
    assert compute_auroc(scores, labels) == 0.0


def test_compute_auroc_random_is_near_half():
    """A constant signal should yield AUROC = 0.5."""
    scores = [0.5, 0.5, 0.5, 0.5]
    labels = [1, 0, 1, 0]
    auroc = compute_auroc(scores, labels)
    assert auroc == 0.5


def test_compute_auroc_single_class_returns_none():
    """When all labels are the same, AUROC is undefined."""
    assert compute_auroc([0.9, 0.8], [1, 1]) is None
    assert compute_auroc([0.1, 0.2], [0, 0]) is None


def test_compute_auroc_length_mismatch_raises():
    """Mismatched lengths should raise ValueError."""
    with pytest.raises(ValueError, match="same length"):
        compute_auroc([0.5], [1, 0])


def test_signal_evaluation_json_schema():
    """If the analysis has been run, verify the output JSON schema."""
    output = ROOT / "results" / "vase_offline_signals" / "signal_evaluation.json"
    if not output.exists():
        pytest.skip("Signal evaluation not yet generated")
    data = json.loads(output.read_text(encoding="utf-8"))
    assert "signals" in data
    assert "tasks" in data
    for task in data["tasks"]:
        assert "task" in task
        assert "results" in task
        for result in task["results"]:
            assert "signal" in result
            auroc = result["auroc"]
            assert auroc is None or (0.0 <= auroc <= 1.0)


def test_signal_summary_csv_schema():
    """If the analysis has been run, verify the output CSV schema."""
    output = ROOT / "results" / "vase_offline_signals" / "signal_summary.csv"
    if not output.exists():
        pytest.skip("Signal summary not yet generated")
    with output.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) > 0
    for row in rows:
        assert "signal_name" in row
        assert "task" in row
        assert "auroc" in row
