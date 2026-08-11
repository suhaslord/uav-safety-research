from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_phase8_trace_lab_has_separate_bundle_contract():
    html = (ROOT / "phase8_dashboard" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "phase8_dashboard" / "app.js").read_text(encoding="utf-8")

    assert "AegisLand Phase 8 Trace Lab" in html
    assert 'id="bundleFile"' in html
    assert 'id="metricRows"' in html
    assert "aegisland.phase8.trace-comparison.v1" in js
    assert "controller_tuning_allowed" in js
    assert "safety_acceptance" in js
    assert "fixture_non_authoritative" in js


def test_phase8_trace_lab_uses_no_external_script_or_telemetry_dependency():
    html = (ROOT / "phase8_dashboard" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "phase8_dashboard" / "app.js").read_text(encoding="utf-8")

    assert "https://" not in html
    assert "http://" not in html
    assert "fetch(" not in js
    assert "XMLHttpRequest" not in js
