from __future__ import annotations

import json

import numpy as np
import pandas as pd

from uav_safety.provenance import validate_result_manifest
from uav_safety.trace_validation import (
    PHASE8_RESULT_MANIFEST_SCHEMA,
    PHASE8_TRACE_COMPARISON_SCHEMA,
    compare_external_traces,
    render_phase8_report,
    write_phase8_comparison,
)


def make_trace(*, error_scale: float = 1.0, lateral_bias: float = 0.0, rows: int = 80) -> pd.DataFrame:
    data = []
    for i in range(rows):
        t = 0.05 * i
        truth_x = 0.8 * np.exp(-0.018 * i) * np.cos(0.08 * i)
        truth_z = max(0.0, 4.0 - 0.035 * i)
        truth_vx = -0.03 * np.sin(0.08 * i)
        truth_vz = -0.7 if truth_z > 0.2 else -0.1
        image_error = error_scale * (0.04 * np.sin(0.21 * i) + 0.015 * np.cos(0.07 * i)) + lateral_bias
        reference_error = error_scale * (0.025 * np.sin(0.19 * i + 0.3)) + 0.35 * lateral_bias
        image_z_error = error_scale * 0.035 * np.cos(0.15 * i)
        reference_z_error = error_scale * 0.02 * np.sin(0.13 * i)
        image_dropped = i % 23 == 7
        reference_available = i % 19 != 11
        reference_fresh = reference_available and i % 2 == 0
        data.append({
            "t_s": t,
            "truth_x_m": truth_x,
            "truth_z_m": truth_z,
            "truth_vx_mps": truth_vx,
            "truth_vz_mps": truth_vz,
            "image_x_m": truth_x + image_error,
            "image_z_m": truth_z + image_z_error,
            "image_vx_mps": truth_vx + error_scale * 0.02 * np.sin(0.17 * i),
            "image_vz_mps": truth_vz + error_scale * 0.03 * np.cos(0.11 * i),
            "image_confidence": max(0.05, min(0.99, 0.86 - 1.8 * abs(image_error))),
            "image_sigma_pos_m": 0.10 + 0.35 * abs(image_error),
            "image_dropped": image_dropped,
            "reference_x_m": truth_x + reference_error,
            "reference_z_m": truth_z + reference_z_error,
            "reference_vx_mps": truth_vx + error_scale * 0.012 * np.cos(0.09 * i),
            "reference_vz_mps": truth_vz + error_scale * 0.018 * np.sin(0.10 * i),
            "reference_sigma_pos_m": 0.12 + 0.25 * abs(reference_error),
            "reference_available": reference_available,
            "reference_fresh": reference_fresh,
            "image_transport_latency_s": 0.015 + 0.002 * (i % 3),
            "reference_transport_latency_s": 0.045 + 0.01 * (i % 4),
            "reference_state_age_s": 0.05 * (i % 3),
            "reference_delivery": reference_fresh,
        })
    return pd.DataFrame(data)


def metric(bundle: dict, name: str) -> dict:
    return next(row for row in bundle["metrics"] if row["metric"] == name)


def test_phase8_identical_trace_marks_core_distribution_close():
    trace = make_trace()
    bundle = compare_external_traces(trace, trace.copy())
    assert bundle["schema"] == PHASE8_TRACE_COMPARISON_SCHEMA
    assert bundle["claim_level"] == "pipeline_validation_only"
    assert bundle["safety_acceptance"] is False
    assert bundle["controller_tuning_allowed"] is False
    assert metric(bundle, "image_x_error_m")["status"] == "close"
    assert metric(bundle, "reference_transport_latency_s")["status"] == "close"
    assert metric(bundle, "image_x_error_m")["ks"] == 0.0
    assert metric(bundle, "image_x_error_m")["normalized_wasserstein_1"] == 0.0


def test_phase8_large_external_error_shift_is_preserved_as_mismatch():
    surrogate = make_trace()
    external = make_trace(error_scale=3.5, lateral_bias=0.45)
    bundle = compare_external_traces(
        surrogate,
        external,
        external_evidence_status="external_simulator_unseen",
        external_source="independent_simulator_log",
    )
    assert bundle["claim_level"] == "external_model_resemblance_diagnostic"
    assert bundle["overall_diagnostic"] == "diagnostic_mismatch"
    assert metric(bundle, "image_x_error_m")["status"] == "mismatch"


def test_phase8_optional_latency_is_compared_without_fabricating_missing_values():
    surrogate = make_trace()
    external = make_trace().drop(columns=["reference_transport_latency_s"])
    bundle = compare_external_traces(surrogate, external)
    latency = metric(bundle, "reference_transport_latency_s")
    assert latency["status"] == "insufficient"
    assert latency["external"]["n"] == 0


def test_phase8_report_escapes_source_labels():
    trace = make_trace()
    bundle = compare_external_traces(trace, trace, external_source="<script>alert(1)</script>")
    rendered = render_phase8_report(bundle)
    assert "<script>alert(1)</script>" not in rendered
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered
    assert "flight-safety pass/fail" in rendered


def test_phase8_writer_hashes_inputs_and_outputs(tmp_path):
    surrogate_path = tmp_path / "surrogate.csv"
    external_path = tmp_path / "external.csv"
    out_dir = tmp_path / "bundle"
    make_trace().to_csv(surrogate_path, index=False)
    make_trace(error_scale=1.15).to_csv(external_path, index=False)

    result = write_phase8_comparison(
        surrogate_path,
        external_path,
        out_dir,
        git_sha="abc123",
        external_evidence_status="fixture_non_authoritative",
    )
    bundle = json.loads(result["bundle_path"].read_text(encoding="utf-8"))
    metadata = json.loads(result["metadata_path"].read_text(encoding="utf-8"))
    manifest_result = validate_result_manifest(
        result["manifest_path"],
        expected_schema=PHASE8_RESULT_MANIFEST_SCHEMA,
    )

    assert bundle["git_sha"] == "abc123"
    assert bundle["input_provenance"]["surrogate"]["sha256"]
    assert bundle["input_provenance"]["external"]["sha256"]
    assert metadata["controller_tuning_allowed"] is False
    assert manifest_result["valid"] is True
    assert manifest_result["checked_files"] == 5
    assert "NON-AUTHORITATIVE FIXTURE" in result["summary_path"].read_text(encoding="utf-8")
