from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_research_cockpit_assets_exist_and_preserve_claim_boundaries():
    dashboard = ROOT / "dashboard"
    html = (dashboard / "index.html").read_text(encoding="utf-8")
    js = (dashboard / "cockpit.js").read_text(encoding="utf-8")
    css = (dashboard / "cockpit.css").read_text(encoding="utf-8")
    extension_js = (dashboard / "cockpit-extension.js").read_text(encoding="utf-8")
    extension_css = (dashboard / "cockpit-extension.css").read_text(encoding="utf-8")

    assert 'cockpit.css' in html
    assert 'cockpit-extension.css' in html
    assert 'cockpit.js' in html
    assert 'cockpit-extension.js' in html
    assert 'phase7.html' in html
    assert 'simulation-only' in html.lower()
    assert 'external_perception_seen' in html
    assert 'safety acceptance' in html.lower()
    assert 'artifactDigest' in js
    assert 'refreshGithubStatus' in js
    assert '.timeline' in css
    assert '#poseChart' in css

    # The floating header islands avoid a full-width light slab across dark sections.
    assert 'background: transparent !important' in extension_css
    assert 'sectionUnderHeader' in extension_js
    assert 'classList.toggle("on-dark"' in extension_js

    # Public research navigation and source provenance remain explicit.
    assert 'https://github.com/suhaslord/uav-safety-research' in html
    assert 'https://www.linkedin.com/in/suhas-beemineni-1984763b8/' in html
    assert 'Visualization source audit' in html
    assert 'analysis/perception_trace.csv' in html
    assert 'capture/capture_frames.csv' in html
    assert '#9114281248' in html
    assert '31523496671' in html

    # Historical versions are pinned to concrete GitHub records rather than implied current state.
    assert 'research lineage' in html.lower()
    assert 'pull/6' in html
    assert 'pull/7' in html
    assert 'pull/8' in html
    assert 'pull/9' in html
    assert 'pull/10' in html
    assert 'pull/11' in html
    assert 'pull/12' in html
    assert 'pull/13' in html
    assert 'b4e9838555e935a5ec42690495315473629b58f6' in html
    assert '7354eeda8b975f45b659ce4f3f86c82501e6321d' in html
    assert 'bd62e3b31431306fd9d897f560be7325d711d21a' in html
    assert 'b9df03e111f3a796e50df440becc587c48ee7643' in html
    assert '33c5c73768757b508f5c613b2fba73f94e3fd5a6' in html


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
