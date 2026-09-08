from pathlib import Path

CSS = Path("deploy/vercel/final-convergence.css").read_text(encoding="utf-8")
MARKER = "Tesla-safe Liquid Glass overlay"


def overlay() -> str:
    assert MARKER in CSS
    return CSS.split(MARKER, 1)[1]


def test_liquid_glass_overlay_is_present():
    layer = overlay()
    assert "backdrop-filter:blur(18px)" in layer
    assert "-webkit-backdrop-filter:blur(18px)" in layer
    assert "workspace-status-card" in layer
    assert "archive-category" in layer
    assert "phase-verdict-panel" in layer
    assert "prefers-reduced-motion:reduce" in layer


def test_overlay_does_not_rewrite_tesla_geometry_or_type():
    layer = overlay()
    forbidden = (
        "grid-template",
        "font-size:",
        "line-height:",
        "letter-spacing:",
        "text-transform:",
        "border-radius:",
        "padding:",
        "padding-",
        "margin:",
        "margin-",
        "width:",
        "min-width:",
        "max-width:",
        "height:",
        "min-height:",
        "max-height:",
    )
    for token in forbidden:
        assert token not in layer, f"Liquid Glass overlay must not alter Tesla geometry/type: {token}"


def test_overlay_keeps_light_tesla_material_and_semantic_statuses():
    layer = overlay()
    assert "rgba(255,255,255,.64)" in layer
    assert ".verdict-chip" in layer
    assert "verdict-chip--pass" not in layer
    assert "verdict-chip--fail" not in layer
