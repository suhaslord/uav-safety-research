#!/usr/bin/env python3
"""Generate train-only robustness augmentations. No protected-image inference."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

LOCKED_SPLIT_SHA = "32623634069c4f3082b79a6a42bca408c636f4b626e5f7691276257999544905"
CONDITIONS = ("blur", "low_light", "noise", "partial_occlusion", "mixed")
TRAIN_CONDITION_SETS = {
    "all": CONDITIONS,
    "photometric": ("blur", "low_light", "noise"),
}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
REPO = Path(__file__).resolve().parents[1]
PROTECTED_MANIFEST = REPO / "results/phase25_failure_atlas/protected_test_manifest.csv"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def protected_names(path: Path) -> set[str]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    names = {r["image"] for r in rows}
    if len(names) != 86 or len(rows) != 86:
        raise ValueError("Protected test manifest must have 86 unique frames")
    return names


def verify_split(split_root: Path, *, locked_sha: str = LOCKED_SPLIT_SHA,
                 protected_manifest: Path = PROTECTED_MANIFEST) -> tuple[list[Path], list[Path], str]:
    split_root = split_root.resolve()
    manifest = split_root / "split_manifest.csv"
    actual_sha = digest(manifest)
    if actual_sha != locked_sha:
        raise ValueError("Historical split manifest checksum differs from locked KIOS split")
    with manifest.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows or not {"split", "image", "label", "sequence", "frame_index"}.issubset(rows[0]):
        raise ValueError("Split manifest columns are missing")
    by_split: dict[str, set[str]] = {s: set() for s in ("train", "val", "embargo", "test")}
    all_names: set[str] = set()
    for row in rows:
        split, name, label = row["split"], row["image"], row["label"]
        if split not in by_split or Path(name).name != name or Path(label).name != label:
            raise ValueError("Invalid split entry or nested filename")
        if name in all_names or Path(name).with_suffix(".txt").name != label:
            raise ValueError("Duplicate image or mismatched label filename")
        by_split[split].add(name)
        all_names.add(name)
    protected = protected_names(protected_manifest)
    if by_split["test"] != protected or (by_split["train"] | by_split["val"]) & protected:
        raise ValueError("Split/test membership conflicts with protected frames")
    if not by_split["train"] or not by_split["val"]:
        raise ValueError("Both training and development validation images are required")
    protected_hashes: set[str] = set()
    if locked_sha == LOCKED_SPLIT_SHA and protected_manifest == PROTECTED_MANIFEST:
        lock = json.loads((REPO / "docs/phase25_reconstruction_lock.json").read_text())
        if lock.get("split_manifest_sha256") != LOCKED_SPLIT_SHA:
            raise ValueError("Protected evidence lock does not match split")
        protected_hashes = {item["image_sha256"] for item in lock["protected_test_files"].values()}
    selected = {}
    for split in ("train", "val"):
        image_dir = split_root / "images" / split
        label_dir = split_root / "labels" / split
        images = {p.name: p for p in image_dir.iterdir()
                  if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES}
        labels = {p.name for p in label_dir.glob("*.txt")}
        if set(images) != by_split[split] or labels != {
                Path(name).with_suffix(".txt").name for name in images}:
            raise ValueError(f"Unlisted, missing, or mismatched {split} files")
        selected[split] = [images[name] for name in sorted(images)]
        for path in selected[split]:
            if digest(path) in protected_hashes:
                raise ValueError("Protected test image bytes appeared in development input")
    # No images or labels in test/embargo are accessed.
    return selected["train"], selected["val"], actual_sha


def validate_label(path: Path) -> list[tuple[float, float, float, float]]:
    boxes = []
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) != 5 or fields[0] != "0":
            raise ValueError(f"Unexpected class/format in {path.name}")
        cx, cy, width, height = (float(v) for v in fields[1:])
        if (not all(map(math.isfinite, (cx, cy, width, height)))
                or min(width, height) <= 0
                or min(cx - width / 2, cy - height / 2) < -1e-6
                or max(cx + width / 2, cy + height / 2) > 1 + 1e-6):
            raise ValueError(f"Invalid YOLO geometry in {path.name}")
        boxes.append((cx, cy, width, height))
    if not boxes:
        raise ValueError(f"No annotated landing target in {path.name}")
    return boxes


def rng_for(seed: int, filename: str, variant: int) -> np.random.Generator:
    key = hashlib.sha256(f"{seed}:{filename}:{variant}:detector_robustness".encode()).digest()
    return np.random.default_rng(int.from_bytes(key[:8], "little"))


def noise(image: Image.Image, rng: np.random.Generator, sigma: float) -> Image.Image:
    pixels = np.asarray(image.convert("RGB"), dtype=np.float32).copy()
    pixels += rng.normal(0, sigma, pixels.shape)
    return Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8), "RGB")


def occlude(image: Image.Image, boxes: list[tuple[float, float, float, float]],
            rng: np.random.Generator) -> tuple[Image.Image, float]:
    out = image.copy().convert("RGB")
    cx, cy, bw, bh = boxes[int(rng.integers(0, len(boxes)))]
    iw, ih = out.size
    fw, fh = float(rng.uniform(.22, .40)), float(rng.uniform(.22, .40))
    rw, rh = max(1, round(bw * iw * fw)), max(1, round(bh * ih * fh))
    x0, y0 = (cx - bw / 2) * iw, (cy - bh / 2) * ih
    x1, y1 = (cx + bw / 2) * iw, (cy + bh / 2) * ih
    if rw > x1 - x0 or rh > y1 - y0:
        return out, 0.0
    left = max(0, round(rng.uniform(x0, max(x0, x1 - rw))))
    top = max(0, round(rng.uniform(y0, max(y0, y1 - rh))))
    right, bottom = min(iw, left + rw), min(ih, top + rh)
    if left >= right or top >= bottom:
        return out, 0.0
    pixels = np.asarray(out)
    fill = tuple(int(v) for v in np.median(pixels.reshape(-1, 3), axis=0))
    ImageDraw.Draw(out).rectangle((left, top, right - 1, bottom - 1), fill=fill)
    fraction = ((right - left) * (bottom - top)) / max(1, bw * iw * bh * ih)
    return out, min(1.0, fraction)


def augment(image: Image.Image, boxes: list[tuple[float, float, float, float]],
            condition: str, rng: np.random.Generator) -> tuple[Image.Image, float]:
    if condition not in CONDITIONS:
        raise ValueError("Unknown training condition")
    out = image.convert("RGB")
    fraction = 0.0
    if condition in ("blur", "mixed"):
        out = out.filter(ImageFilter.GaussianBlur(radius=float(rng.uniform(.7, 1.8))))
    if condition in ("low_light", "mixed"):
        out = ImageEnhance.Brightness(out).enhance(float(rng.uniform(.5, .8)))
    if condition in ("noise", "mixed"):
        out = noise(out, rng, float(rng.uniform(5, 14)))
    if condition in ("partial_occlusion", "mixed"):
        out, fraction = occlude(out, boxes, rng)
    return out, fraction


def build(split_root: Path, out: Path, *, seed: int = 20261013, variants: int = 2,
          mode: str = "append", replace_fraction: float = 0.5,
          train_condition_set: str = "all",
          locked_sha: str = LOCKED_SPLIT_SHA,
          protected_manifest: Path = PROTECTED_MANIFEST) -> dict:
    if mode not in {"append", "matched"}:
        raise ValueError("Choose append or matched mode")
    if train_condition_set not in TRAIN_CONDITION_SETS:
        raise ValueError("Choose a documented training condition set")
    chosen_conditions = TRAIN_CONDITION_SETS[train_condition_set]
    if variants not in range(1, 6) or (mode == "matched" and variants != 1):
        raise ValueError("Matched mode requires exactly one replacement decision per frame")
    if not math.isfinite(replace_fraction) or not 0 < replace_fraction < 1:
        raise ValueError("Replacement fraction must be finite and strictly between 0 and 1")
    if out.exists():
        raise FileExistsError("Output exists: refusing to overwrite candidate")
    train, val, manifest_sha = verify_split(split_root, locked_sha=locked_sha,
                                            protected_manifest=protected_manifest)
    split_root, out = split_root.resolve(), out.resolve()
    if out == split_root or split_root in out.parents or out in split_root.parents:
        raise ValueError("Output must be outside the original split")
    for originals, split in ((train, "train"), (val, "val")):
        for image in originals:
            validate_label(split_root / "labels" / split / (image.stem + ".txt"))
    for directory in ("images/train", "labels/train", "images/val", "labels/val"):
        (out / directory).mkdir(parents=True, exist_ok=False)
    # Rank only development-train filenames (never protected test labels or pixels).
    # Exactly round(fraction * N) originals are replaced, never appended.
    ranked = sorted(train, key=lambda p: hashlib.sha256(
        f"{seed}:{p.name}:matched".encode("utf-8")).digest())
    n_replace = max(1, min(len(train) - 1, round(len(train) * replace_fraction)))
    replacements = {p.name: chosen_conditions[i % len(chosen_conditions)]
                    for i, p in enumerate(ranked[:n_replace])} if mode == "matched" else {}
    inventory = []
    for originals, split in ((train, "train"), (val, "val")):
        for source in originals:
            label = split_root / "labels" / split / (source.stem + ".txt")
            dest_img = out / "images" / split / source.name
            dest_lbl = out / "labels" / split / label.name
            shutil.copyfile(source, dest_img)
            shutil.copyfile(label, dest_lbl)
            condition = "original"
            fraction = 0.0
            if split == "train" and mode == "matched" and source.name in replacements:
                condition = replacements[source.name]
                boxes = validate_label(label)
                with Image.open(source) as original:
                    generated, fraction = augment(original, boxes, condition,
                                                  rng_for(seed, source.name, 0))
                    if source.suffix.lower() in {".jpg", ".jpeg"}:
                        generated.save(dest_img, format="JPEG", quality=95, subsampling=0)
                    else:
                        generated.save(dest_img)
            inventory.append({"source": source.name, "split": split, "condition": condition,
                              "image": dest_img.relative_to(out).as_posix(),
                              "image_sha256": digest(dest_img), "label_sha256": digest(dest_lbl),
                              "masked_fraction_upper_bound": round(fraction, 5)})
            if split != "train" or mode == "matched":
                continue
            boxes = validate_label(label)
            with Image.open(source) as original:
                for variant in range(variants):
                    rng = rng_for(seed, source.name, variant)
                    condition = chosen_conditions[(int(rng.integers(0, 2**31)) + variant) % len(chosen_conditions)]
                    generated, fraction = augment(original, boxes, condition, rng)
                    filename = f"{source.stem}__aug{variant:02d}.png"
                    target_img = out / "images/train" / filename
                    target_lbl = out / "labels/train" / f"{Path(filename).stem}.txt"
                    generated.save(target_img, format="PNG")
                    shutil.copyfile(label, target_lbl)
                    inventory.append({"source": source.name, "split": "train", "condition": condition,
                                      "image": target_img.relative_to(out).as_posix(),
                                      "image_sha256": digest(target_img),
                                      "label_sha256": digest(target_lbl),
                                      "masked_fraction_upper_bound": round(fraction, 5)})
    (out / "data.yaml").write_text(
        f"path: {out}\ntrain: images/train\nval: images/val\nnames:\n  0: landing_pad\n",
        encoding="utf-8")
    receipt = {"schema": "aegisland.detector_robustness.development-only-aug.v1",
               "status": "candidate_data_prepared",
               "locked_split_sha256": manifest_sha,
               "seed": seed, "mode": mode,
               "train_condition_set": train_condition_set,
               "train_conditions": list(chosen_conditions),
               "replace_fraction": replace_fraction if mode == "matched" else None,
               "variants_per_train_frame": variants,
               "original_train": len(train), "original_val": len(val),
               "derived_train": len(train) * variants if mode == "append" else 0,
               "transformed_train": len(replacements), "training_image_count": len(train) if mode == "matched" else len(train) * (variants + 1),
               "derived_val": 0,
               "protected_test_read": False, "test_or_embargo_copied": False,
               "new_model_trained": False, "protected_test_evaluated": False,
               "independent_sessions_used": False,
               "limitations": "Training candidate only; val shares two KIOS sessions. No protected tuning, independent validation or flight-safety claim.",
               "inventory": inventory}
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split-root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=20261013)
    parser.add_argument("--variants", type=int, default=2)
    parser.add_argument("--mode", choices=("append", "matched"), default="matched")
    parser.add_argument("--replace-fraction", type=float, default=0.5)
    parser.add_argument("--train-condition-set", choices=tuple(TRAIN_CONDITION_SETS),
                        default="all")
    args = parser.parse_args()
    result = build(args.split_root, args.out, seed=args.seed, variants=args.variants,
                   mode=args.mode, replace_fraction=args.replace_fraction,
                   train_condition_set=args.train_condition_set)
    print(json.dumps({k: v for k, v in result.items() if k != "inventory"}, indent=2))


if __name__ == "__main__":
    main()
