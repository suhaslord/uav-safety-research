"""The editorial refresh cannot displace AegisLand's evidence or controls."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "deploy" / "vercel"


def test_editorial_sheet_loads_last_only_where_intended():
    for page in ("index.html", "prototype.html"):
        head = (SITE / page).read_text(encoding="utf-8").split("</head>", 1)[0]
        sources = re.findall(r'<link rel="stylesheet" href="([^"]+)"', head)
        assert sources[-1] == "/tesla-editorial.css?v=1", page
        assert sources.count("/tesla-editorial.css?v=1") == 1, page


def test_original_media_and_interactions_are_preserved():
    home = (SITE / "index.html").read_text(encoding="utf-8")
    demo = (SITE / "prototype.html").read_text(encoding="utf-8")
    for item in (
        "/film/aerocast-flight.mp4",
        "/film/evaluation-nasa-clip.mp4",
        'id="home-comparison"',
        'id="camera-preview"',
        'href="/prototype/"',
        "NASA Armstrong footage",
        "not AegisLand experiment data",
        "No independent Phase 26 dataset has passed admission",
    ):
        assert item in home, item
    for item in (
        'id="prototype-app"',
        'id="condition-select"',
        'id="frame-select"',
        'id="model-select"',
        'id="cutoff"',
        'id="accepted-count"',
        "not a tested landing-safety system",
        "not for choosing or validating a real-world threshold",
    ):
        assert item in demo, item


def test_finish_is_restrained_and_page_scoped():
    css = (SITE / "tesla-editorial.css").read_text(encoding="utf-8")
    assert len(css) > 1000
    assert "radial-gradient(" not in css
    assert "border-radius:4px" in css
    assert "--editorial-ink:#171a20" in css
    assert "--editorial-blue:#1766b2" in css
    assert "body.home-evidence-led" in css
    assert "body.prototype-page" in css
    assert "body:not(" not in css
    assert "url(" not in css  # no external brand assets or image swaps
    assert "prefers-reduced-motion" in css
