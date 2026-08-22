from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOTION = (ROOT / "dashboard" / "glass-ui.css").read_text(encoding="utf-8")
SHELL = (ROOT / "deploy" / "vercel" / "index.html").read_text(encoding="utf-8")


def test_phase_hero_text_is_kept_out_of_moving_svg_geometry():
    assert ".scene-hero .scene-svg text{display:none!important}" in MOTION


def test_phase_hero_has_contained_stable_layout():
    assert "contain:layout paint style!important" in MOTION
    assert "grid-template-rows:auto minmax(0,1fr) auto!important" in MOTION
    assert "overflow:hidden!important" in MOTION


def test_all_twelve_historical_phase_steps_fit_shared_rail():
    assert "grid-template-columns:repeat(12,minmax(78px,1fr))!important" in MOTION


def test_historical_homepage_motion_stays_restrained():
    assert ".hero-media .hero-image" in MOTION
    assert "opacity:.055!important" in MOTION
    assert "#homeModelRail::before" in MOTION
    assert "@keyframes motionScan" in MOTION
    assert "@keyframes motionOrbit" in MOTION


def test_phase_animation_pacing_is_preserved():
    assert ".p1-drone{animation-duration:6.8s!important}" in MOTION
    assert ".p7-cube{animation-duration:9s!important}" in MOTION
    assert ".p10-band{animation-duration:5.6s!important}" in MOTION
    assert ".p10r-arrow{animation-duration:5s!important}" in MOTION


def test_motion_layer_does_not_reintroduce_glass_materials():
    assert "backdrop-filter" not in MOTION
    assert "--glass-control-bg" not in MOTION
    assert not (ROOT / "dashboard" / "glass-refraction.css").exists()


def test_vercel_home_is_native_instead_of_runtime_loading_historical_css():
    assert 'data-site-shell="native"' in SHELL
    assert "document.write" not in SHELL
    assert "cdn.jsdelivr.net" not in SHELL
    assert "const motion=`${base}glass-ui.css`;" not in SHELL
    assert "glass-refraction.css" not in SHELL
