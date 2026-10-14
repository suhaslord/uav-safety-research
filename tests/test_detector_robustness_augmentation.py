"""Detector robustness augmentation and paired training are development-only."""
from __future__ import annotations

import csv
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image
import pytest

from scripts.prepare_detector_robustness_augmentation import (
    augment, build, digest, verify_split,
)


def sample_split(tmp_path):
    root = tmp_path / "input"
    for split in ("train", "val"):
        (root / "images" / split).mkdir(parents=True)
        (root / "labels" / split).mkdir(parents=True)
    rows = []
    for index, (split, name) in enumerate([
        ("train", "train__0001.png"), ("train", "train__0002.png"),
        ("val", "val__0003.png"), ("embargo", "held__0004.png"),
        *[("test", f"protected__{i:04d}.jpg") for i in range(86)],
    ]):
        rows.append({"sequence": name.split("__")[0], "frame_index": index,
                     "split": split, "image": name, "label": Path(name).with_suffix(".txt").name})
        if split in ("train", "val"):
            Image.new("RGB", (100, 80), (160, 100, 80)).save(root / "images" / split / name)
            (root / "labels" / split / Path(name).with_suffix(".txt").name).write_text(
                "0 0.5 0.5 0.5 0.5\n")
    manifest = root / "split_manifest.csv"
    with manifest.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    protected = tmp_path / "protected.csv"
    with protected.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["image"])
        writer.writeheader()
        writer.writerows([{"image": row["image"]} for row in rows if row["split"] == "test"])
    return root, digest(manifest), protected


def test_only_train_is_augmented_and_val_is_original(tmp_path):
    root, sha, protected = sample_split(tmp_path)
    out = tmp_path / "candidate"
    receipt = build(root, out, variants=3, locked_sha=sha, protected_manifest=protected)
    assert receipt["original_train"] == 2
    assert receipt["derived_train"] == 6
    assert receipt["original_val"] == 1
    assert receipt["derived_val"] == 0
    assert not (out / "images/test").exists()
    assert not (out / "images/embargo").exists()
    assert len(list((out / "images/train").iterdir())) == 8
    assert len(list((out / "images/val").iterdir())) == 1
    assert (out / "images/val/val__0003.png").read_bytes() == (
        root / "images/val/val__0003.png").read_bytes()
    assert (out / "labels/val/val__0003.txt").read_bytes() == (
        root / "labels/val/val__0003.txt").read_bytes()
    assert "test:" not in (out / "data.yaml").read_text()


def test_reproducible_variants_and_existing_output_refused(tmp_path):
    root, sha, protected = sample_split(tmp_path)
    r1 = build(root, tmp_path / "a", seed=42, variants=2,
               locked_sha=sha, protected_manifest=protected)
    r2 = build(root, tmp_path / "b", seed=42, variants=2,
               locked_sha=sha, protected_manifest=protected)
    assert r1 == r2
    with pytest.raises(FileExistsError):
        build(root, tmp_path / "a", locked_sha=sha, protected_manifest=protected)


def test_protected_names_cannot_be_reassigned_into_train(tmp_path):
    root, sha, protected = sample_split(tmp_path)
    manifest = root / "split_manifest.csv"
    original = manifest.read_text()
    manifest.write_text(original.replace("train,train__0001.png", "test,train__0001.png", 1))
    with pytest.raises(ValueError, match="protected frames"):
        verify_split(root, locked_sha=digest(manifest), protected_manifest=protected)


def test_bad_labels_and_unlisted_files_are_rejected(tmp_path):
    root, sha, protected = sample_split(tmp_path)
    (root / "images/train/extra.png").write_bytes(b"invalid")
    with pytest.raises(ValueError, match="Unlisted"):
        verify_split(root, locked_sha=sha, protected_manifest=protected)
    (root / "images/train/extra.png").unlink()
    (root / "labels/train/train__0001.txt").write_text("0 0.5 0.5 1.5 0.5\n")
    with pytest.raises(ValueError, match="Invalid YOLO"):
        build(root, tmp_path / "bad", locked_sha=sha, protected_manifest=protected)
    assert not (tmp_path / "bad").exists()


def test_partial_obstructions_do_not_fully_hide_targets():
    image = Image.new("RGB", (200, 160), (100, 180, 60))
    box = [(0.5, 0.5, .65, .65)]
    for seed in range(50):
        output, mask_fraction = augment(image, box, "partial_occlusion",
                                        np.random.default_rng(seed))
        assert output.size == image.size
        assert 0 <= mask_fraction <= .165
    with pytest.raises(ValueError, match="Unknown"):
        augment(image, box, "protected_test", np.random.default_rng(1))


def test_paired_training_is_same_seed_and_val_only(tmp_path, monkeypatch):
    from scripts import train_detector_robustness_candidate as runner
    root, sha, protected = sample_split(tmp_path)
    candidate = tmp_path / "candidate"
    build(root, candidate, mode="matched", variants=1,
          locked_sha=sha, protected_manifest=protected)
    original_verify_split = verify_split
    monkeypatch.setattr(runner, "verify_split", lambda location:
                        original_verify_split(location, locked_sha=sha,
                                              protected_manifest=protected))
    calls = []

    class FakeYOLO:
        def __init__(self, weights):
            self.weights = weights
            calls.append(("new", weights))

        def train(self, **kwargs):
            calls.append(("train", kwargs))
            save_dir = Path(kwargs["project"]) / kwargs["name"]
            (save_dir / "weights").mkdir(parents=True)
            (save_dir / "weights/best.pt").write_bytes(kwargs["name"].encode())
            return SimpleNamespace(save_dir=str(save_dir))

        def val(self, **kwargs):
            calls.append(("val", kwargs))
            assert kwargs["split"] == "val"
            assert "test:" not in Path(kwargs["data"]).read_text()
            score = .55 if "candidate" in self.weights else .48
            return SimpleNamespace(box=SimpleNamespace(mp=score, mr=score,
                                                        map50=score, map=score))

    result = runner.train_pair(root, candidate, tmp_path / "comparison",
                               epochs=2, model_factory=FakeYOLO)
    assert result["protected_test_evaluated"] is False
    assert result["independent_validation"] is False
    assert result["model_improvement_established"] is False
    assert result["candidate_minus_baseline"]["map50"] == pytest.approx(.07)
    train_calls = [value for kind, value in calls if kind == "train"]
    assert len(train_calls) == 2
    for key in train_calls[0]:
        if key not in {"data", "name"}:
            assert train_calls[0][key] == train_calls[1][key]
    assert sum(kind == "val" for kind, _ in calls) == 12
    assert result["matched_train_images_per_arm"] == 2
    assert result["matched_optimizer_step_budget"] is True
    assert set(result["candidate_minus_baseline_by_condition"]) == {
        "clean", "blur", "low_light", "noise", "partial_occlusion", "mixed"}


def test_changed_validation_file_blocks_training(tmp_path, monkeypatch):
    from scripts import train_detector_robustness_candidate as runner
    root, sha, protected = sample_split(tmp_path)
    candidate = tmp_path / "candidate"
    build(root, candidate, mode="matched", variants=1,
          locked_sha=sha, protected_manifest=protected)
    original_verify_split = verify_split
    monkeypatch.setattr(runner, "verify_split", lambda location:
                        original_verify_split(location, locked_sha=sha,
                                              protected_manifest=protected))
    Image.new("RGB", (100, 80), (0, 1, 2)).save(candidate / "images/val/val__0003.png")
    with pytest.raises(ValueError, match="validation images differ"):
        runner.train_pair(root, candidate, tmp_path / "comparison", model_factory=lambda _: None)
    assert not (tmp_path / "comparison").exists()


def test_matched_replacement_preserves_count_names_and_labels(tmp_path):
    root, sha, protected = sample_split(tmp_path)
    receipt = build(root, tmp_path / "matched", mode="matched", variants=1,
                    replace_fraction=0.5, locked_sha=sha, protected_manifest=protected)
    assert receipt["mode"] == "matched"
    assert receipt["derived_train"] == 0
    assert receipt["transformed_train"] == 1
    assert receipt["training_image_count"] == receipt["original_train"] == 2
    assert len(list((tmp_path / "matched/images/train").iterdir())) == 2
    assert any(row["condition"] != "original" for row in receipt["inventory"])
    for image in (root / "images/train").iterdir():
        assert (tmp_path / "matched/labels/train" / f"{image.stem}.txt").read_bytes() == (
            root / "labels/train" / f"{image.stem}.txt").read_bytes()


def test_stacked_training_rejected_before_fit(tmp_path, monkeypatch):
    from scripts import train_detector_robustness_candidate as runner
    root, sha, protected = sample_split(tmp_path)
    old = tmp_path / "stacked"
    build(root, old, variants=1, locked_sha=sha, protected_manifest=protected)
    original_verify = verify_split
    monkeypatch.setattr(runner, "verify_split", lambda location:
                        original_verify(location, locked_sha=sha,
                                        protected_manifest=protected))
    with pytest.raises(ValueError, match="Candidate receipt fails"):
        runner.train_pair(root, old, tmp_path / "unused", model_factory=lambda _: None)
    assert not (tmp_path / "unused").exists()


def test_matched_candidate_modified_training_label_is_rejected(tmp_path, monkeypatch):
    from scripts import train_detector_robustness_candidate as runner
    root, sha, protected = sample_split(tmp_path)
    new = tmp_path / "matched"
    build(root, new, mode="matched", variants=1, locked_sha=sha, protected_manifest=protected)
    original_verify = verify_split
    monkeypatch.setattr(runner, "verify_split", lambda location:
                        original_verify(location, locked_sha=sha, protected_manifest=protected))
    (new / "labels/train/train__0001.txt").write_text("0 0.5 0.5 0.4 0.4\n")
    with pytest.raises(ValueError, match="training label was changed"):
        runner.train_pair(root, new, tmp_path / "unused", model_factory=lambda _: None)
    assert not (tmp_path / "unused").exists()


def test_photometric_only_training_never_masks_target(tmp_path):
    root, sha, protected = sample_split(tmp_path)
    receipt = build(root, tmp_path / "mild", seed=20261013, variants=1,
                    mode="matched", replace_fraction=0.15,
                    train_condition_set="photometric",
                    locked_sha=sha, protected_manifest=protected)
    assert receipt["train_condition_set"] == "photometric"
    assert receipt["train_conditions"] == ["blur", "low_light", "noise"]
    assert receipt["transformed_train"] == 1
    assert receipt["training_image_count"] == 2
    assert {r["condition"] for r in receipt["inventory"]} <= {
        "original", "blur", "low_light", "noise"}
    assert all(r["masked_fraction_upper_bound"] == 0 for r in receipt["inventory"])
    assert (tmp_path / "mild/images/val/val__0003.png").read_bytes() == (
        root / "images/val/val__0003.png").read_bytes()


def test_unknown_condition_set_is_rejected_before_output(tmp_path):
    root, sha, protected = sample_split(tmp_path)
    with pytest.raises(ValueError, match="documented training condition set"):
        build(root, tmp_path / "bad", mode="matched", variants=1,
              train_condition_set="other", locked_sha=sha,
              protected_manifest=protected)
    assert not (tmp_path / "bad").exists()


def test_development_screen_rejects_clean_and_mixed_regression():
    from scripts.train_detector_robustness_candidate import development_screen
    keys = ("clean", "blur", "low_light", "noise", "partial_occlusion", "mixed")
    baseline = {key: {"precision": 0.6, "recall": 0.3,
                      "map50": 0.35, "map50_95": 0.2} for key in keys}
    candidate = {key: dict(row) for key, row in baseline.items()}
    candidate["noise"]["map50"] += 0.20
    candidate["clean"]["map50"] -= 0.03
    candidate["mixed"]["map50"] -= 0.04
    report = development_screen(baseline, candidate)
    assert report["status"] == "development_screen_fail"
    assert report["gates"]["mean_six_condition_map50_gain"] is True
    assert report["gates"]["clean_map50_no_meaningful_drop"] is False
    assert report["gates"]["mixed_map50_no_large_drop"] is False
    assert report["automatic_model_promotion"] is False


def test_development_screen_requires_all_conditions_and_checks_ranges():
    from scripts.train_detector_robustness_candidate import development_screen
    keys = ("clean", "blur", "low_light", "noise", "partial_occlusion", "mixed")
    rows = {key: {"precision": 0.5, "recall": 0.4,
                  "map50": 0.35, "map50_95": 0.2} for key in keys}
    candidate = {key: dict(row, map50=0.38) for key, row in rows.items()}
    assert development_screen(rows, candidate)["status"] == "development_screen_pass"
    with pytest.raises(ValueError, match="Missing"):
        development_screen(rows, {"clean": candidate["clean"]})
    candidate["noise"]["map50"] = float("nan")
    with pytest.raises(ValueError, match="Invalid"):
        development_screen(rows, candidate)


def test_dev_video_grouping_never_merges_sessions():
    from scripts.train_detector_robustness_candidate import group_development_sessions
    paths = [Path("land_pad__0030.jpg"), Path("land_pad2__0050.jpg"),
             Path("land_pad__0020.jpg"), Path("land_pad2__0051.jpg")]
    grouped = group_development_sessions(paths)
    assert sorted(grouped) == ["land_pad", "land_pad2"]
    assert [p.name for p in grouped["land_pad"]] == [
        "land_pad__0020.jpg", "land_pad__0030.jpg"]
    assert [p.name for p in grouped["land_pad2"]] == [
        "land_pad2__0050.jpg", "land_pad2__0051.jpg"]
    with pytest.raises(ValueError, match="sequence ID"):
        group_development_sessions([Path("missing-id.jpg")])


def test_dev_session_slicing_skips_single_video_synthetic_fixture(tmp_path, monkeypatch):
    from scripts import train_detector_robustness_candidate as runner
    root, sha, protected = sample_split(tmp_path)
    orig = verify_split
    monkeypatch.setattr(runner, "verify_split", lambda location:
                        orig(location, locked_sha=sha, protected_manifest=protected))
    slices, counts = runner.prepare_development_session_slices(
        root, {}, tmp_path / "unused-session-slices")
    assert slices == {}
    assert counts == {"val": 1}
    assert not (tmp_path / "unused-session-slices").exists()
