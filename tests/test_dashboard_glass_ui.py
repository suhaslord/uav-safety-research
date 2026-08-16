import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GLASS = (ROOT / "dashboard" / "glass-ui.css").read_text(encoding="utf-8")
REFRACTION = (ROOT / "dashboard" / "glass-refraction.css").read_text(encoding="utf-8")
SHELL = (ROOT / "deploy" / "vercel" / "index.html").read_text(encoding="utf-8")


def test_phase_hero_text_is_kept_out_of_moving_svg_geometry():
    assert ".scene-hero .scene-svg text{display:none!important}" in GLASS


def test_phase_hero_has_contained_stable_layout():
    assert "contain:layout paint style!important" in GLASS
    assert "grid-template-rows:auto minmax(0,1fr) auto!important" in GLASS
    assert "overflow:hidden!important" in GLASS


def test_all_twelve_phase_steps_fit_shared_rail():
    assert "grid-template-columns:repeat(12,minmax(78px,1fr))!important" in GLASS


def test_homepage_giant_target_is_restrained():
    assert ".hero-media .hero-image" in GLASS
    assert "opacity:.055!important" in GLASS
    assert "#homeModelRail::before" in GLASS


def test_refraction_layer_has_visible_but_restrained_glass_edges():
    assert "--glass-control-bg:linear-gradient" in REFRACTION
    assert "inset 0 1px 0 rgba(255,255,255,.98)" in REFRACTION
    assert "--glass-control-shadow-hover" in REFRACTION
    assert "#homeModelRail .home-rail-step" in REFRACTION


def test_vercel_shell_loads_glass_layers_from_pinned_revision():
    assert "const glass=`${base}glass-ui.css`;" in SHELL
    assert "const refraction=`${base}glass-refraction.css`;" in SHELL
    match = re.search(r"const rev='([0-9a-f]{40})';", SHELL)
    assert match is not None
    assert match.group(1) != "0" * 40
    # The shell must retain only its own real closing script tag; nested injected
    # scripts are escaped as <\\/script> so browsers cannot terminate early.
    assert SHELL.count("</script>") == 1
