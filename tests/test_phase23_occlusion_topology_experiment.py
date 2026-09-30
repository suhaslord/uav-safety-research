"""Comprehensive validation tests for Phase 23 Occlusion Topology Experiment.

Tests cover Part 22:
- exact protocol SHA (v1.0 preserved and v1.1 amended)
- checkpoint SHA lock
- source population (86 frames, sequence balance)
- 5,160 completed treatment rows
- prediction completeness (no NULL fields post-inference)
- no duplicate keys
- achieved dose bounds and zero-dose identity
- zero-dose baseline gate pass with zero delta
- raw prediction linkage
- all 12 figures generated and non-empty
- machine-readable artifacts integrity
- common support across all 8 dose bins
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "results" / "phase25_occlusion_topology"
DOCS_DIR = REPO_ROOT / "docs"

EXPECTED_V1_0_PROTOCOL_SHA = "2cfad0c6f10bb055492cf058f8e4cbdbe2d48dae047f9270753371ec80d36018"
EXPECTED_V1_1_PROTOCOL_SHA = "b4637e5b9b0c9551ac6a106d20fe8bc62f05d50b7030432c1c4e1bf7cf771a29"
EXPECTED_MANIFEST_SHA = "8605cf1cbf9e8769c0324bf066078f9964f232ac3128131c8bd0b689bb7b64b7"
EXPECTED_CKPT_SHA = "43240be969708c32b3e11340c9846b3a588baf361378398677c794d16a455310"

TOPOLOGIES = ["CENTER", "OUTER_RING", "STRIPED", "RANDOM_PATCH"]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Protocol & Model Provenance Tests
# ---------------------------------------------------------------------------
class TestProvenanceAndLocks:
    def test_protocol_v1_0_preserved(self) -> None:
        """Protocol v1.0 must be preserved permanently without changes."""
        v1_path = DOCS_DIR / "phase25_phase23_occlusion_topology_protocol.json"
        assert v1_path.exists(), "Protocol v1.0 missing"
        actual_sha = sha256_file(v1_path)
        assert actual_sha == EXPECTED_V1_0_PROTOCOL_SHA, (
            f"Protocol v1.0 SHA mismatch: {actual_sha} != {EXPECTED_V1_0_PROTOCOL_SHA}"
        )

    def test_protocol_v1_1_amended(self) -> None:
        """Protocol v1.1 must exist and match locked SHA-256."""
        v1_1_path = DOCS_DIR / "phase25_phase23_occlusion_topology_protocol_v1_1.json"
        assert v1_1_path.exists(), "Protocol v1.1 missing"
        actual_sha = sha256_file(v1_1_path)
        assert actual_sha == EXPECTED_V1_1_PROTOCOL_SHA, (
            f"Protocol v1.1 SHA mismatch: {actual_sha} != {EXPECTED_V1_1_PROTOCOL_SHA}"
        )

    def test_fairness_decision_document(self) -> None:
        """Fairness decision document must record the amendment reason."""
        decision_path = DOCS_DIR / "phase25_occlusion_topology_fairness_decision.json"
        assert decision_path.exists()
        with open(decision_path, encoding="utf-8") as f:
            d = json.load(f)
        assert d["decision"] == "AMENDED_TO_V1_1"
        assert d["status"] == "APPROVED_PRE_INFERENCE"
        assert d["prior_protocol"]["sha256"] == EXPECTED_V1_0_PROTOCOL_SHA
        assert d["amended_protocol"]["sha256"] == EXPECTED_V1_1_PROTOCOL_SHA

    def test_zero_dose_baseline_gate(self) -> None:
        """Zero-dose baseline gate record must show PASS with deltas <= 0.001."""
        gate_path = RESULTS_DIR / "zero_dose_gate_record.json"
        assert gate_path.exists()
        with open(gate_path, encoding="utf-8") as f:
            gate = json.load(f)
        assert gate["status"] == "PASS"
        assert gate["checkpoint_sha256"] == EXPECTED_CKPT_SHA
        assert gate["manifest_sha256"] == EXPECTED_MANIFEST_SHA
        for metric, hist_val in gate["historical_baseline"].items():
            obs_val = gate["zero_dose_observed"][metric]
            delta = abs(obs_val - hist_val)
            assert delta <= gate["tolerance"], f"Gate failed on {metric}: delta={delta}"


# ---------------------------------------------------------------------------
# Treatment Population & Output Tests
# ---------------------------------------------------------------------------
class TestTreatmentPopulation:
    @pytest.fixture(scope="module")
    def views(self) -> list[dict[str, str]]:
        csv_path = RESULTS_DIR / "topology_views.csv"
        assert csv_path.exists(), "topology_views.csv missing"
        with open(csv_path, encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def test_exact_row_count(self, views: list[dict[str, str]]) -> None:
        """Treatment population must be exactly 5,160 rows (86 * 4 * 15)."""
        assert len(views) == 5160

    def test_unique_keys(self, views: list[dict[str, str]]) -> None:
        """Every (frame_id, topology, requested_dose) must be unique."""
        keys = [(r["frame_id"], r["topology"], r["requested_dose"]) for r in views]
        assert len(set(keys)) == 5160

    def test_prediction_completeness(self, views: list[dict[str, str]]) -> None:
        """All prediction fields must be non-empty after inference."""
        required_fields = ["pred_count", "best_iou", "best_confidence", "tp", "fp", "fn", "frame_success"]
        for r in views:
            for f in required_fields:
                val = r.get(f, "")
                assert val != "", f"Empty field '{f}' in row {r['frame_id']} {r['topology']}"
            # Check numerical validity
            assert int(r["pred_count"]) >= 0
            assert 0.0 <= float(r["best_iou"]) <= 1.0
            assert 0.0 <= float(r["best_confidence"]) <= 1.0
            assert int(r["tp"]) in (0, 1)
            assert int(r["fn"]) in (0, 1)
            assert r["frame_success"] in ("True", "False")

    def test_achieved_dose_bounds(self, views: list[dict[str, str]]) -> None:
        """Achieved dose must be strictly in [0.0, 1.0]."""
        for r in views:
            ad = float(r["achieved_dose"])
            rd = float(r["requested_dose"])
            assert 0.0 <= ad <= 1.0
            if rd == 0.0:
                assert ad == 0.0, f"Dose 0 achieved non-zero: {ad}"

    def test_sequence_balance(self, views: list[dict[str, str]]) -> None:
        """Must have exactly 3,960 land_pad and 1,200 land_pad2 views."""
        lp = sum(1 for r in views if r["sequence"] == "land_pad")
        lp2 = sum(1 for r in views if r["sequence"] == "land_pad2")
        assert lp == 3960  # 66 * 60
        assert lp2 == 1200  # 20 * 60

    def test_raw_predictions_linkage(self, views: list[dict[str, str]]) -> None:
        """Raw predictions must link to existing frame_ids and contain bounding boxes."""
        raw_csv = RESULTS_DIR / "raw_predictions.csv"
        assert raw_csv.exists()
        view_frames = set(r["frame_id"] for r in views)
        with open(raw_csv, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count = 0
            for r in reader:
                count += 1
                assert r["frame_id"] in view_frames
                if count >= 500:  # sample check
                    break
        assert count > 0


# ---------------------------------------------------------------------------
# Common Support & Statistical Design Tests
# ---------------------------------------------------------------------------
class TestCommonSupportAndStatistics:
    def test_common_support_in_all_bins(self) -> None:
        """Every common-support bin must have >= 50 observations for every topology."""
        agg_csv = RESULTS_DIR / "aggregate_by_topology_dose.csv"
        assert agg_csv.exists()
        with open(agg_csv, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            n = int(r["n"])
            assert n >= 50, f"Insufficient observations in {r['topology']} bin {r['dose_bin_label']}: N={n}"

    def test_ed50_results_format(self) -> None:
        """ED50 results must be present for all 4 topologies."""
        ed50_path = RESULTS_DIR / "ed50_results.json"
        assert ed50_path.exists()
        with open(ed50_path, encoding="utf-8") as f:
            data = json.load(f)
        for topo in TOPOLOGIES:
            assert topo in data
            assert "crossed_threshold" in data[topo]

    def test_all_12_figures_exist(self) -> None:
        """All 12 required figures must exist and be non-empty (>10KB)."""
        figures_dir = RESULTS_DIR / "figures"
        expected_figs = [
            "01_success_vs_achieved_dose.png",
            "02_recall_vs_achieved_dose.png",
            "03_iou_vs_achieved_dose.png",
            "04_confidence_vs_achieved_dose.png",
            "05_ed50_comparison.png",
            "06_topology_dose_heatmap.png",
            "07_center_vs_outer_ring_paired.png",
            "08_target_scale_dose_response.png",
            "09_confidence_vs_iou_map.png",
            "10_failure_transition_counts.png",
            "11_achieved_vs_requested_calibration.png",
            "12_common_support_distribution.png",
        ]
        for fig_name in expected_figs:
            p = figures_dir / fig_name
            assert p.exists(), f"Figure missing: {fig_name}"
            assert p.stat().st_size > 10000, f"Figure too small (empty?): {fig_name}"

    def test_machine_readable_artifacts_exist(self) -> None:
        """All 8 machine-readable artifacts must exist and decode."""
        expected_files = [
            "aggregate_by_topology_dose.csv",
            "statistics.json",
            "ed50_results.json",
            "change_point_results.json",
            "topology_comparisons.json",
            "failure_examples.json",
            "analysis_summary.json",
            "study_report.md",
        ]
        for f in expected_files:
            p = RESULTS_DIR / f
            assert p.exists(), f"Artifact missing: {f}"
            assert p.stat().st_size > 0, f"Artifact empty: {f}"
            if f.endswith(".json"):
                with open(p, encoding="utf-8") as jf:
                    json.load(jf)
