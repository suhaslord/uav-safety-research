import re
from pathlib import Path

CSS = Path("deploy/vercel/final-convergence.css").read_text(encoding="utf-8")
MARKER = "Tesla-safe Liquid Glass overlay"


def overlay() -> str:
    assert MARKER in CSS
    return CSS.split(MARKER, 1)[1]


def declarations(layer: str) -> list[str]:
    # Only inspect CSS declarations inside blocks. This deliberately ignores
    # media-query conditions such as `@media (max-width:900px)`.
    props = []
    for block in re.findall(r"\{([^{}]*)\}", layer, flags=re.S):
        for match in re.finditer(r"(?:^|;)\s*([\w-]+)\s*:", block):
            props.append(match.group(1).lower())
    return props


def test_liquid_glass_overlay_is_present():
    layer = overlay()
    assert "backdrop-filter:blur(18px)" in layer
    assert "-webkit-backdrop-filter:blur(18px)" in layer
    assert "workspace-status-card" in layer
    assert "archive-category" in layer
    assert "phase-verdict-panel" in layer
    assert "prefers-reduced-motion:reduce" in layer


def test_overlay_does_not_rewrite_tesla_geometry_or_type():
    forbidden = {
        "grid-template",
        "grid-template-columns",
        "grid-template-rows",
        "font-size",
        "line-height",
        "letter-spacing",
        "text-transform",
        "border-radius",
        "padding",
        "padding-top",
        "padding-right",
        "padding-bottom",
        "padding-left",
        "margin",
        "margin-top",
        "margin-right",
        "margin-bottom",
        "margin-left",
        "width",
        "min-width",
        "max-width",
        "height",
        "min-height",
        "max-height",
    }
    touched = forbidden.intersection(declarations(overlay()))
    assert not touched, f"Liquid Glass overlay must not alter Tesla geometry/type: {sorted(touched)}"


def test_overlay_keeps_light_tesla_material_and_semantic_statuses():
    layer = overlay()
    assert "rgba(255,255,255,.64)" in layer
    assert ".verdict-chip" in layer
    assert "verdict-chip--pass" not in layer
    assert "verdict-chip--fail" not in layer
