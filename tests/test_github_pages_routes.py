import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pages_build", ROOT / "deploy/github-pages/build.py")
pages = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pages)
TAXONOMY = (ROOT / "dashboard/phase-taxonomy.js").read_text(encoding="utf-8")


def test_pages_includes_all_29_archived_routes_and_explicit_paired_report():
    slugs = pages.phase_slugs(TAXONOMY)
    assert len(slugs) == len(set(slugs)) == 29
    assert "phase25" in slugs and "phase26" not in slugs
    config = json.loads((ROOT / "deploy/vercel/vercel.json").read_text(encoding="utf-8"))
    assert any(rule["source"].rstrip("/") == "/phases/phase25" and rule["destination"] == "/phase25.html" for rule in config["rewrites"])


@pytest.mark.parametrize("base", ["", "/uav-safety-research"])
def test_pages_layers_live_atlas_labels_without_changing_source(tmp_path, base):
    original = (ROOT / "deploy/vercel/failure-atlas.js").read_bytes()
    output = tmp_path / "site"
    pages.build(output, base)
    live = (output / "failure-atlas.js").read_text(encoding="utf-8")
    frozen = (output / "failure-atlas-frozen.js").read_text(encoding="utf-8")
    assert f"{base}/failure-atlas-frozen.js?v=8" in live
    assert "Local image · unverified" in live
    assert f"fetch('{base}/failure-atlas-data.json?v=3')" in frozen
    assert (ROOT / "deploy/vercel/failure-atlas.js").read_bytes() == original
    if not base:
        assert (output / "failure-atlas-frozen.js").read_bytes() == original


@pytest.mark.parametrize("replacement", ["phase24", "phase26", "not_a_phase"])
def test_pages_refuses_missing_duplicate_or_prospective_record(replacement):
    with pytest.raises(ValueError, match="29-route Phase 25 archive"):
        pages.phase_slugs(TAXONOMY.replace("    phase25: {", f"    {replacement}: {{"))
