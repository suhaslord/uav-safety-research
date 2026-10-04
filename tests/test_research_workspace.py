from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_home_actions_feature_phase25_and_scope_phase22_status() -> None:
    html = _read("deploy/vercel/index.html")
    assert 'href="/model-vase/">Model VASE</a>' in html
    assert 'href="/failure-atlas/">Explore Failure Atlas</a>' in html
    assert 'href="/phases/">Archive</a>' in html
    assert 'id="current-audit"' in html
    assert 'id="status"' in html and "Phase 22: transfer without refitting." in html
    assert 'href="/phases/phase22/"' in html
    assert "10 / 10 gates passed" in html
    assert "6 PASS / 7 FAIL" in html
    assert 'id="homeLineage"' in html
    assert 'data-aegis-experiment-lab' not in html
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
    home = _read("deploy/vercel/index.html")
    assert 'src="/home-evidence.js?v=' in home
    assert 'href="/home-evidence.css?v=' in home
    shells = [
        _read("dashboard/phases/index.html"),
        _read("dashboard/phases/phase.html"),
        _read("dashboard/phases/frozen.html"),
        _read("deploy/vercel/phase11.html"),
    ]
    for html in shells:
        assert 'href="/tesla-bundle.css?v=' in html
        assert 'src="/research-workspace.js?v=' in html


def test_home_editorial_media_is_local_credited_and_context_only() -> None:
    html = _read("deploy/vercel/index.html")
    css = _read("deploy/vercel/home-evidence.css")
    fetcher = _read("deploy/vercel/fetch-editorial-media.mjs")

    assert 'data-editorial-media="local-v2"' in html
    filename = "acero-uav-flight.jpg"
    assert f'src="/media/{filename}"' in html
    assert filename in fetcher
    assert 'id="home-comparison"' in html
    assert '<img src="https://' not in html
    assert "not AegisLand experiment results" in html
    assert "Don Richey / NASA Ames" in html
    assert 'class="field-context"' in html
    assert html.index('id="home-comparison"') < html.index('class="home-field-media"')
    assert "Model VASE" in html and "Phase 23 paired" in html
    assert 'class="home-field-media"' in html
    assert html.count('data-autoplay="visible"') == 2
    assert html.count('muted loop preload="none"') == 2
    assert 'src="/film/aerocast-flight.mp4"' in html
    assert 'src="/film/evaluation-nasa-clip.mp4"' in html
    assert 'src="/media/acero-uav-landing.jpg"' in html
    assert "public-domain context" in html
    assert "home-field-media__stage" in css
    assert "aspect-ratio: 3/2" in css


def test_model_vase_hero_uses_the_same_contextual_photo_language_as_home() -> None:
    page = _read("deploy/vercel/model-vase.html")
    css = _read("deploy/vercel/model-vase.css")

    assert '<figure class="vase-hero__media">' in page
    assert 'src="/media/acero-uav-landing.jpg"' in page
    assert "NASA Ames Research Center · public domain" in page
    assert 'id="answer"' in page and 'id="answer-title"' in page
    assert "Can it recognize a bad estimate before the landing decision?" in page
    assert ".model-vase-page .vase-hero::after{display:none}" in css
    assert ".vase-hero__media img" in css and ".vase-hero__copy" in css


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
        image = ROOT / "deploy/vercel/media" / filename
        assert image.is_file() and image.stat().st_size > 50_000

    assert "Visual context — not AegisLand experimental evidence" in manifest
    assert "phase-editorial-photo__fallback" in runtime
    assert "figure.dataset.imageState = 'fallback'" in runtime
    assert "aspect-ratio:16 / 9" in css
    assert "object-fit:cover" in css

    for shell in (phase, frozen, phase11):
        assert 'href="/tesla-bundle.css?v=' in shell
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
    assert "--rw-accent:#e82127" in home
    assert "min-height:610px!important" in home
    assert "grid-template-columns:repeat(13,minmax(0,1fr))" in home
    assert "--phase-accent:#e82127!important" in identity
