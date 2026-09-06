import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_vercel_home_is_native_frozen_archive_shell() -> None:
    html = (ROOT / "deploy" / "vercel" / "index.html").read_text(encoding="utf-8")

    assert 'data-site-shell="native frozen-archive"' in html
    assert "document.write" not in html
    assert "cdn.jsdelivr.net/gh/suhaslord/uav-safety-research" not in html
    assert "const rev=" not in html
    assert 'id="evidenceSpine"' in html
    assert 'src="/frozen-lineage.js?v=2"' in html
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


def test_frozen_archive_replaces_current_frontier_bridge_without_breaking_legacy_phase_template() -> None:
    current = (ROOT / "dashboard" / "aegis-current.js").read_text(encoding="utf-8")
    archive = (ROOT / "dashboard" / "phases" / "index.html").read_text(encoding="utf-8")
    frozen = (ROOT / "dashboard" / "phases" / "frozen.html").read_text(encoding="utf-8")
    phase = (ROOT / "dashboard" / "phases" / "phase.html").read_text(encoding="utf-8")

    assert "cdn.jsdelivr.net" not in current
    assert "document.write" not in current
    assert "Phase 12" in current

    assert 'src="/frozen-lineage.js?v=1"' in archive
    assert 'src="/aegis-current.js"' not in archive
    assert 'src="/phase-runtime.js"' not in archive

    assert 'src="/frozen-lineage.js?v=1"' in frozen
    assert "phase(?:12|13a|13b|13c|1[4-9]|2[0-2])" in frozen

    assert phase.rfind('src="/aegis-current.js"') > phase.rfind('src="/phase-hero-scenes.js"')


def test_phase10r_logic_is_loaded_by_the_shared_phase_template() -> None:
    html = (ROOT / "dashboard" / "phases" / "phase.html").read_text(encoding="utf-8")

    phase10r = html.index('src="/phase10r-archive.js"')
    scenes = html.index('src="/phase-hero-scenes.js"')
    assert phase10r < scenes
