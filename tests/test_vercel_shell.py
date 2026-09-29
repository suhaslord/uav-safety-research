import csv
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_phase25_lens_reuses_published_aggregates_without_frame_claims() -> None:
    payload = json.loads((ROOT / "deploy/vercel/phase25-explorer-data.json").read_text(encoding="utf-8"))
    comparison_path = ROOT / "results/phase23_robust_detector/robustness_comparison.csv"
    with comparison_path.open(newline="", encoding="utf-8") as handle:
        comparison = {row["condition"]: row for row in csv.DictReader(handle)}
    assert payload["status"] == "published_aggregates_only"
    assert payload["source_sha256"]["comparison"] == hashlib.sha256(comparison_path.read_bytes()).hexdigest()
    assert len(payload["conditions"]) == 6
    for item in payload["conditions"]:
        assert item["baseline_map50"] == float(comparison[item["key"]]["baseline_map50"])
        assert item["robust_map50"] == float(comparison[item["key"]]["phase23_map50"])
        assert (ROOT / "deploy/vercel" / item["illustration"].lstrip("/")).is_file()
    phase = (ROOT / "deploy/vercel/phase25.html").read_text(encoding="utf-8")
    home = (ROOT / "deploy/vercel/index.html").read_text(encoding="utf-8")
    assert 'data-atlas-chart' in phase and 'data-atlas-controls' in phase
    assert 'data-atlas-controls' in home
    assert 'src="/phase25-explorer.js?v=' in phase and 'src="/phase25-explorer.js?v=' in home
    assert "Measured baseline frame outcomes are now" in phase
    assert "Phase 23 paired outcomes remain pending" in phase
    audit = json.loads((ROOT / "docs/phase25_reconstruction_audit.json").read_text(encoding="utf-8"))
    assert audit["archive_derived_protected_image_count"] == 86
    assert audit["frame_condition_count"] == 516
    assert 'class="atlas-inputs"' in phase
    assert 'class="phase25-feature__proof"' in home
    for count in ("86", "516"):
        assert f">{count}</strong>" in phase
        assert f">{count}</b>" in home
    assert "phase25_reconstruction_audit.json" in phase and "phase25_reconstruction_audit.json" in home


def test_phase25_lens_resolves_assets_under_a_project_page_base_path() -> None:
    script = (ROOT / "deploy/vercel/phase25-explorer.js").read_text(encoding="utf-8")

    assert "new URL('.', document.currentScript?.src || window.location.href)" in script
    assert "fetch(new URL('phase25-explorer-data.json', appBase))" in script
    assert "photo.src = appAsset(chosen.illustration)" in script
    assert "String.fromCharCode(47)" in script


def test_vercel_home_is_native_frozen_archive_shell() -> None:
    html = (ROOT / "deploy" / "vercel" / "index.html").read_text(encoding="utf-8")

    assert 'data-site-shell="native frozen-archive"' in html
    assert 'data-editorial-media="local-v2"' in html
    assert "document.write" not in html
    assert "cdn.jsdelivr.net/gh/suhaslord/uav-safety-research" not in html
    assert "const rev=" not in html
    assert 'id="evidenceSpine"' in html
    assert 'src="/frozen-lineage.js?v=' in html
    assert "Model VASE · answer so far" in html
    assert 'id="current-audit"' in html
    assert 'id="phase25"' in html
    assert '<a class="button primary signature-button" href="/model-vase/">Model VASE</a>' in html
    assert "Can the system know when its landing estimate is unreliable?" in html
    assert "These are different experiments. They have not been joined into one tested model." in html
    assert "97.6%" in html and "−13.3 pp" in html
    assert "Baseline measured · Phase 23 pending" in html
    assert "0.8319" in html
    assert "0.7744" in html
    assert "simulation_only=true" in html
    assert "safety_acceptance=false" in html
    assert "controller_tuning_allowed=false" in html
    # Keep the scientific boundary semantic instead of coupling QA to retired prose.
    assert "Simulation and benchmark results only. No flight-safety claim, certification claim, or controller-tuning claim." in html
    assert 'name="aegis-evidence-boundary"' in html


def test_model_vase_page_reports_separate_evidence_without_claiming_a_fused_model() -> None:
    page = (ROOT / "deploy" / "vercel" / "model-vase.html").read_text(encoding="utf-8")
    stylesheet = (ROOT / "deploy" / "vercel" / "model-vase.css").read_text(encoding="utf-8")
    evidence_script = (ROOT / "deploy" / "vercel" / "model-vase-evidence.js").read_text(encoding="utf-8")
    mark = (ROOT / "deploy" / "vercel" / "model-vase-mark.svg").read_text(encoding="utf-8")

    assert "Model VASE" in page
    assert "2.4%" in page and "1.4%" in page and "84.2%" in page
    assert "+3.4 pp" in page and "−13.3 pp" in page
    assert "10,000 simulated episodes" in page and "Paired frame transitions cannot be reported" in page
    assert "integrated research architecture, not a newly trained checkpoint" in page
    assert "V3 PATH · CONNECTED" in page and "PHASE 12 · NOT YET CONNECTED" in page
    assert "Only the V3 simulation path is connected" in page
    assert "docs/v3_results.md" in page
    assert "PHASES 10R–12" in page and "KIOS frames" in page
    assert "vase-evidence-card" in page and "/failure-atlas/" in page
    assert 'data-evidence-button="simulation"' in page and 'data-evidence-button="vision"' in page
    assert 'data-evidence-panel="simulation"' in page and 'data-evidence-panel="vision"' in page
    assert "activate('vision')" in evidence_script and "ArrowRight" in evidence_script
    assert 'href="/aegisland-brand.css?v=' in page
    assert "#e82127" in stylesheet and "#3e6ae1" not in stylesheet and "prefers-reduced-motion" in stylesheet
    assert 'viewBox="0 0 48 48"' in mark


def test_local_visual_qa_server_serves_model_vase_evidence_switch_script() -> None:
    server = (ROOT / ".github" / "qa" / "local-vercel-server.mjs").read_text(encoding="utf-8")

    assert "'model-vase-evidence.js'" in server


def test_homepage_videos_have_webm_fallbacks_for_browsers_without_h264() -> None:
    page = (ROOT / "deploy" / "vercel" / "index.html").read_text(encoding="utf-8")
    qa_server = (ROOT / ".github" / "qa" / "local-vercel-server.mjs").read_text(encoding="utf-8")

    assert page.count('type="video/webm"') == 2
    assert page.count('type="video/mp4"') == 2
    assert (ROOT / "deploy" / "vercel" / "film" / "aerocast-flight.webm").is_file()
    assert (ROOT / "deploy" / "vercel" / "film" / "evaluation-nasa-clip.webm").is_file()
    assert "'.webm': 'video/webm'" in qa_server


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
    assert "/phase23.html" in destinations
    assert "/phase24.html" in destinations
    assert "/phase25.html" in destinations
    assert "/model-vase.html" in destinations
    assert "/failure-atlas.html" in destinations
    assert {"/model-vase", "/model-vase/"} == {item["source"] for item in rewrites if item["destination"] == "/model-vase.html"}
    assert {"/failure-atlas", "/failure-atlas/"} == {item["source"] for item in rewrites if item["destination"] == "/failure-atlas.html"}
    assert {"/reproduce", "/reproduce/"} == {item["source"] for item in rewrites if item["destination"] == "/reproduce.html"}
    phase23_sources = {item["source"] for item in rewrites if item["destination"] == "/phase23.html"}
    assert "/phases/phase23" in phase23_sources and "/phases/phase23/" in phase23_sources
    phase24_sources = {item["source"] for item in rewrites if item["destination"] == "/phase24.html"}
    assert "/phases/phase24" in phase24_sources and "/phases/phase24/" in phase24_sources
    phase25_sources = {item["source"] for item in rewrites if item["destination"] == "/phase25.html"}
    assert "/phases/phase25" in phase25_sources and "/phases/phase25/" in phase25_sources
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

    assert "--phase-blue:#e82127" in polish
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
    assert "Keep every result in view." in archive
    assert "Research categories" in archive
    assert "<strong>7</strong> research categories" in archive
    assert "28 phase records" in archive
    assert "6 PASS / 7 FAIL" in archive
    assert "Phase 23 detector and Phase 24 audit are separate" in archive


def test_phase_taxonomy_personalizes_all_28_phase_routes() -> None:
    taxonomy = (ROOT / "dashboard" / "phase-taxonomy.js").read_text(encoding="utf-8")
    personalization = (ROOT / "dashboard" / "phase-personalization.js").read_text(encoding="utf-8")
    css = (ROOT / "dashboard" / "phase-personalization.css").read_text(encoding="utf-8")

    expected_slugs = (
        "phase1", "phase2", "phase3", "phase4", "phase5", "phase6", "phase6b",
        "phase7", "phase8", "phase9", "phase10", "phase10r", "phase11", "phase12",
        "phase13a", "phase13b", "phase13c", "phase14", "phase15", "phase16", "phase17",
        "phase18", "phase19", "phase20", "phase21", "phase22", "phase23", "phase24",
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
        "real-camera-robustness",
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

    assert phase.rfind('src="/phase-personalization.js?v=') > phase.rfind('src="/aegis-current.js"')
    assert phase.rfind('src="/phase-editorial-media.js?v=1"') > phase.rfind('src="/phase-personalization.js?v=')


def test_phase10r_logic_is_loaded_by_the_shared_phase_template() -> None:
    html = (ROOT / "dashboard" / "phases" / "phase.html").read_text(encoding="utf-8")

    phase10r = html.index('src="/phase10r-archive.js"')
    scenes = html.index('src="/phase-hero-scenes.js"')
    assert phase10r < scenes


def test_phase24_standalone_report_has_charts_provenance_and_method_limits() -> None:
    report = (ROOT / "deploy" / "vercel" / "phase24.html").read_text(encoding="utf-8")
    script = (ROOT / "deploy" / "vercel" / "phase24.js").read_text(encoding="utf-8")
    data = json.loads((ROOT / "deploy" / "vercel" / "data" / "phase24-results.json").read_text(encoding="utf-8"))

    assert 'src="/phase24.js?v=1"' in report
    assert report.count('data-phase24-chart=') == 4
    assert "No model was retrained" in report
    assert "not 516 independent examples" in report
    assert "confidence intervals" in report
    assert "Detector precision, recall, and mAP do not demonstrate landing safety" in report
    assert data["analysis_type"] == "descriptive_reanalysis"
    assert 'fetch("/data/phase24-results.json"' in script


def test_phase23_report_and_phase24_share_a_report_layout() -> None:
    phase23 = (ROOT / "deploy" / "vercel" / "phase23.html").read_text(encoding="utf-8")
    phase24 = (ROOT / "deploy" / "vercel" / "phase24.html").read_text(encoding="utf-8")
    css = (ROOT / "deploy" / "vercel" / "phase-report.css").read_text(encoding="utf-8")
    assert 'href="/phase-report.css?v=' in phase23
    assert 'href="/phase-report.css?v=' in phase24
    assert '.record-path' in css
    assert 'href="/phases/phase24/"' in phase23
    assert 'href="/phases/phase23/"' in phase24
    assert phase23.count('<tr class="severe">') == 2
    assert "separate from the frozen Phase 1–22 simulation record" in phase23
    gallery = re.findall(r'<figure><img src="([^"]+)" width="640" height="585"[^>]*loading="eager"', phase23)
    assert len(gallery) == 6
    assert all((ROOT / "deploy/vercel" / source.lstrip("/")).is_file() for source in gallery)
    assert "These are condition examples, not detector-output overlays" in phase23
    assert 'id="checkpoint-recovery"' in phase23
    assert "py scripts\\bundle_phase23_checkpoint.py" in phase23


def test_phase25_is_featured_as_work_in_progress_without_result_claims() -> None:
    home = (ROOT / "deploy" / "vercel" / "index.html").read_text(encoding="utf-8")
    page = (ROOT / "deploy" / "vercel" / "phase25.html").read_text(encoding="utf-8")
    archive = (ROOT / "dashboard" / "phases" / "index.html").read_text(encoding="utf-8")

    assert home.index('id="phase25"') < home.index('id="status"')
    assert 'href="/phases/phase25/"' in archive
    assert 'aria-label="Model VASE overview"' in archive
    assert 'aria-label="Current Phase 25 work"' in archive
    assert 'href="/phase-report.css?v=' in page
    assert 'class="atlas-status"' in page
    assert "Inputs verified" in page
    assert "KIOS inputs verified" in archive
    assert "Results await the exact model and source images" not in archive
    assert "The 86-frame set was already used in Phases 23–24" in page
    assert "not either detector’s predictions" in page
    assert "original Phase 23 checkpoint" in page


def test_failure_atlas_is_baseline_only_with_auditable_tables() -> None:
    site = json.loads((ROOT / "deploy/vercel/failure-atlas-data.json").read_text())
    manifest = json.loads((ROOT / "results/phase25_baseline_diagnostic/run_manifest.json").read_text())
    comparison_path = ROOT / "results/phase23_robust_detector/robustness_comparison.csv"
    with comparison_path.open(newline="", encoding="utf-8") as handle:
        comparison = {row["condition"]: row for row in csv.DictReader(handle)}
    assert site["status"] == "baseline_only" and site["phase23"] is None
    assert len(site["frame_ids"]) == 86 and len(site["cases"]) == 516
    assert site["prediction_rows"] == manifest["prediction_rows"] == 136359
    assert {key: value for key, value in site["source_hashes"].items() if key != "phase23_comparison_csv"} == manifest["table_sha256"]
    assert site["source_hashes"]["phase23_comparison_csv"] == hashlib.sha256(comparison_path.read_bytes()).hexdigest()
    assert set(site["phase23_condition_aggregates"]) == {"clean", "blur", "low_light", "noise", "occlusion", "mixed"}
    for condition, item in site["phase23_condition_aggregates"].items():
        assert item["map50"] == float(comparison[condition]["phase23_map50"])
        assert item["recall"] == float(comparison[condition]["phase23_recall"])
    assert sum(case["count"] for case in site["cases"]) == site["prediction_rows"]
    assert sum(len(case["boxes"]) + case["omitted"] for case in site["cases"]) == site["prediction_rows"]
    assert sum(case["tp"] for case in site["cases"]) == sum(box[6] for case in site["cases"] for box in case["boxes"])
    assert not any("phase23" in case for case in site["cases"])
    html = (ROOT / "deploy/vercel/failure-atlas.html").read_text()
    assert 'id="frame-range"' in html and 'id="scatter"' in html
    assert 'id="evidence-dialog"' in html and 'id="local-files"' in html
    assert 'id="local-folder"' in html and "webkitdirectory" in html
    assert 'id="phase23-map50"' in html and 'id="phase23-recall"' in html
    assert 'id="phase23-frame-image"' in html and 'id="phase23-image-placeholder"' in html
    assert "These are not predictions for this frame" in html
    assert "Loading the verified 86-frame image set" in html
    assert "Images selected locally are not hash-checked" in html
    assert 'href="/aegisland-brand.css?v=2"' in html
    atlas_js = (ROOT / "deploy/vercel/failure-atlas.js").read_text(encoding="utf-8")
    assert "`/media/phase25/${condition}/${item.id}`" in atlas_js
    assert "Verified ${names[condition].toLowerCase()} frame image loaded" in atlas_js


def test_phase23_displayed_condition_table_matches_committed_csv() -> None:
    html = (ROOT / "deploy" / "vercel" / "phase23.html").read_text(encoding="utf-8")
    body = re.search(r"<tbody>(.*?)</tbody>", html, re.S)
    assert body is not None
    displayed = [
        [re.sub(r"<[^>]+>", "", cell).strip() for cell in re.findall(r'<td(?: class="[^"]+")?>(.*?)</td>', row, re.S)]
        for row in re.findall(r'<tr(?: class="severe")?>(.*?)</tr>', body.group(1), re.S)
    ]
    with (ROOT / "results" / "phase23_robust_detector" / "robustness_comparison.csv").open(newline="") as source:
        rows = list(csv.DictReader(source))

    def pct(value: str) -> str:
        return f"{100 * float(value):.1f}%"

    def pp(value: str) -> str:
        number = 100 * float(value)
        return f"{'+' if number >= 0 else '−'}{abs(number):.1f} pp"

    labels = {"clean": "Clean", "blur": "Blur", "low_light": "Low light", "noise": "Noise", "occlusion": "Occlusion", "mixed": "Mixed stress"}
    expected = [
        [labels[row["condition"]], pct(row["baseline_map50"]), pct(row["phase23_map50"]), pp(row["map50_gain"]),
         pct(row["baseline_recall"]), pct(row["phase23_recall"]), pp(row["recall_gain"])]
        for row in rows
    ]
    assert displayed == expected


def test_live_perception_panels_and_phase_reading_width_are_balanced() -> None:
    current = (ROOT / "deploy" / "vercel" / "lab" / "current-data.js").read_text(encoding="utf-8")
    shared = (ROOT / "deploy" / "vercel" / "phase-ui-consistency.css").read_text(encoding="utf-8")

    assert "width:min(1440px,calc(100% - 64px))" in current
    assert "grid-template-columns:minmax(0,1fr) minmax(0,1fr)" in current
    assert ".perception-card__frame--square{aspect-ratio:16/9;width:100%" in current
    assert 'href="/phases/phase23/">Read Phase 23' in current
    assert 'href="/phases/phase24/">Open charts and results' in current
    assert "width:min(1280px,calc(100% - 48px))" in shared
    assert "grid-template-columns:minmax(0,1.2fr) minmax(340px,.8fr)" in shared
