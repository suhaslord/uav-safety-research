from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase10r_is_bound_before_legacy_renderer_runs() -> None:
    taxonomy = _read("dashboard/phase-taxonomy.js")
    runtime = _read("dashboard/phase-runtime.js")

    # Phase 10R must be recognized as its own route before the legacy renderer's
    # DOMContentLoaded handler asks currentKey() for the active phase.
    assert "10r?" in taxonomy
    assert "document.body.dataset.phase = routeMatch[1].toLowerCase()" in taxonomy
    assert "document.body.dataset.phase ||" in runtime


def test_phase10r_progression_stays_inside_aegisland_archive() -> None:
    personalization = _read("dashboard/phase-personalization.js")

    assert "slug === 'phase10r'" in personalization
    assert "next.href = '/phases/phase11/'" in personalization
    assert "next.removeAttribute('target')" in personalization
    assert "next.removeAttribute('rel')" in personalization
    assert "Phase 11 · Protected reliability" in personalization


def test_phase10r_retains_its_own_frozen_holdout_record() -> None:
    patch = _read("dashboard/phase10r-archive.js")

    assert 'label: "Phase 10R · Frozen holdout"' in patch
    assert 'title: "Mean error fell. Trust still broke under distribution shift."' in patch
    assert '79.2%' in patch
    assert '20.0%' in patch
    assert 'Final verdict: mixed / failed overall' in patch
