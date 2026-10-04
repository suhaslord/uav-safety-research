"""Regression coverage for the Phase 25 audit's substantive failure modes."""
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
from PIL import Image
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import execute_phase23_occlusion_topology as runner
import phase25_descriptive_analysis as analysis
from phase25_reconstruction_lock import CONDITIONS


def test_support_is_half_open_and_invalid_doses_fail():
    assert analysis.dose_bin(0) == 0
    assert analysis.dose_bin(0.05) == 1
    assert analysis.dose_bin(0.749999) == 7
    assert analysis.dose_bin(0.75) is None
    assert analysis.dose_bin(1) is None
    for value in (-0.01, 1.01, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            analysis.dose_bin(value)


def test_crossing_ignores_upward_crossings_and_missing_bins():
    assert analysis.first_downward_crossing([0.4, 0.6, 0.4]) == pytest.approx(0.15)
    assert analysis.first_downward_crossing([0.6, None, 0.4]) is None
    assert analysis.first_downward_crossing([0.5, 0.5]) is None
    assert analysis.first_downward_crossing([0.6, 0.4]) == pytest.approx(0.0625)


def test_contrast_matches_frame_bins_instead_of_pooling_doses():
    rows = []
    # Both frames have identical within-bin topology outcomes. Unequal dose
    # counts make the pooled means differ despite a zero matched contrast.
    for frame, count in (("first", 10), ("second", 1)):
        for topo, low_count, high_count in (("CENTER", count, 1), ("STRIPED", 1, count)):
            for dose, success, n in ((0.01, "True", low_count), (0.1, "False", high_count)):
                rows.extend(dict(frame_id=frame, sequence="s", topology=topo,
                                 achieved_dose=str(dose), frame_success=success) for _ in range(n))
    result = analysis.topology_summary(rows)
    contrast = result["matched_contrasts"]["CENTER_minus_STRIPED"]
    assert contrast["difference_pp"] == 0
    assert contrast["frames"] == 2
    assert contrast["matched_frame_bins"] == 4
    assert contrast["by_sequence"]["s"]["difference_pp"] == 0


def test_historical_evidence_and_report_agree():
    summary = analysis.build_summary()
    paired = summary["paired"]["overall"]
    assert (paired["recovered"], paired["regressed"], paired["both_pass"], paired["both_fail"]) == (49, 65, 223, 179)
    assert paired["difference_pp"] == pytest.approx(-100 * 16 / 516)
    topology = summary["topology"]
    assert topology["excluded_outside_common_support"] == {"CENTER": 9, "OUTER_RING": 1, "STRIPED": 0, "RANDOM_PATCH": 3}
    assert topology["bins"]["OUTER_RING"][1]["success_rate"] == pytest.approx(101 / 214)
    assert topology["first_observed_downward_crossing"]["OUTER_RING"] == pytest.approx(0.07228173540439206)
    report = analysis.render_report(summary)
    assert "0.072282" in report and "101/214" in report
    assert "never falls below" not in report
    assert "p_value" not in json.dumps(summary)
    assert "diff_ci" not in json.dumps(summary)
    assert summary["historical_zero_dose"]["fp_count_mismatches"] == 268
    assert summary["historical_zero_dose"]["frame_success_mismatches"] == 0


def test_input_pin_rejects_changed_observations(tmp_path):
    (tmp_path / "rows.csv").write_text("a,b\n1,2\n")
    lock = {"source_text_sha256": {"rows.csv": analysis.text_sha(tmp_path / "rows.csv")}}
    (tmp_path / "rows.csv").write_text("a,b\n1,3\n")
    with pytest.raises(ValueError, match="Historical evidence changed"):
        analysis.verify_sources(tmp_path, lock)


@pytest.fixture
def treatment(tmp_path, monkeypatch):
    stress = tmp_path / "stress"
    images, labels = stress / "clean/images/test", stress / "clean/labels/test"
    images.mkdir(parents=True)
    labels.mkdir(parents=True)
    pixels = np.arange(32 * 32 * 3, dtype=np.uint8).reshape(32, 32, 3)
    Image.fromarray(pixels).save(images / "frame.jpg", quality=80)
    (labels / "frame.txt").write_text("0 0.5 0.5 0.7 0.6\n")
    manifest = [{"image": "frame.jpg", "label": "frame.txt", "sequence": "land_pad"}]
    monkeypatch.setattr(runner, "DEFAULT_DOSES", [0.0, 0.5])
    out = tmp_path / "out #1"
    out.mkdir()
    rows = runner.generate_treatment_dataset(manifest, stress, out)
    return stress, out, rows


def test_generated_zero_controls_preserve_source_pixels_and_reject_reuse(treatment):
    stress, out, rows = treatment
    with Image.open(stress / "clean/images/test/frame.jpg") as image:
        expected = np.asarray(image.convert("RGB"))
    zeros = [r for r in rows if r["requested_dose"] == 0]
    assert len(zeros) == 4
    for row in zeros:
        with Image.open(row["image_path"]) as image:
            assert image.format == "PNG"
            np.testing.assert_array_equal(np.asarray(image.convert("RGB")), expected)
    with pytest.raises(ValueError, match="Refusing to reuse"):
        runner.atomic_write_lossless_image(Image.fromarray(expected), Path(zeros[0]["image_path"]))


def test_zero_and_positive_doses_use_the_same_rasterized_denominator(treatment):
    _, _, rows = treatment
    assert len({r["box_pixels"] for r in rows}) == 1
    for row in rows:
        assert row["achieved_dose"] == row["mask_pixels"] / row["box_pixels"]
        assert row["visible_box_fraction"] == 1 - row["achieved_dose"]


def test_gate_evaluates_exact_generated_inventory(treatment):
    _, out, rows = treatment
    controls = [r for r in rows if r["requested_dose"] == 0]

    def val(**kwargs):
        path_line = Path(kwargs["data"]).read_text().splitlines()[0]
        assert json.loads(path_line.removeprefix("path: ")) == str((out / "zero_dose_gate").resolve())
        actual = list((out / "zero_dose_gate/images/test").iterdir())
        assert {p.name for p in actual} == {Path(r["image_path"]).name for r in controls}
        for row in controls:
            assert runner.sha256_file(out / "zero_dose_gate/images/test" / Path(row["image_path"]).name) == row["generated_image_sha256"]
        m = runner.HISTORICAL_CLEAN_METRICS
        return SimpleNamespace(box=SimpleNamespace(mp=m["precision"], mr=m["recall"], map50=m["map50"], map=m["map50_95"]))

    assert runner.run_zero_dose_baseline_gate(SimpleNamespace(val=val), rows, out) == runner.HISTORICAL_CLEAN_METRICS


def test_gate_rejects_missing_or_modified_controls(treatment):
    _, out, rows = treatment
    model = SimpleNamespace(val=lambda **kwargs: pytest.fail("Invalid controls reached inference"))
    with pytest.raises(ValueError, match="Incomplete generated"):
        runner.run_zero_dose_baseline_gate(model, rows[1:], out)
    Path(rows[0]["image_path"]).write_bytes(b"modified")
    with pytest.raises(ValueError, match="Generated control changed"):
        runner.run_zero_dose_baseline_gate(model, rows, out)


def test_failed_gate_prevents_treatment_inference(tmp_path, monkeypatch):
    out = tmp_path / "out"
    calls = []
    monkeypatch.setattr(sys, "argv", ["runner", "--source-root", "source", "--stress-root", "stress",
                                     "--archive", "archive", "--out-dir", str(out)])
    monkeypatch.setattr(runner, "verify_method_lock", lambda: {})
    monkeypatch.setattr(runner, "verify_runtime", lambda: {})
    monkeypatch.setattr(runner, "verify_inputs", lambda *args: ([], tmp_path / "best.pt"))
    monkeypatch.setattr(runner, "generate_treatment_dataset", lambda *args: calls.append("generated") or [])
    monkeypatch.setitem(sys.modules, "ultralytics", SimpleNamespace(YOLO=lambda path: object()))

    def fail_gate(model, rows, output):
        assert calls == ["generated"]
        raise RuntimeError("gate failed")

    monkeypatch.setattr(runner, "run_zero_dose_baseline_gate", fail_gate)
    monkeypatch.setattr(runner, "run_treatment_inference", lambda *args: pytest.fail("Failed gate reached treatments"))
    with pytest.raises(RuntimeError, match="gate failed"):
        runner.main()
    assert not (out / "run_manifest.json").exists()


def test_source_gate_authenticates_pixels_labels_and_inventory(tmp_path, monkeypatch):
    source, stress = tmp_path / "source", tmp_path / "stress"
    (source / "images/test").mkdir(parents=True)
    (source / "labels/test").mkdir(parents=True)
    (source / "images/test/frame.jpg").write_bytes(b"authenticated source image")
    (source / "labels/test/frame.txt").write_text("0 0.5 0.5 0.1 0.1\n")
    rows = [{"image": "frame.jpg", "label": "frame.txt"}]
    lock = {"protected_test_files": {"frame.jpg": {"label": "frame.txt",
            "image_sha256": runner.sha256_file(source / "images/test/frame.jpg"),
            "label_sha256": runner.sha256_file(source / "labels/test/frame.txt")}},
            "condition_image_inventory_sha256": {}}
    for condition in CONDITIONS:
        images, labels = stress / condition / "images/test", stress / condition / "labels/test"
        images.mkdir(parents=True)
        labels.mkdir(parents=True)
        (images / "frame.jpg").write_bytes(b"authenticated stress image")
        (labels / "frame.txt").write_bytes((source / "labels/test/frame.txt").read_bytes())
        lock["condition_image_inventory_sha256"][condition] = runner.hashlib.sha256(
            f"frame.jpg:{runner.sha256_file(images / 'frame.jpg')}\n".encode()).hexdigest()
    monkeypatch.setattr(runner, "load_lock", lambda: lock)
    monkeypatch.setattr(runner, "verify_archive", lambda *args: None)
    runner.verify_source_inventory(rows, source, stress, tmp_path / "archive")
    (source / "images/test/extra.jpg").write_bytes(b"unexpected")
    with pytest.raises(ValueError, match="Incorrect protected source"):
        runner.verify_source_inventory(rows, source, stress, tmp_path / "archive")
    (source / "images/test/extra.jpg").unlink()
    (stress / "clean/images/test/frame.jpg").write_bytes(b"tampered stress")
    with pytest.raises(ValueError, match="image bytes differ"):
        runner.verify_source_inventory(rows, source, stress, tmp_path / "archive")
    (source / "labels/test/frame.txt").write_text("0 0.5 0.5 0.9 0.9\n")
    with pytest.raises(ValueError, match="source label differs"):
        runner.verify_source_inventory(rows, source, stress, tmp_path / "archive")


def test_runtime_gate_rejects_changed_version(monkeypatch):
    expected = json.loads((ROOT / "docs/phase25_input_lock.json").read_text())["phase25_runtime"]
    monkeypatch.setattr(runner.platform, "python_version", lambda: expected["python_version"])
    monkeypatch.setattr(runner.importlib.metadata, "version", lambda name: expected[f"{name}_version"])
    assert runner.verify_runtime() == {key: value for key, value in expected.items() if key != "status"}
    monkeypatch.setattr(runner.importlib.metadata, "version", lambda name: "wrong version")
    with pytest.raises(ValueError, match="runtime mismatch"):
        runner.verify_runtime()


def test_output_rejects_historical_and_stale_directories(tmp_path):
    runner.require_fresh_output(tmp_path / "new")
    with pytest.raises(ValueError, match="historical topology"):
        runner.require_fresh_output(ROOT / "results/phase25_occlusion_topology/new")
    for directory in ("phase25_failure_atlas", "research_revalidation_2026_10_03", "phase23_robust_detector"):
        with pytest.raises(ValueError, match="frozen release directories"):
            runner.require_fresh_output(ROOT / "results" / directory / "new-replay")
    (tmp_path / "stale").write_text("retained result")
    with pytest.raises(ValueError, match="new or empty"):
        runner.require_fresh_output(tmp_path)


def test_method_protocol_pins_complete_current_implementation():
    protocol = json.loads(runner.PROTOCOL_V2_PATH.read_text())
    for path, expected in protocol["method_text_sha256"].items():
        assert analysis.text_sha(ROOT / path) == expected, path
    assert "scripts/execute_phase23_occlusion_topology.py" in protocol["method_text_sha256"]


def test_current_outputs_and_public_summaries_are_reproducible():
    completed = subprocess.run([sys.executable, str(ROOT / "scripts/phase25_descriptive_analysis.py"), "--check"],
                               cwd=ROOT, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stdout + completed.stderr
