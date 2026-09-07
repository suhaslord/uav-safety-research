import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_vercel_home_is_native_frozen_archive_shell() -> None:
    html = (ROOT / "deploy" / "vercel" / "index.html").read_text(encoding="utf-8")

    assert 'data-site-shell="native frozen-archive"' in html
    assert 'data-editorial-media="local-v2"' in html
    assert "document.write" not in html
    assert "cdn.jsdelivr.net/gh/suhaslord/uav-safety-research" not in html
    assert "const rev=" not in html
    assert 'id="evidenceSpine"' in html
    assert 'src="/frozen-lineage.js?v=' in html
    assert "Frozen through Phase 22" in html
    assert "0.8319" in html
    assert "0.7744" in html
    assert "simulation_only=true" in html
    assert "safety_acceptance=false" in html
    assert "controller_tuning_allowed=false" in html
    assert "No Phase 23 is implied or authorized" in html


def test_vercel_routes_use_packaged_frozen_and_legacy_assets() -> None:
    config = json.loads((ROOT / "deploy" / "vercel" / "vercel.json").read_text(encoding="utf-8"))
    rewrites = config["rewrites"]
    destinations = [item["destination"] for item in rewrites]

    assert all(not destination.startswith("https://cdn.jsdelivr.net/") for destination in destinations)
    assert "/dashboard/phases/index.html" in destinations
    assert "/dashboard/phases/frozen.html" in destinations
    assert "/dashboard/phases/phase.html" in destinations
    assert "/dashboard/aegis-current.js" in destinations
    assert "/dashboard/phase-taxonomy.js" in destinations
    assert "/dashboard/phase-personalization.css" in destinations
    assert "/dashboard/phase-personalization.js" in destinations
    assert "/dashboard/phase-editorial-media.css" in destinations
    assert "/dashboard/phase-visuals.js" in destinations
    assert "/dashboard/phase-editorial-media.js" in destinations
    assert "/phase11.html" in destinations
    assert "/phase12.html" not in destinations

    frozen_sources = {
        item["source"]
        for item in rewrites
        if item["destination"] == "/dashboard/phases/frozen.html"
    }
    for slug in (
        "phase12",
        "phase13a",
        "phase13b",
        "phase13c",
        "phase14",
        "phase15",
        "phase16",
        "phase17",
        "phase18",
        "phase19",
        "phase20",
        "phase21",
        "phase22",
    ):
        assert f"/phases/{slug}" in frozen_sources
        assert f"/phases/{slug}/" in frozen_sources


def test_phase12_standalone_file_remains_a_frozen_historical_record() -> None:
    html = (ROOT / "deploy" / "vercel" / "phase12.html").read_text(encoding="utf-8")

    assert "Phase 12" in html
    assert "935935" in html
    assert "2.23035" in html
    assert "95.53%" in html
    assert "simulation_only=true" in html
    assert "safety_acceptance=false" in html
    assert "controller_tuning_allowed=false" in html
    assert "No further Phase 12 tuning" in html


def test_phase_archive_uses_shared_tesla_polish_without_rewriting_lineage() -> None:
    polish = (ROOT / "deploy" / "vercel" / "phase-polish.css").read_text(encoding="utf-8")
    archive = (ROOT / "dashboard" / "phases" / "index.html").read_text(encoding="utf-8")
    frozen = (ROOT / "dashboard" / "phases" / "frozen.html").read_text(encoding="utf-8")
    phase = (ROOT / "dashboard" / "phases" / "phase.html").read_text(encoding="utf-8")

    assert "--phase-blue:#3e6ae1" in polish
    assert "backdrop-filter" in polish
    assert "linear-gradient" not in polish
    assert 'href="/phase-polish.css?v=' in archive
    assert 'href="/phase-polish.css?v=' in frozen
    assert 'href="/phase-polish.css?v=' in phase
    assert 'href="/phase-personalization.css?v=' in archive
    assert 'href="/phase-personalization.css?v=' in frozen
    assert 'href="/phase-personalization.css?v=' in phase
    assert 'href="/phase-editorial-media.css?v=' in frozen
    assert 'href="/phase-editorial-media.css?v=' in phase
    assert 'href="/signature.css?v=' not in archive
    assert 'href="/signature.css?v=' not in frozen
    assert "One research program. Six distinct chapters." in archive
    assert "Research categories" in archive


def test_phase_taxonomy_personalizes_all_26_phase_routes() -> None:
    taxonomy = (ROOT / "dashboard" / "phase-taxonomy.js").read_text(encoding="utf-8")
    personalization = (ROOT / "dashboard" / "phase-personalization.js").read_text(encoding="utf-8")
    css = (ROOT / "dashboard" / "phase-personalization.css").read_text(encoding="utf-8")

    expected_slugs = (
        "phase1", "phase2", "phase3", "phase4", "phase5", "phase6", "phase6b",
        "phase7", "phase8", "phase9", "phase10", "phase10r", "phase11", "phase12",
        "phase13a", "phase13b", "phase13c", "phase14", "phase15", "phase16", "phase17",
        "phase18", "phase19", "phase20", "phase21", "phase22",
    )
    for slug in expected_slugs:
        assert f"{slug}: {{ category:" in taxonomy

    for category in (
        "safety-architecture",
        "perception-robustness",
        "external-validation",
        "reliability-calibration",
        "latency-dynamics",
        "context-transfer",
    ):
        assert f"id: '{category}'" in taxonomy

    assert "phase-identity-chip" in personalization
    assert "phase-role-card" in personalization
    assert "dataset.phaseCategory" in personalization
    assert ".archive-category" in css
    assert ".phase-role-card" in css


def test_frozen_archive_replaces_current_frontier_bridge_without_breaking_legacy_phase_template() -> None:
    current = (ROOT / "dashboard" / "aegis-current.js").read_text(encoding="utf-8")
    archive = (ROOT / "dashboard" / "phases" / "index.html").read_text(encoding="utf-8")
    frozen = (ROOT / "dashboard" / "phases" / "frozen.html").read_text(encoding="utf-8")
    phase = (ROOT / "dashboard" / "phases" / "phase.html").read_text(encoding="utf-8")

    assert "cdn.jsdelivr.net" not in current
    assert "document.write" not in current
    assert "Phase 12" in current

    assert 'src="/frozen-lineage.js?v=' in archive
    assert 'src="/phase-taxonomy.js?v=' in archive
    assert 'src="/aegis-current.js"' not in archive
    assert 'src="/phase-runtime.js"' not in archive

    assert 'src="/frozen-lineage.js?v=' in frozen
    assert 'src="/phase-taxonomy.js?v=' in frozen
    assert 'src="/phase-visuals.js?v=' in frozen
    assert 'src="/phase-personalization.js?v=' in frozen
    assert 'src="/phase-editorial-media.js?v=' in frozen
    assert "phase(?:12|13a|13b|13c|1[4-9]|2[0-2])" in frozen

    assert phase.rfind('src="/phase-personalization.js?v=1"') > phase.rfind('src="/aegis-current.js"')
    assert phase.rfind('src="/phase-editorial-media.js?v=1"') > phase.rfind('src="/phase-personalization.js?v=1"')


def test_phase10r_logic_is_loaded_by_the_shared_phase_template() -> None:
    html = (ROOT / "dashboard" / "phases" / "phase.html").read_text(encoding="utf-8")

    phase10r = html.index('src="/phase10r-archive.js"')
    scenes = html.index('src="/phase-hero-scenes.js"')
    assert phase10r < scenes
