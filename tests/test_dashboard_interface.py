from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_research_cockpit_assets_exist_and_preserve_claim_boundaries():
    dashboard = ROOT / "dashboard"
    html = (dashboard / "index.html").read_text(encoding="utf-8")
    js = (dashboard / "cockpit.js").read_text(encoding="utf-8")
    css = (dashboard / "cockpit.css").read_text(encoding="utf-8")

    assert 'cockpit.css' in html
    assert 'cockpit.js' in html
    assert 'phase7.html' in html
    assert 'simulation-only' in html.lower()
    assert 'external_perception_seen' in html
    assert 'safety acceptance' in html.lower()
    assert 'artifactDigest' in js
    assert 'refreshGithubStatus' in js
    assert '.timeline' in css
    assert '#poseChart' in css


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
