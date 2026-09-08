from pathlib import Path

CSS = Path("deploy/vercel/final-convergence.css").read_text(encoding="utf-8")
MARKER = "Apple x Tesla hybrid layer"


def layer() -> str:
    assert MARKER in CSS
    return CSS.split(MARKER, 1)[1]


def test_apple_tesla_hybrid_layer_is_present():
    design = layer()
    assert "--at-red:#e82127" in design
    assert "--at-ink:#171a20" in design
    assert "--at-bg:#f5f5f7" in design
    assert "backdrop-filter:blur(28px)" in design
    assert "border-radius:999px" in design
    assert "workspace-status-card" in design
    assert "archive-category" in design
    assert "phase-detail__panel" in design


def test_hybrid_uses_monochrome_tesla_palette_not_ai_neon():
    design = layer().lower()
    assert "cyan" not in design
    assert "violet" not in design
    assert "#e82127" in design
    assert "#171a20" in design
    assert "rgba(255,255,255" in design


def test_hybrid_has_apple_surface_language():
    design = layer()
    assert "border-radius:30px" in design or "--at-radius-xl:30px" in design
    assert "blur(34px)" in design
    assert "saturate(1.42)" in design
    assert "-apple-system" in design
    assert "box-shadow:var(--at-shadow)" in design
    assert "mobile-menu-sheet" in design


def test_tesla_identity_and_semantic_statuses_remain_distinct():
    design = layer()
    assert ".button.primary" in design
    assert "background:var(--at-ink)!important" in design
    assert ".verdict-chip--pass" in design
    assert ".verdict-chip--fail" in design
    assert "var(--rw-pass" in design
    assert "var(--rw-fail" in design


def test_previous_mobile_visual_blockers_stay_fixed():
    assert "#archiveBoot{display:none!important}" in CSS
    assert "min-width:44px!important" in CSS
    assert "width:calc(100vw - 16px)!important" in CSS
    assert "grid-template-columns:repeat(6,minmax(44px,1fr))" in CSS


def test_reduced_motion_and_focus_are_explicit():
    design = layer()
    assert "prefers-reduced-motion:reduce" in design
    assert ":focus-visible" in design
    assert "outline:2px solid var(--at-red)" in design
