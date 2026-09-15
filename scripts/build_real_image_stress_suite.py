from __future__ import annotations

from pathlib import Path
import argparse
import hashlib
import shutil

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw

from uav_safety.real_landing_dataset import read_yolo_boxes


CONDITIONS = ("clean", "blur", "low_light", "noise", "occlusion", "mixed")


def _rng_for(name: str, seed: int) -> np.random.Generator:
    digest = hashlib.sha256(f"{seed}:{name}".encode("utf-8")).digest()
    return np.random.default_rng(int.from_bytes(digest[:8], "little"))


def _noise(image: Image.Image, rng: np.random.Generator, sigma: float = 18.0) -> Image.Image:
    arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    arr += rng.normal(0.0, sigma, size=arr.shape)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode="RGB")


def _occlude(image: Image.Image, label_path: Path) -> Image.Image:
    boxes = read_yolo_boxes(label_path)
    if not boxes:
        return image
    target = max(boxes, key=lambda box: box.area)
    width, height = image.size
    cx = target.x_center * width
    cy = target.y_center * height
    # Cover a controlled central portion of the annotated pad rather than the
    # entire object. This tests partial obstruction while keeping the label fixed.
    occ_w = max(8, target.width * width * 0.55)
    occ_h = max(8, target.height * height * 0.55)
    x0, y0 = cx - occ_w / 2, cy - occ_h / 2
    x1, y1 = cx + occ_w / 2, cy + occ_h / 2
    out = image.convert("RGB").copy()
    draw = ImageDraw.Draw(out)
    # Use local-image median-like neutral gray instead of a pure black sticker.
    arr = np.asarray(out)
    fill = tuple(int(v) for v in np.median(arr.reshape(-1, 3), axis=0))
    draw.rectangle((x0, y0, x1, y1), fill=fill)
    return out


def degrade(image: Image.Image, condition: str, label_path: Path, rng: np.random.Generator) -> Image.Image:
    out = image.convert("RGB")
    if condition == "clean":
        return out
    if condition in {"blur", "mixed"}:
        out = out.filter(ImageFilter.GaussianBlur(radius=2.2))
    if condition in {"low_light", "mixed"}:
        out = ImageEnhance.Brightness(out).enhance(0.42)
    if condition in {"noise", "mixed"}:
        out = _noise(out, rng, sigma=20.0 if condition == "noise" else 14.0)
    if condition in {"occlusion", "mixed"}:
        out = _occlude(out, label_path)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Build deterministic stress variants of the protected KIOS real-image test split.")
    parser.add_argument("--split-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("data/derived/kios_real_stress"))
    parser.add_argument("--seed", type=int, default=20260915)
    args = parser.parse_args()

    test_images = args.split_root / "images" / "test"
    test_labels = args.split_root / "labels" / "test"
    images = sorted(path for path in test_images.iterdir() if path.is_file())
    if not images:
        raise SystemExit(f"No protected test images found in {test_images}")

    if args.out.exists():
        shutil.rmtree(args.out)

    for condition in CONDITIONS:
        image_dir = args.out / condition / "images" / "test"
        label_dir = args.out / condition / "labels" / "test"
        image_dir.mkdir(parents=True, exist_ok=True)
        label_dir.mkdir(parents=True, exist_ok=True)
        for image_path in images:
            label_path = test_labels / f"{image_path.stem}.txt"
            if not label_path.exists():
                raise FileNotFoundError(label_path)
            with Image.open(image_path) as image:
                output = degrade(image, condition, label_path, _rng_for(image_path.name, args.seed))
                output.save(image_dir / image_path.name, quality=95)
            shutil.copy2(label_path, label_dir / label_path.name)

        (args.out / condition / "data.yaml").write_text(
            f"path: {(args.out / condition).resolve()}\n"
            "train: images/test\n"
            "val: images/test\n"
            "test: images/test\n"
            "names:\n"
            "  0: landing_pad\n",
            encoding="utf-8",
        )

    (args.out / "README.md").write_text(
        "# Held-out real-image stress suite\n\n"
        "Generated only from the protected real-image test split. Labels are unchanged.\n\n"
        "- clean: unchanged RGB image\n"
        "- blur: Gaussian blur, radius 2.2 px\n"
        "- low_light: brightness ×0.42\n"
        "- noise: deterministic Gaussian RGB noise, σ=20/255\n"
        "- occlusion: neutral-gray rectangle covering 55% of the annotated pad width/height\n"
        "- mixed: blur + brightness ×0.42 + σ=14/255 noise + partial occlusion\n",
        encoding="utf-8",
    )
    print(f"Built {len(images)} held-out images × {len(CONDITIONS)} conditions at {args.out}")


if __name__ == "__main__":
    main()
