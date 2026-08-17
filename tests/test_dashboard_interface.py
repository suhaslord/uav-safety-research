from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_research_cockpit_is_current_phase11_and_preserves_claim_boundaries():
    dashboard = ROOT / "dashboard"
    html = (dashboard / "index.html").read_text(encoding="utf-8")
    js = (dashboard / "cockpit.js").read_text(encoding="utf-8")
    css = (dashboard / "cockpit.css").read_text(encoding="utf-8")
    extension_js = (dashboard / "cockpit-extension.js").read_text(encoding="utf-8")
    extension_css = (dashboard / "cockpit-extension.css").read_text(encoding="utf-8")

    # The public cockpit now natively presents the latest evidence-backed model.
    assert 'data-current-model="phase11"' in html
    assert 'Phase 11' in html
    assert 'P14R' in html
    assert 'latest AegisLand model' in html
    assert 'strongest AegisLand model yet' in html
    assert '98.53%' in html
    assert '96.17%' in html
    assert '95.82%' in html
    assert '94.63%' in html
    assert '10 / 11' in html
    assert '2.435' in html
    assert '2.25' in html
    assert 'P15' in html
    assert 'Unexposed' in html or 'unexposed' in html

    # Scientific scope stays explicit while the presentation moves forward.
    assert 'simulation-only' in html.lower()
    assert 'safety_acceptance=false' in html
    assert 'controller_tuning_allowed=false' in html
    assert 'final_unseen_replication=false' in html
    assert '/phases/phase11/' in html
    assert '/phases/' in html
    assert 'docs/phase11_final_report.md' in html
    assert 'https://github.com/suhaslord/uav-safety-research' in html

    # Legacy cockpit assets remain in-repo for provenance/older interfaces even though
    # the current homepage no longer depends on Phase 9-specific charts.
    assert 'artifactDigest' in js
    assert 'refreshGithubStatus' in js
    assert '.timeline' in css
    assert '#poseChart' in css
    assert 'background: transparent !important' in extension_css
    assert 'sectionUnderHeader' in extension_js
    assert 'classList.toggle("on-dark"' in extension_js


def test_phase11_page_scrolls_and_marks_latest_model():
    html = (ROOT / "dashboard" / "phases" / "phase11.html").read_text(encoding="utf-8")
    assert 'overflow-x:hidden!important;overflow-y:auto!important' in html
    assert 'latest model' in html.lower()
    assert 'strongest' in html.lower()
    assert '98.53%' in html
    assert '96.17 / 95.82%' in html
    assert '94.63%' in html
    assert '2.435' in html
    assert '869869' in html
    assert 'safety_acceptance=false' in html
    assert 'controller_tuning_allowed=false' in html


def test_phase7_explorer_assets_remain_available():
    dashboard = ROOT / "dashboard"
    html = (dashboard / "phase7.html").read_text(encoding="utf-8")
    js = (dashboard / "app.js").read_text(encoding="utf-8")
    css = (dashboard / "styles.css").read_text(encoding="utf-8")

    assert 'styles.css' in html
    assert 'app.js' in html
    assert 'summaryFile' in html
    assert 'pairedFile' in html
    assert 'simulation research only' in html.lower()
    assert 'parseCsv' in js
    assert 'unsafe_touchdown_rate' in js
    assert 'plant_model' in js
    assert '.matrix-table' in css
