import csv
import hashlib
import io
import json
from pathlib import Path
import sys

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_phase22_representation_study as study
from phase22_representation_transform import atomic_write, encode, REPRESENTATIONS, image_difference


@pytest.fixture
def jpeg():
    image = Image.new("RGB", (31, 27))
    image.putdata([(i % 256, (i * 7) % 256, (i * 13) % 256) for i in range(31 * 27)])
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=87)
    return buffer.getvalue()


def test_protected_population_is_exact_and_authenticated():
    frames = study.read_protected_manifest(study.PROTECTED)
    assert len(frames) == 86
    assert study.sha256_file(study.PROTECTED) == study.PROTECTED_MANIFEST_SHA256
    assert study.Counter(f["sequence"] for f in frames) == {"land_pad": 66, "land_pad2": 20}


@pytest.mark.parametrize("representation", REPRESENTATIONS)
def test_transform_determinism_and_decode(jpeg, representation):
    first = encode(jpeg, representation)
    assert first == encode(jpeg, representation)
    with Image.open(io.BytesIO(first)) as image:
        image.load()
        assert image.size == (31, 27)
    if representation == "RAW_SOURCE":
        assert first == jpeg


def test_q95_matches_exact_historical_behavior(jpeg):
    with Image.open(io.BytesIO(jpeg)) as image:
        expected = io.BytesIO()
        image.convert("RGB").save(expected, format="JPEG", quality=95)
    assert encode(jpeg, "HISTORICAL_Q95") == expected.getvalue()


def test_png_is_pixel_identical_and_psnr_is_defined_for_lossy(jpeg):
    lossless = image_difference(jpeg, encode(jpeg, "LOSSLESS_PNG"))
    assert lossless["pixel_mae"] == lossless["pixel_rmse"] == 0
    assert lossless["psnr_db"] is None
    assert lossless["pixels_identical"]
    lossy = image_difference(jpeg, encode(jpeg, "HISTORICAL_Q95"))
    assert lossy["pixel_rmse"] > 0
    assert lossy["psnr_db"] > 0


def test_atomic_writer_rejects_hash_corruption_and_invalid_image(tmp_path, jpeg):
    path = tmp_path / "image.jpg"
    with pytest.raises(ValueError, match="SHA mismatch"):
        atomic_write(path, jpeg, "0" * 64, image=True)
    assert not path.exists()
    corrupt = b"not an image"
    with pytest.raises(Exception):
        atomic_write(path, corrupt, study.digest(corrupt), image=True)
    assert not path.exists()
    atomic_write(path, jpeg, study.digest(jpeg), image=True)
    atomic_write(path, jpeg, study.digest(jpeg), image=True)
    changed = encode(jpeg, "Q90")
    with pytest.raises(ValueError, match="overwrite"):
        atomic_write(path, changed, study.digest(changed), image=True)
    assert path.read_bytes() == jpeg
    assert not list(tmp_path.glob(".pending-*"))


def test_atomic_writer_detects_corruption_after_disk_write(monkeypatch, tmp_path, jpeg):
    original = Path.read_bytes
    def corrupt_pending(path):
        data = original(path)
        return data[:-1] if path.name.startswith(".pending-") else data
    monkeypatch.setattr(Path, "read_bytes", corrupt_pending)
    with pytest.raises(ValueError, match="disk SHA mismatch"):
        atomic_write(tmp_path / "corrupt.jpg", jpeg, study.digest(jpeg), image=True)
    assert not (tmp_path / "corrupt.jpg").exists()
    assert not list(tmp_path.glob(".pending-*"))


def valid_rows():
    return [{"frame_id": f["image"], "representation": rep, "success": i % 2 == 0,
             "TP": int(i % 2 == 0), "FP": i % 3, "FN": int(i % 2 != 0),
             "best_iou": .6 if i % 2 == 0 else .2, "matched_confidence": .8 if i % 2 == 0 else None,
             "best_confidence_any": .8, "prediction_count": 1, "gt_count": 1}
            for i, f in enumerate(study.read_protected_manifest(study.PROTECTED)) for rep in REPRESENTATIONS]


def test_population_rejects_duplicates_and_missing_cases():
    rows = valid_rows()
    study.unique_population(rows)
    for changed in (rows[:-1], rows + [rows[0]], rows[:-1] + [rows[0]]):
        with pytest.raises(ValueError, match="population"):
            study.unique_population(changed)


def test_model_and_settings_lock(monkeypatch, tmp_path):
    monkeypatch.setattr(study, "runtime", lambda: {})
    protocol = {"checkpoint_sha256": study.BASELINE_CHECKPOINT_SHA256, "settings": dict(study.SETTINGS),
                "runtime": {}, "representations": list(REPRESENTATIONS), "method_sha256": {}}
    path = tmp_path / "protocol.json"
    for field in ("checkpoint_sha256", "settings"):
        changed = dict(protocol)
        changed[field] = "wrong" if field == "checkpoint_sha256" else {**study.SETTINGS, "conf": .01}
        path.write_text(json.dumps(changed))
        with pytest.raises(ValueError, match="lock"):
            study.validate_protocol(changed, study.sha256_file(path), path)
    path.write_text(json.dumps(protocol))
    with pytest.raises(ValueError, match="Protocol SHA"):
        study.validate_protocol(protocol, "0" * 64, path)


def test_q95_and_raw_gates_and_nonfinite_rejection():
    aggregates = {"HISTORICAL_Q95": dict(study.REFERENCE), "RAW_SOURCE": {"map50": .423908}}
    kwargs = dict(complete=True, deterministic=True, hashes_verified=True)
    assert study.stage_a_gate(aggregates, **kwargs)["status"] == "PASS"
    for metric in study.REFERENCE:
        bad = {**aggregates, "HISTORICAL_Q95": {**study.REFERENCE, metric: study.REFERENCE[metric] + .0011}}
        assert study.stage_a_gate(bad, **kwargs)["status"] == "FAIL"
    for value in (.426627, float("nan"), float("inf")):
        bad = {**aggregates, "RAW_SOURCE": {"map50": value}}
        assert study.stage_a_gate(bad, **kwargs)["status"] == "FAIL"
    for flag in kwargs:
        assert study.stage_a_gate(aggregates, **{**kwargs, flag: False})["status"] == "FAIL"


@pytest.mark.parametrize("stage_a,zero", [({"status": "FAIL"}, {"status": "PASS"}),
    ({"status": "PASS", "checks": {"all": True}}, {"status": "FAIL"}),
    ({"status": "PASS", "checks": {"all": False}}, {"status": "PASS", "checks": {"all": True}})])
def test_no_treatment_after_failed_gate(stage_a, zero):
    called = []
    with pytest.raises(ValueError, match="prohibited"):
        study.require_treatment_gates(stage_a, zero)
        called.append("detector")
    assert not called


def test_statistics_are_seeded_and_pair_identical_frames():
    rows = valid_rows()
    manifest = [{"frame_id": r["frame_id"], "representation": r["representation"], "pixel_rmse": 1.} for r in rows]
    first = study.paired_analysis(rows, manifest, seed=7, replicates=100)
    assert first == study.paired_analysis(rows, manifest, seed=7, replicates=100)
    assert sum(first["transitions"].values()) == 86
    assert first["exact_mcnemar_p"] == 1
    assert first["statistics"]["best_iou"]["ci95"] == [0., 0.]
    # Construct a single improvement; paired McNemar must use discordant sources, not all variants.
    q95 = next(r for r in rows if r["representation"] == "HISTORICAL_Q95" and not r["success"])
    q95.update(success=True, matched_confidence=.6, TP=1, FN=0)
    changed = study.paired_analysis(rows, manifest, seed=7, replicates=100)
    assert changed["transitions"]["raw_fail_q95_pass"] == 1
    assert changed["transitions"]["raw_pass_q95_fail"] == 0


def test_committed_artifact_schema_and_hashes_when_available():
    output = ROOT / "results/phase22_input_representation"
    if not (output / "run_manifest.json").exists():
        pytest.skip("Study inference has not completed")
    run = json.loads((output / "run_manifest.json").read_text())
    for name, expected in run["output_sha256"].items():
        assert study.sha256_file(output / name) == expected
    assert study.sha256_file(output / "protocol.json") == run["protocol_sha256"]
    with (output / "frame_metrics.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    study.unique_population(rows)
    assert len(rows) == 430
    assert set(rows[0]) == {"frame_id", "sequence", "representation", "success", "TP", "FP", "FN", "gt_count",
                           "best_iou", "matched_confidence", "best_confidence_any", "prediction_count"}
    with (output / "representation_manifest.csv").open(newline="") as handle:
        manifest = list(csv.DictReader(handle))
    study.unique_population(manifest)
    lock = study.load_lock()
    actual = hashlib.sha256()
    for frame in study.read_protected_manifest(study.PROTECTED):
        row = next(r for r in manifest if r["frame_id"] == frame["image"] and r["representation"] == "HISTORICAL_Q95")
        actual.update(f"{frame['image']}:{row['derived_sha256']}\n".encode())
    assert actual.hexdigest() == lock["condition_image_inventory_sha256"]["clean"]
