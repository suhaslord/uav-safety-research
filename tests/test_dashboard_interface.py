from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_assets_exist_and_are_self_contained():
    dashboard = ROOT / "dashboard"
    html = (dashboard / "index.html").read_text(encoding="utf-8")
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
    assert 'http://' not in html and 'https://' not in html
