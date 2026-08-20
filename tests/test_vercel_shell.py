import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_vercel_home_is_native_static_shell() -> None:
    html = (ROOT / "deploy" / "vercel" / "index.html").read_text(encoding="utf-8")

    assert 'data-site-shell="native"' in html
    assert "document.write" not in html
    assert "cdn.jsdelivr.net/gh/suhaslord/uav-safety-research" not in html
    assert "const rev=" not in html
    assert html.count('class="home-rail-step') == 13
    assert "Open Phase 11" in html


def test_vercel_routes_use_packaged_dashboard_assets() -> None:
    config = json.loads((ROOT / "deploy" / "vercel" / "vercel.json").read_text(encoding="utf-8"))
    rewrites = config["rewrites"]
    destinations = [item["destination"] for item in rewrites]

    assert all(not destination.startswith("https://cdn.jsdelivr.net/") for destination in destinations)
    assert "/dashboard/phases/index.html" in destinations
    assert "/dashboard/phases/phase.html" in destinations
    assert "/dashboard/aegis-current.js" in destinations
    assert "/phase11.html" in destinations


def test_current_frontier_bridge_is_local_and_loaded_last() -> None:
    current = (ROOT / "dashboard" / "aegis-current.js").read_text(encoding="utf-8")
    archive = (ROOT / "dashboard" / "phases" / "index.html").read_text(encoding="utf-8")
    phase = (ROOT / "dashboard" / "phases" / "phase.html").read_text(encoding="utf-8")

    assert "cdn.jsdelivr.net" not in current
    assert "document.write" not in current
    assert archive.rfind('src="/aegis-current.js"') > archive.rfind('src="/phase-runtime.js"')
    assert phase.rfind('src="/aegis-current.js"') > phase.rfind('src="/phase-hero-scenes.js"')


def test_phase10r_logic_is_loaded_by_the_shared_phase_template() -> None:
    html = (ROOT / "dashboard" / "phases" / "phase.html").read_text(encoding="utf-8")

    phase10r = html.index('src="/phase10r-archive.js"')
    scenes = html.index('src="/phase-hero-scenes.js"')
    assert phase10r < scenes
