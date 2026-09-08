from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GLASS = (ROOT / "deploy" / "vercel" / "final-convergence.css").read_text(encoding="utf-8")


def test_glass_design_tokens_are_defined():
    for token in (
        "--rw-bg:#020617",
        "--rw-accent:#22d3ee",
        "--rw-violet:#a78bfa",
        "--rw-pass:#4ade80",
        "--rw-warn:#fbbf24",
        "--rw-fail:#f87171",
        "--glass-panel-bg:rgba(15,23,42,.65)",
        "--glass-border:rgba(186,230,253,.14)",
        "--glass-transition:180ms cubic-bezier(.2,.7,.2,1)",
    ):
        assert token in GLASS


def test_reusable_glass_primitives_exist():
    for selector in (
        ".glass-panel",
        ".glass-card",
        ".glass-sidebar",
        ".glass-input",
        ".glass-button",
        ".status-badge",
    ):
        assert selector in GLASS
    assert "backdrop-filter:blur(18px)" in GLASS
    assert "-webkit-backdrop-filter:blur(18px)" in GLASS


def test_command_bar_archive_and_phase_surfaces_use_glass_system():
    assert "Floating command bar" in GLASS
    assert "Archive: glass search console and dossier rows." in GLASS
    assert "Shared phase detail: title, verdict, evidence, metrics, limits and methods." in GLASS
    assert ".archive-toolbar__search input" in GLASS
    assert ".archive-card.phase-personalized" in GLASS
    assert ".phase-verdict-panel" in GLASS
    assert ".phase-detail__metrics-band" in GLASS


def test_status_semantics_keep_red_for_failure_only():
    assert ".status-badge--pass" in GLASS
    assert ".verdict-chip--pass" in GLASS
    assert ".status-badge--fail" in GLASS
    assert ".verdict-chip--fail" in GLASS
    assert "color:var(--rw-pass)!important" in GLASS
    assert "color:var(--rw-fail)!important" in GLASS


def test_glass_background_motion_respects_reduced_motion():
    assert "@keyframes aegisGlassDriftA" in GLASS
    assert "@keyframes aegisGlassDriftB" in GLASS
    assert "@media(prefers-reduced-motion:reduce)" in GLASS
    assert "body.research-workspace::before" in GLASS
    assert "body.research-workspace::after" in GLASS
