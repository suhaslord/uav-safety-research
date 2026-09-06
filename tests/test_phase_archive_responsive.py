from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_legacy_phase_template_keeps_canonical_responsive_base_plus_polish_guardrails():
    phase = (ROOT / "dashboard/phases/phase.html").read_text()
    assert 'phase-responsive.css' in phase
    assert 'href="/phase-polish.css?v=' in phase
    assert 'href="/phase-polish-fixes.css?v=' in phase
    assert 'tesla-mobile.css' not in phase
    assert 'tesla-phase-mobile.css' not in phase
    assert 'class="archive-shell phase-polish-shell"' in phase


def test_frozen_archive_uses_shared_tesla_polish_instead_of_dark_signature_stack():
    index = (ROOT / "dashboard/phases/index.html").read_text()
    frozen = (ROOT / "dashboard/phases/frozen.html").read_text()

    assert 'href="/phase-polish.css?v=' in index
    assert 'href="/signature.css?v=' not in index
    assert 'phase-responsive.css' not in index
    assert 'tesla-mobile.css' not in index
    assert 'tesla-phase-mobile.css' not in index
    assert 'class="phase-polish-shell"' in index

    assert 'href="/phase-polish.css?v=' in frozen
    assert 'href="/phase-polish-fixes.css?v=' in frozen
    assert 'href="/signature.css?v=' not in frozen
    assert 'phase-responsive.css' not in frozen
    assert 'tesla-mobile.css' not in frozen
    assert 'tesla-phase-mobile.css' not in frozen
    assert 'class="phase-polish-shell"' in frozen


def test_responsive_css_has_no_compatibility_important_stack():
    css = (ROOT / "dashboard/phase-responsive.css").read_text()
    # Guard against actual priority declarations, not explanatory comments.
    assert "!important;" not in css
    assert ".signature-visual strong" in css
    assert "font-size:12px" in css
    assert "@media (max-width:767px)" in css


def test_phase_polish_guardrails_bound_mobile_content_and_hashes():
    css = (ROOT / "deploy/vercel/phase-polish-fixes.css").read_text()
    assert ".phase-hash" in css
    assert "overflow-wrap:anywhere" in css
    assert "body.archive-shell.phase-polish-shell .hero{min-height:auto" in css
    assert "body.archive-shell.phase-polish-shell .section{min-height:0" in css


def test_phase10_mobile_is_content_led():
    css = (ROOT / "dashboard/phase-responsive.css").read_text()
    assert ".signature-phase10 .frontier-metrics" in css
    assert "grid-template-columns:1fr;" in css
    assert "font-size:22px" in css
