from __future__ import annotations

from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

from uav_safety.image_perception import (
    SyntheticLandingPadRenderer,
    SyntheticImageConfig,
    ThresholdPadEstimator,
    IMAGE_CONDITIONS,
)


def export_synthetic_frames(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    cfg = SyntheticImageConfig(image_size=96)
    renderer = SyntheticLandingPadRenderer(cfg)
    estimator = ThresholdPadEstimator(cfg)

    # Seed for deterministic reproducible rendering
    rng_base = 20260922

    conditions = list(IMAGE_CONDITIONS) + ["noise"]
    for condition in conditions:
        rng = np.random.default_rng(rng_base)
        # Altitude 2.5m, slight lateral offset 0.45m
        actual_cond = condition if condition in IMAGE_CONDITIONS else "clean"
        raw_frame = renderer.render(
            x_offset_m=0.45,
            altitude_m=2.5,
            rng=rng,
            condition=actual_cond,
            severity=1.2 if actual_cond != "clean" else 1.0,
        )
        if condition == "noise":
            noise = rng.normal(0.0, 0.18, size=raw_frame.shape)
            raw_frame = np.clip(raw_frame + noise, 0.0, 1.0)

        estimate = estimator.estimate(raw_frame)

        # Convert to 8-bit RGB
        frame_uint8 = np.clip(raw_frame * 255.0, 0, 255).astype(np.uint8)
        img = Image.fromarray(frame_uint8, mode="L").convert("RGB")

        # Scale up cleanly to 384x384 (4x) using Nearest Neighbor to showcase true 96x96 pixel sensor resolution
        scale = 4
        scaled = img.resize((96 * scale, 96 * scale), resample=Image.Resampling.NEAREST)
        draw = ImageDraw.Draw(scaled)

        # Draw detected centroid if valid
        if estimate.valid and np.isfinite(estimate.centroid_x_px):
            cx = estimate.centroid_x_px * scale
            cy = (96 / 2) * scale
            # Crosshair in Electric Blue (#3e6ae1)
            arm = 14
            color = (62, 106, 225)
            draw.line([(cx - arm, cy), (cx + arm, cy)], fill=color, width=2)
            draw.line([(cx, cy - arm), (cx, cy + arm)], fill=color, width=2)
            draw.ellipse([(cx - 4, cy - 4), (cx + 4, cy + 4)], outline=color, width=2)

        out_path = output_dir / f"synthetic_{condition}.png"
        scaled.save(out_path, optimize=True)
        print(f"Saved synthetic {condition} frame to {out_path} (valid={estimate.valid}, conf={estimate.confidence:.2f})")


if __name__ == "__main__":
    out = Path("deploy/vercel/media/perception")
    export_synthetic_frames(out)
