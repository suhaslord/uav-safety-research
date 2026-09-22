from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from uav_safety.real_landing_dataset import read_yolo_boxes


CONDITIONS = ("clean", "blur", "low_light", "noise", "occlusion", "mixed")


def export_kios_frames(frame_name: str, stress_root: Path, labels_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    label_path = labels_dir / f"{frame_name}.txt"
    boxes = read_yolo_boxes(label_path)
    if not boxes:
        raise ValueError(f"No boxes found for {label_path}")
    target = max(boxes, key=lambda b: b.area)

    for cond in CONDITIONS:
        img_path = stress_root / cond / "images" / "test" / f"{frame_name}.jpg"
        if not img_path.exists():
            raise FileNotFoundError(f"Missing {img_path}")

        img = Image.open(img_path).convert("RGB")
        w, h = img.size

        # Target bounding box in image coordinates
        x0 = int(round((target.x_center - target.width / 2) * w))
        y0 = int(round((target.y_center - target.height / 2) * h))
        x1 = int(round((target.x_center + target.width / 2) * w))
        y1 = int(round((target.y_center + target.height / 2) * h))

        draw = ImageDraw.Draw(img)
        # Electric Blue stroke for detected bounding box (#3e6ae1)
        blue = (62, 106, 225)
        white = (255, 255, 255)
        dark = (23, 26, 32)

        # Draw 3px outline
        for offset in range(3):
            draw.rectangle([x0 - offset, y0 - offset, x1 + offset, y1 + offset], outline=blue)

        # Draw clean label pill: "LANDING PAD · KIOS REAL"
        label_text = f"LANDING PAD · {cond.upper()}"
        pill_w = len(label_text) * 7 + 16
        pill_h = 20
        draw.rectangle([x0, max(0, y0 - pill_h), x0 + pill_w, y0], fill=blue)
        draw.text((x0 + 8, max(2, y0 - pill_h + 3)), label_text, fill=white)

        # Resize to standard 640px width maintaining aspect ratio for web performance
        target_w = 640
        target_h = int(round(h * (target_w / w)))
        resized = img.resize((target_w, target_h), resample=Image.Resampling.LANCZOS)

        out_file = output_dir / f"kios_{cond}.jpg"
        resized.save(out_file, quality=90, optimize=True)
        print(f"Exported {out_file} ({target_w}x{target_h})")


if __name__ == "__main__":
    stress = Path("data/derived/kios_real_stress")
    labels = Path("data/derived/kios_real_yolo/labels/test")
    out = Path("deploy/vercel/media/perception")
    export_kios_frames("land_pad2__2100", stress, labels, out)
