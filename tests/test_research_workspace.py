from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_home_primary_action_opens_current_evidence_and_scopes_phase22_status() -> None:
    html = _read("deploy/vercel/index.html")
    assert '>Review Phase 22</a>' in html
    assert 'href="/phases/phase22/"' in html
    assert "10 / 10 locked gates passed" in html
    assert "6 PASS / 7 FAIL" in html
    assert 'id="homeLineage"' in html
    assert "workspace-status-actions" not in html
    assert "workspace-brief-strip" not in html


def test_archive_has_semantic_frozen_filters_search_and_empty_state() -> None:
    html = _read("dashboard/phases/index.html")
    assert ">Frozen PASS</button>" in html
    assert ">Frozen FAIL</button>" in html
    assert 'id="archiveEmptyState"' in html
    assert 'id="archiveReset"' in html
    assert "card.textContent" in html
    assert "isFrozen && verdict === 'pass'" in html
    assert "isFrozen && verdict === 'fail'" in html
    assert "!isFrozen" in html


def test_frozen_phase_prioritizes_finding_before_secondary_metrics() -> None:
    html = _read("dashboard/phases/frozen.html")
    finding = html.index('class="phase-detail__body"')
    metrics = html.index('class="phase-detail__metrics-band"')
    context = html.index('class="phase-detail__context"')
    assert finding < metrics < context


def test_workspace_interaction_layer_is_loaded_across_public_shells() -> None:
    shells = [
        _read("deploy/vercel/index.html"),
        _read("dashboard/phases/index.html"),
        _read("dashboard/phases/phase.html"),
        _read("dashboard/phases/frozen.html"),
        _read("deploy/vercel/phase11.html"),
    ]
    for html in shells:
        assert 'href="/research-workspace.css?v=' in html
        assert 'src="/research-workspace.js?v=' in html


def test_home_editorial_media_is_local_credited_and_context_only() -> None:
    html = _read("deploy/vercel/index.html")
    css = _read("deploy/vercel/research-media.css")
    fetcher = _read("deploy/vercel/fetch-editorial-media.mjs")

    assert 'data-editorial-media="local-v1"' in html
    assert 'src="/media/acero-uav-flight.jpg"' in html
    assert 'src="/media/acero-uav-landing.jpg"' in html
    assert '<img src="https://' not in html
    assert html.count("Visual context — not AegisLand experimental evidence") == 2
    assert html.count("Don Richey / NASA Ames Research Center") == 2
    assert html.count("Public domain") == 2
    assert html.count("data-image-fallback") == 2
    assert 'width="1280" height="852"' in html
    assert 'width="1280" height="854"' in html
    assert "aspect-ratio:16 / 9" in css
    assert "acero-uav-flight.jpg" in fetcher
    assert "acero-uav-landing.jpg" in fetcher


def test_workspace_uses_original_light_research_system() -> None:
    css = _read("deploy/vercel/research-workspace.css")
    home = _read("deploy/vercel/research-home.css")
    identity = _read("dashboard/phase-personalization.css")
    assert "--rw-bg:#ffffff" in css
    assert "--rw-text:#171a20" in css
    assert "--rw-accent:" in css
    assert "font-size:clamp(34px,4vw,40px)" in css
    assert "background:rgba(255,255,255,.96)" in css
    assert "text-transform:none" in css
    assert "--rw-accent:#3559c7" in home
    assert "min-height:610px!important" in home
    assert "grid-template-columns:repeat(13,minmax(0,1fr))" in home
    assert "--phase-accent:#3559c7!important" in identity
