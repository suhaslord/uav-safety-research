"""Phase 27 augmentation and paired training are development-only."""
from __future__ import annotations

import csv
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image
import pytest

from scripts.prepare_phase27_dev_augmentation import (
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
    from scripts import train_phase27_dev_candidate as runner
    root, sha, protected = sample_split(tmp_path)
    candidate = tmp_path / "candidate"
    build(root, candidate, variants=1, locked_sha=sha, protected_manifest=protected)
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
    assert sum(kind == "val" for kind, _ in calls) == 2


def test_changed_validation_file_blocks_training(tmp_path, monkeypatch):
    from scripts import train_phase27_dev_candidate as runner
    root, sha, protected = sample_split(tmp_path)
    candidate = tmp_path / "candidate"
    build(root, candidate, variants=1, locked_sha=sha, protected_manifest=protected)
    original_verify_split = verify_split
    monkeypatch.setattr(runner, "verify_split", lambda location:
                        original_verify_split(location, locked_sha=sha,
                                              protected_manifest=protected))
    Image.new("RGB", (100, 80), (0, 1, 2)).save(candidate / "images/val/val__0003.png")
    with pytest.raises(ValueError, match="validation images differ"):
        runner.train_pair(root, candidate, tmp_path / "comparison", model_factory=lambda _: None)
    assert not (tmp_path / "comparison").exists()
