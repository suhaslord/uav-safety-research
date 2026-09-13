from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_all_phase_shells_load_unified_polish_layer() -> None:
    shells = {
        "archive": _read("dashboard/phases/index.html"),
        "legacy": _read("dashboard/phases/phase.html"),
        "frozen": _read("dashboard/phases/frozen.html"),
        "phase11": _read("deploy/vercel/phase11.html"),
    }

    for name, html in shells.items():
        assert 'href="/phase-polish-v2.css?v=1"' in html, name
        assert 'href="/research-workspace.css?v=1"' in html, name
        assert 'src="/research-workspace.js?v=' in html, name


def test_polish_layer_keeps_reduced_motion_support() -> None:
    css = _read("deploy/vercel/phase-polish-v2.css")

    assert "--p2-blue:#3e6ae1" in css
    assert "box-shadow:none!important" in css
    assert "@media(prefers-reduced-motion:reduce)" in css
    assert "phase-detail__panel--evidence" in css
    assert "phase11-polish" in css
    assert "archive-shell .phase-rail-section" in css


def test_research_workspace_has_accessible_focus_and_reduced_motion() -> None:
    css = _read("deploy/vercel/research-workspace.css")
    js = _read("deploy/vercel/research-workspace.js")

    assert "focus-visible" in css
    assert "@media(prefers-reduced-motion:reduce)" in css
    assert "aria-current" in js
    assert "MutationObserver" in js
    assert "event.key !== 'Tab'" in js