from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_legacy_phase_template_keeps_one_canonical_responsive_layer():
    phase = (ROOT / "dashboard/phases/phase.html").read_text()
    assert 'phase-responsive.css' in phase
    assert 'tesla-mobile.css' not in phase
    assert 'tesla-phase-mobile.css' not in phase
    assert 'class="archive-shell"' in phase


def test_frozen_archive_uses_signature_responsive_system_instead_of_legacy_stack():
    index = (ROOT / "dashboard/phases/index.html").read_text()
    frozen = (ROOT / "dashboard/phases/frozen.html").read_text()
    for html in (index, frozen):
        assert '/signature.css?v=1' in html
        assert 'phase-responsive.css' not in html
        assert 'tesla-mobile.css' not in html
        assert 'tesla-phase-mobile.css' not in html
        assert 'class="signature-site"' in html


def test_responsive_css_has_no_compatibility_important_stack():
    css = (ROOT / "dashboard/phase-responsive.css").read_text()
    # Guard against actual priority declarations, not explanatory comments.
    assert "!important;" not in css
    assert ".signature-visual strong" in css
    assert "font-size:12px" in css
    assert "@media (max-width:767px)" in css


def test_phase10_mobile_is_content_led():
    css = (ROOT / "dashboard/phase-responsive.css").read_text()
    assert ".signature-phase10 .frontier-metrics" in css
    assert "grid-template-columns:1fr;" in css
    assert "font-size:22px" in css
