import hashlib
import json
from pathlib import Path

import pytest

from scripts import build_site_revalidation_data as publication

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "deploy/vercel"


def test_published_record_and_figure_match_sealed_inputs():
    assert publication.OUT.read_bytes() == publication.build()
    source = ROOT / "results/research_revalidation_2026_10_03/controlled_occlusion/controlled_occlusion.png"
    assert publication.FIGURE.read_bytes() == source.read_bytes()
    record = json.loads(publication.OUT.read_text(encoding="utf-8"))
    assert record["phase23"]["phase23_cells_checked"] == 24
    assert record["phase23"]["clean_stressed_pair_count"] == 860
    assert record["phase23"]["cross_model_transition_counts"] == {"recovered": 49, "regressed": 65, "both_pass": 223, "both_fail": 179}
    assert record["phase26"]["status"] == "NO_DATASET_ADMITTED"
    assert record["phase26"]["test_inference_authorized"] is False
    assert record["phase26"]["near_distance_argument"] == 9
    assert record["phase26"]["minimum_accepted_dhash_distance"] == 10
    assert record["controlled_occlusion"]["detector_inference_run"] is False


def test_publication_refuses_changed_scientific_inputs(monkeypatch):
    monkeypatch.setattr(publication, "digest", lambda p: "0" * 64)
    with pytest.raises(ValueError, match="Sealed research inputs changed"):
        publication.build()


def test_website_refresh_does_not_rewrite_the_research_freeze():
    manifest = json.loads((ROOT / "results/research_revalidation_2026_10_03/frozen_manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest["files_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name


def test_live_atlas_label_corrections_leave_frozen_artifacts_addressable():
    workflow = (ROOT / ".github/workflows/emergency-vercel-deploy.yml").read_text(encoding="utf-8")
    assert "mv .vercel-release/failure-atlas.js .vercel-release/failure-atlas-frozen.js" in workflow
    assert "cp .vercel-release/failure-atlas-live.js .vercel-release/failure-atlas.js" in workflow
    assert "cmp deploy/vercel/failure-atlas.js .vercel-release/failure-atlas-frozen.js" in workflow
    assert "grep -q '/media/phase25/${condition}/${item.id}' .vercel-release/failure-atlas-frozen.js" in workflow
    assert "grep -q '/media/phase25/${condition}/${item.id}' .vercel-release/failure-atlas.js" not in workflow
    wrapper = (SITE / "failure-atlas-live.js").read_text(encoding="utf-8")
    assert "/failure-atlas-frozen.js?v=8" in wrapper
    assert "Local image · unverified · measured predictions unchanged" in wrapper
    assert "fetch(" not in wrapper  # no new inference or modified result tables


def test_release_qa_waits_for_current_camera_panels_before_image_audit():
    smoke = (ROOT / ".github/qa/phase22-release-smoke.mjs").read_text(encoding="utf-8")
    assert "if(['/phases/','/phases/phase22/'].includes(route))" in smoke
    assert '#experiment-lab[data-current-dataset="kios-real-video"] img' in smoke
    assert "i.loading='eager'" in smoke
    assert "(!i.complete||i.naturalWidth===0)" in smoke


def test_reproduction_page_uses_current_gate_and_exact_source_fetch():
    text = (SITE / "reproduce.html").read_text(encoding="utf-8")
    assert "python scripts/validate_research_release.py" in text
    assert "git fetch --no-tags origin" in text
    assert "f090da03d20b2425c5addccb4d19117c8991bcc1" in text
    assert "6a8623cbeb54951f43b8ca65293598e7c41a474e" in text
    assert "184 files" in text and "1.0.0rc1" in text
    assert "--near-distance 9" in text
    assert "Matching a recorded hash checks byte identity" in text
    assert "Protected Phase 25 frame manifest" in text
    assert "8605cf1cbf9e8769c0324bf066078f9964f232ac3128131c8bd0b689bb7b64b7" in text


def test_current_pages_separate_replay_pairs_and_causal_uncertainty():
    home = (SITE / "index.html").read_text(encoding="utf-8")
    phase23 = (SITE / "phase23.html").read_text(encoding="utf-8")
    phase25 = (SITE / "phase25.html").read_text(encoding="utf-8")
    controlled = (SITE / "phase22-detector-study.html").read_text(encoding="utf-8")
    assert "860" in home and "24 / 24" in home
    assert "clean-room reproduction" not in phase23
    assert "not a newly trained model" in phase23
    assert "860 within-model pairs" in phase25 and "516 cross-model views" in phase25
    assert "not a demonstrated causal mechanism" in phase25
    assert "was not rerun in the latest revalidation" in phase25
    assert "no universal failure threshold" in phase25
    assert "33 of the 86 frames already fail" in controlled
    assert "145,169 predictions" in controlled
    assert "/media/research-revalidation-occlusion.png" in controlled


def test_camera_examples_are_not_labeled_live_detector_outputs():
    script = (SITE / "lab/current-data.js").read_text(encoding="utf-8")
    assert "static source images, not a live feed" in script
    assert "blue box is an annotation, not a detector-output overlay" in script
    assert "No live inference" in script
    assert "Phase 23 detection (blue)" not in script
    assert "Evaluating ${modelMeta.name}" not in script


def test_archive_includes_paired_audit_without_inventing_phase26_results():
    archive = (ROOT / "dashboard/phases/index.html").read_text(encoding="utf-8")
    assert "29 phase records" in archive
    assert "phase25: ['Phase 25'" in archive
    assert "PAIRED AUDIT" in archive
    assert "order.length" in archive
    assert "Phase 26: prospective independent-data admission; no dataset admitted" in archive
    assert "phase26: ['Phase 26'" not in archive
