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

    assert 'data-editorial-media="local-v2"' in html
    for filename in (
        "acero-uav-flight.jpg",
        "acero-ground-control.jpg",
        "stereo-uav-preflight.jpg",
        "acero-uav-landing.jpg",
    ):
        assert f'src="/media/{filename}"' in html
        assert filename in fetcher
    assert '<img src="https://' not in html
    assert html.count("Visual context — not AegisLand experimental evidence") == 4
    assert html.count("Public domain") == 4
    assert html.count("data-image-fallback") == 4
    assert html.count("Don Richey / NASA Ames Research Center") == 3
    assert html.count("Joel Kowsky / NASA") == 1
    assert "aspect-ratio:16 / 9" in css
    assert "research-photo--inline" in css


def test_every_phase_has_one_distinct_local_context_photo() -> None:
    manifest = _read("dashboard/phase-visuals.js")
    runtime = _read("dashboard/phase-editorial-media.js")
    css = _read("dashboard/phase-editorial-media.css")
    fetcher = _read("deploy/vercel/fetch-editorial-media.mjs")
    phase = _read("dashboard/phases/phase.html")
    frozen = _read("dashboard/phases/frozen.html")
    phase11 = _read("deploy/vercel/phase11.html")

    slugs = [
        "phase1", "phase2", "phase3", "phase4", "phase5", "phase6", "phase6b",
        "phase7", "phase8", "phase9", "phase10", "phase10r", "phase11", "phase12",
        "phase13a", "phase13b", "phase13c", "phase14", "phase15", "phase16",
        "phase17", "phase18", "phase19", "phase20", "phase21", "phase22",
    ]
    filenames = [
        "phase01-context.jpg", "phase02-context.jpg", "acero-ground-control.jpg",
        "phase04-context.jpg", "phase05-context.jpg", "acero-uav-flight.jpg",
        "phase06b-context.jpg", "phase07-context.jpg", "phase08-context.jpg",
        "acero-uav-landing.jpg", "phase10-context.jpg", "phase10r-context.jpg",
        "stereo-uav-preflight.jpg", "phase12-context.jpg", "phase13a-context.jpg",
        "phase13b-context.jpg", "phase13c-context.jpg", "phase14-context.jpg",
        "phase15-context.jpg", "phase16-context.jpg", "phase17-context.jpg",
        "phase18-context.jpg", "phase19-context.jpg", "phase20-context.jpg",
        "phase21-context.jpg", "phase22-context.jpg",
    ]

    assert len(slugs) == 26
    assert len(filenames) == len(set(filenames)) == 26
    for slug in slugs:
        assert f"{slug}:" in manifest
    for filename in filenames:
        assert f"'{filename}'" in manifest
        assert f"'{filename}'" in fetcher

    assert "Visual context — not AegisLand experimental evidence" in manifest
    assert "phase-editorial-photo__fallback" in runtime
    assert "figure.dataset.imageState = 'fallback'" in runtime
    assert "aspect-ratio:16 / 9" in css
    assert "object-fit:cover" in css

    for shell in (phase, frozen, phase11):
        assert 'href="/phase-editorial-media.css?v=' in shell
        assert 'src="/phase-visuals.js?v=' in shell
        assert 'src="/phase-editorial-media.js?v=' in shell


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
