from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phase_pages_use_one_canonical_responsive_layer():
    phase = (ROOT / "dashboard/phases/phase.html").read_text()
    index = (ROOT / "dashboard/phases/index.html").read_text()
    for html in (phase, index):
        assert 'phase-responsive.css' in html
        assert 'tesla-mobile.css' not in html
        assert 'tesla-phase-mobile.css' not in html
        assert 'class="archive-shell"' in html


def test_responsive_css_has_no_compatibility_important_stack():
    css = (ROOT / "dashboard/phase-responsive.css").read_text()
    assert "!important" not in css
    assert ".signature-visual strong" in css
    assert "font-size:12px" in css
    assert "@media (max-width:767px)" in css


def test_phase10_mobile_is_content_led():
    css = (ROOT / "dashboard/phase-responsive.css").read_text()
    assert ".signature-phase10 .frontier-metrics" in css
    assert "grid-template-columns:1fr;" in css
    assert "font-size:22px" in css
