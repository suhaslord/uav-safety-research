"""Phase 23 Occlusion Topology Generator.

Generates controlled occlusion masks over annotated landing-pad bounding boxes
using multiple mask geometries (CENTER, OUTER_RING, STRIPED, RANDOM_PATCH) at
parametric dose levels (fraction of annotation-box area occluded).

This generator is the image-manipulation core for the Phase 23 Occlusion
Topology Experiment (Phase 25 sub-study). It does NOT run model inference.

Determinism guarantees:
- All randomness is seeded from (global_seed, frame_name, topology, dose).
- The same inputs always produce byte-identical outputs.
- Atomic writes with fsync prevent partial files.

Usage:
    python scripts/generate_occlusion_topology.py \\
        --manifest results/phase25_failure_atlas/protected_test_manifest.csv \\
        --stress-root <path_to_kios_real_stress> \\
        --out results/phase25_occlusion_topology/generated \\
        --protocol docs/phase25_phase23_occlusion_topology_protocol.json \\
        --dry-run
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import numpy as np
from PIL import Image, ImageDraw

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TOPOLOGIES = ("CENTER", "OUTER_RING", "STRIPED", "RANDOM_PATCH")
DEFAULT_DOSES = (0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45,
                 0.50, 0.55, 0.60, 0.65, 0.70)
GLOBAL_SEED = 20261001
FILL_COLOR = (128, 128, 128)  # neutral gray occluder

# Protected manifest SHA (must match before generation)
PROTECTED_MANIFEST_SHA256 = (
    "8605cf1cbf9e8769c0324bf066078f9964f232ac3128131c8bd0b689bb7b64b7"
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class YoloBox:
    """YOLO-format bounding box (normalized coordinates)."""
    class_id: int
    x_center: float
    y_center: float
    width: float
    height: float

    @property
    def area(self) -> float:
        return self.width * self.height

    def to_pixel(self, img_w: int, img_h: int) -> tuple[float, float, float, float]:
        """Return (x0, y0, x1, y1) in pixel coordinates."""
        cx = self.x_center * img_w
        cy = self.y_center * img_h
        w = self.width * img_w
        h = self.height * img_h
        return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


@dataclass
class OcclusionRecord:
    """One row of the output schema."""
    frame_id: str
    sequence: str
    topology: str
    requested_dose: float
    achieved_dose: float
    dose_error: float
    mask_pixels: int
    box_pixels: int
    image_path: str
    label_path: str
    source_image_sha256: str
    occluded_image_sha256: str
    # Prediction fields are NULL — populated by inference runner later
    pred_count: str = ""
    best_iou: str = ""
    best_confidence: str = ""
    tp: str = ""
    fp: str = ""
    fn: str = ""
    frame_success: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _rng_for(frame_name: str, topology: str, dose: float) -> np.random.Generator:
    """Deterministic PRNG keyed to (GLOBAL_SEED, frame, topology, dose)."""
    key = f"{GLOBAL_SEED}:{frame_name}:{topology}:{dose:.4f}"
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return np.random.default_rng(int.from_bytes(digest[:8], "little"))


def read_yolo_label(label_path: Path) -> list[YoloBox]:
    """Read YOLO label file and return list of YoloBox."""
    boxes = []
    for line in label_path.read_text(encoding="utf-8").strip().splitlines():
        parts = line.strip().split()
        if len(parts) >= 5:
            boxes.append(YoloBox(
                class_id=int(parts[0]),
                x_center=float(parts[1]),
                y_center=float(parts[2]),
                width=float(parts[3]),
                height=float(parts[4]),
            ))
    return boxes


def sha256_file(path: Path) -> str:
    """Compute SHA-256 of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    """Compute SHA-256 of bytes."""
    return hashlib.sha256(data).hexdigest()


def atomic_write_image(image: Image.Image, path: Path, quality: int = 95) -> str:
    """Write image atomically with fsync. Returns SHA-256 of written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        suffix=".tmp", dir=str(path.parent)
    )
    try:
        # Write via the file descriptor for reliable fsync
        with os.fdopen(fd, "wb") as f_tmp:
            image.save(f_tmp, format="JPEG", quality=quality)
            f_tmp.flush()
            os.fsync(f_tmp.fileno())
        # fd is now closed by os.fdopen context manager
        # Read back and compute hash before rename
        with open(tmp, "rb") as f:
            data = f.read()
        sha = sha256_bytes(data)
        # Atomic rename (on Windows this replaces)
        os.replace(tmp, str(path))
        return sha
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def verify_manifest_sha(manifest_path: Path) -> None:
    """Verify that the protected manifest has not been tampered with."""
    actual = sha256_file(manifest_path)
    if actual != PROTECTED_MANIFEST_SHA256:
        raise ValueError(
            f"Protected manifest SHA mismatch!\n"
            f"  Expected: {PROTECTED_MANIFEST_SHA256}\n"
            f"  Actual:   {actual}"
        )


# ---------------------------------------------------------------------------
# Mask generators
# ---------------------------------------------------------------------------
def _create_mask_center(
    img_w: int, img_h: int, box: YoloBox, dose: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Center rectangle mask covering `dose` fraction of annotation box area.

    The mask is a centered rectangle inside the annotation box, sized so that
    its area equals dose * box_area. The aspect ratio of the mask matches the
    annotation box aspect ratio.
    """
    mask = np.zeros((img_h, img_w), dtype=np.uint8)
    if dose <= 0.0:
        return mask

    x0, y0, x1, y1 = box.to_pixel(img_w, img_h)
    box_w = x1 - x0
    box_h = y1 - y0
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2

    # Scale factor: mask area = dose * box_area
    # mask_w = box_w * s, mask_h = box_h * s => s^2 = dose => s = sqrt(dose)
    s = min(np.sqrt(dose), 1.0)
    mask_w = box_w * s
    mask_h = box_h * s

    mx0 = int(max(0, cx - mask_w / 2))
    my0 = int(max(0, cy - mask_h / 2))
    mx1 = int(min(img_w, cx + mask_w / 2))
    my1 = int(min(img_h, cy + mask_h / 2))

    mask[my0:my1, mx0:mx1] = 255
    return mask


def _create_mask_outer_ring(
    img_w: int, img_h: int, box: YoloBox, dose: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Outer ring mask: occludes the periphery of the box, leaving center clear.

    At dose d, the outer ring covers d fraction of the box area. The ring is
    defined as: full box minus a centered hole. The hole has area = (1-d) * box_area,
    so hole_scale = sqrt(1-d).
    """
    mask = np.zeros((img_h, img_w), dtype=np.uint8)
    if dose <= 0.0:
        return mask

    x0, y0, x1, y1 = box.to_pixel(img_w, img_h)
    box_w = x1 - x0
    box_h = y1 - y0
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2

    # Fill entire box
    bx0 = int(max(0, x0))
    by0 = int(max(0, y0))
    bx1 = int(min(img_w, x1))
    by1 = int(min(img_h, y1))
    mask[by0:by1, bx0:bx1] = 255

    # Cut a centered hole of area (1 - dose) * box_area
    hole_scale = np.sqrt(max(0.0, 1.0 - dose))
    if hole_scale > 0.0:
        hw = box_w * hole_scale
        hh = box_h * hole_scale
        hx0 = int(max(0, cx - hw / 2))
        hy0 = int(max(0, cy - hh / 2))
        hx1 = int(min(img_w, cx + hw / 2))
        hy1 = int(min(img_h, cy + hh / 2))
        mask[hy0:hy1, hx0:hx1] = 0

    return mask


def _create_mask_striped(
    img_w: int, img_h: int, box: YoloBox, dose: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Horizontal stripe mask within the bounding box.

    Creates alternating horizontal stripes within the annotation box.
    Uses pixel-exact adaptive stripe allocation so that the achieved
    fraction of occluded box rows equals the requested dose.
    """
    mask = np.zeros((img_h, img_w), dtype=np.uint8)
    if dose <= 0.0:
        return mask

    x0, y0, x1, y1 = box.to_pixel(img_w, img_h)
    bx0 = int(max(0, x0))
    by0 = int(max(0, y0))
    bx1 = int(min(img_w, x1))
    by1 = int(min(img_h, y1))

    box_h_px = by1 - by0
    box_w_px = bx1 - bx0
    if box_h_px < 1 or box_w_px < 1:
        return mask

    # Total rows to occlude within the box
    k_total = int(round(dose * box_h_px))
    if dose > 0 and k_total <= 0:
        k_total = 1
    k_total = min(k_total, box_h_px)

    # Number of stripe periods: up to 5, adapt to box height so stripes remain distinct
    n_stripes = min(5, max(1, box_h_px // 4))

    # Partition box_h_px into n_stripes periods as evenly as possible
    period_bounds = np.linspace(0, box_h_px, n_stripes + 1, dtype=int)

    # Distribute k_total occluded rows across the n_stripes periods
    base_occ = k_total // n_stripes
    rem = k_total % n_stripes

    for i in range(n_stripes):
        y_start = by0 + int(period_bounds[i])
        y_end = by0 + int(period_bounds[i + 1])
        h_period = y_end - y_start
        occ_rows = base_occ + (1 if i < rem else 0)
        occ_rows = min(occ_rows, h_period)
        if occ_rows > 0 and y_start < by1:
            mask[y_start : y_start + occ_rows, bx0:bx1] = 255

    return mask


def _create_mask_random_patch(
    img_w: int, img_h: int, box: YoloBox, dose: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Random rectangular patches placed within the annotation box.

    Places small random rectangles until the target dose fraction is
    approximately achieved. The number and size of patches scale with dose.
    Patch placement is deterministic via the seeded PRNG.
    """
    mask = np.zeros((img_h, img_w), dtype=np.uint8)
    if dose <= 0.0:
        return mask

    x0, y0, x1, y1 = box.to_pixel(img_w, img_h)
    bx0 = int(max(0, x0))
    by0 = int(max(0, y0))
    bx1 = int(min(img_w, x1))
    by1 = int(min(img_h, y1))

    box_w_px = bx1 - bx0
    box_h_px = by1 - by0
    box_area = box_w_px * box_h_px
    if box_area < 4:
        return mask

    target_area = dose * box_area
    covered = 0
    max_iterations = 200  # prevent infinite loop

    # Patch size: sqrt(dose/n_patches) of the box dimensions
    n_patches_target = max(3, int(dose * 15))
    patch_area_target = target_area / n_patches_target

    for _ in range(max_iterations):
        if covered >= target_area * 0.98:
            break

        # Random patch size (uniform ± 50% of target patch size)
        side = max(2, int(np.sqrt(patch_area_target)))
        pw = rng.integers(max(1, side // 2), max(2, side * 2))
        ph = rng.integers(max(1, side // 2), max(2, side * 2))
        pw = min(int(pw), box_w_px)
        ph = min(int(ph), box_h_px)

        # Random position within box
        px = bx0 + int(rng.integers(0, max(1, box_w_px - pw + 1)))
        py = by0 + int(rng.integers(0, max(1, box_h_px - ph + 1)))

        # Count new pixels that would be covered
        sub = mask[py:py + ph, px:px + pw]
        new_pixels = np.sum(sub == 0)

        mask[py:py + ph, px:px + pw] = 255
        covered += new_pixels

    return mask


MASK_GENERATORS = {
    "CENTER": _create_mask_center,
    "OUTER_RING": _create_mask_outer_ring,
    "STRIPED": _create_mask_striped,
    "RANDOM_PATCH": _create_mask_random_patch,
}


# ---------------------------------------------------------------------------
# Core generation logic
# ---------------------------------------------------------------------------
def compute_achieved_dose(mask: np.ndarray, box: YoloBox,
                          img_w: int, img_h: int) -> tuple[float, int, int]:
    """Compute achieved dose = occluded_pixels_in_box / box_pixels.

    Returns (achieved_dose, mask_pixels_in_box, box_pixels).
    """
    x0, y0, x1, y1 = box.to_pixel(img_w, img_h)
    bx0 = int(max(0, x0))
    by0 = int(max(0, y0))
    bx1 = int(min(img_w, x1))
    by1 = int(min(img_h, y1))

    box_region = mask[by0:by1, bx0:bx1]
    box_pixels = box_region.size
    if box_pixels == 0:
        return 0.0, 0, 0
    mask_pixels = int(np.sum(box_region > 0))
    return mask_pixels / box_pixels, mask_pixels, box_pixels


def apply_mask(image: Image.Image, mask: np.ndarray,
               fill: tuple[int, int, int] = FILL_COLOR) -> Image.Image:
    """Apply occlusion mask to image. Masked pixels become fill color."""
    arr = np.array(image.convert("RGB"))
    arr[mask > 0] = fill
    return Image.fromarray(arr, mode="RGB")


def generate_one_view(
    image_path: Path,
    label_path: Path,
    topology: str,
    dose: float,
    output_dir: Path,
    frame_id: str,
    sequence: str,
    dry_run: bool = False,
) -> OcclusionRecord:
    """Generate a single occluded view and return the record.

    If dose == 0.0, the image is written unchanged (identity transform).
    If dry_run is True, no files are written; achieved dose is computed in-memory.
    """
    if topology not in MASK_GENERATORS:
        raise ValueError(f"Unknown topology: {topology}")

    img = Image.open(image_path).convert("RGB")
    img_w, img_h = img.size

    boxes = read_yolo_label(label_path)
    if not boxes:
        raise ValueError(f"No YOLO boxes in {label_path}")
    # Use the largest target
    target = max(boxes, key=lambda b: b.area)

    rng = _rng_for(frame_id, topology, dose)

    # Generate mask
    if dose <= 0.0:
        mask = np.zeros((img_h, img_w), dtype=np.uint8)
    else:
        mask = MASK_GENERATORS[topology](img_w, img_h, target, dose, rng)

    # Compute achieved dose
    achieved, mask_px, box_px = compute_achieved_dose(mask, target, img_w, img_h)
    dose_error = abs(achieved - dose)

    # Source image SHA
    source_sha = sha256_file(image_path)

    # Output paths
    dose_str = f"{dose:.2f}".replace(".", "p")
    out_name = f"{frame_id}__{topology}__{dose_str}.jpg"
    out_image_path = output_dir / topology / dose_str / "images" / out_name
    out_label_path = output_dir / topology / dose_str / "labels" / f"{frame_id}__{topology}__{dose_str}.txt"

    if dry_run:
        occluded_sha = "DRY_RUN"
    else:
        # Apply mask and write
        occluded = apply_mask(img, mask) if dose > 0.0 else img.copy()
        occluded_sha = atomic_write_image(occluded, out_image_path)

        # Copy label (annotations are unchanged — occlusion doesn't move the target)
        out_label_path.parent.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy2(label_path, out_label_path)

    return OcclusionRecord(
        frame_id=frame_id,
        sequence=sequence,
        topology=topology,
        requested_dose=dose,
        achieved_dose=round(achieved, 6),
        dose_error=round(dose_error, 6),
        mask_pixels=mask_px,
        box_pixels=box_px,
        image_path=str(out_image_path.relative_to(output_dir)) if not dry_run else f"DRY_RUN/{out_name}",
        label_path=str(out_label_path.relative_to(output_dir)) if not dry_run else f"DRY_RUN/{out_name}",
        source_image_sha256=source_sha,
        occluded_image_sha256=occluded_sha,
    )


# ---------------------------------------------------------------------------
# Batch generation
# ---------------------------------------------------------------------------
def load_manifest(manifest_path: Path) -> list[dict[str, str]]:
    """Load the protected test manifest CSV."""
    verify_manifest_sha(manifest_path)
    rows = []
    with open(manifest_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    if len(rows) != 86:
        raise ValueError(f"Expected 86 frames, got {len(rows)}")
    return rows


def find_clean_image(
    stress_root: Path, image_name: str,
) -> tuple[Path, Path]:
    """Find clean image and label for a manifest entry."""
    img_path = stress_root / "clean" / "images" / "test" / image_name
    label_name = Path(image_name).stem + ".txt"
    label_path = stress_root / "clean" / "labels" / "test" / label_name
    if not img_path.exists():
        raise FileNotFoundError(f"Clean image not found: {img_path}")
    if not label_path.exists():
        raise FileNotFoundError(f"Clean label not found: {label_path}")
    return img_path, label_path


def generate_all(
    manifest_path: Path,
    stress_root: Path,
    output_dir: Path,
    topologies: Sequence[str] = TOPOLOGIES,
    doses: Sequence[float] = DEFAULT_DOSES,
    dry_run: bool = False,
) -> list[OcclusionRecord]:
    """Generate all views for the topology experiment.

    Returns list of OcclusionRecord sorted by (frame_id, topology, dose).
    """
    manifest = load_manifest(manifest_path)
    records: list[OcclusionRecord] = []

    total = len(manifest) * len(topologies) * len(doses)
    count = 0

    for row in manifest:
        seq = row["sequence"]
        frame_idx = row["frame_index"]
        image_name = row["image"]
        frame_id = f"{seq}__{frame_idx}"

        img_path, label_path = find_clean_image(stress_root, image_name)

        for topo in topologies:
            for dose in doses:
                count += 1
                if count % 100 == 0 or count == total:
                    mode = "DRY-RUN" if dry_run else "GENERATING"
                    print(f"  [{mode}] {count}/{total}: {frame_id} {topo} dose={dose:.2f}")

                record = generate_one_view(
                    image_path=img_path,
                    label_path=label_path,
                    topology=topo,
                    dose=dose,
                    output_dir=output_dir,
                    frame_id=frame_id,
                    sequence=seq,
                    dry_run=dry_run,
                )
                records.append(record)

    # Sort deterministically
    records.sort(key=lambda r: (r.frame_id, r.topology, r.requested_dose))
    return records


def write_records_csv(records: list[OcclusionRecord], path: Path) -> str:
    """Write records to CSV. Returns SHA-256 of written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "frame_id", "sequence", "topology", "requested_dose", "achieved_dose",
        "dose_error", "mask_pixels", "box_pixels", "image_path", "label_path",
        "source_image_sha256", "occluded_image_sha256",
        "pred_count", "best_iou", "best_confidence", "tp", "fp", "fn",
        "frame_success",
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records:
            writer.writerow({
                "frame_id": rec.frame_id,
                "sequence": rec.sequence,
                "topology": rec.topology,
                "requested_dose": f"{rec.requested_dose:.4f}",
                "achieved_dose": f"{rec.achieved_dose:.6f}",
                "dose_error": f"{rec.dose_error:.6f}",
                "mask_pixels": rec.mask_pixels,
                "box_pixels": rec.box_pixels,
                "image_path": rec.image_path,
                "label_path": rec.label_path,
                "source_image_sha256": rec.source_image_sha256,
                "occluded_image_sha256": rec.occluded_image_sha256,
                "pred_count": rec.pred_count,
                "best_iou": rec.best_iou,
                "best_confidence": rec.best_confidence,
                "tp": rec.tp,
                "fp": rec.fp,
                "fn": rec.fn,
                "frame_success": rec.frame_success,
            })
    return sha256_file(path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate occlusion topology views for Phase 23 experiment.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--manifest", type=Path,
        default=Path("results/phase25_failure_atlas/protected_test_manifest.csv"),
        help="Path to protected test manifest CSV.",
    )
    parser.add_argument(
        "--stress-root", type=Path, required=True,
        help="Path to kios_real_stress directory containing clean/images/test/.",
    )
    parser.add_argument(
        "--out", type=Path,
        default=Path("results/phase25_occlusion_topology/generated"),
        help="Output directory for generated views.",
    )
    parser.add_argument(
        "--topologies", nargs="+", default=list(TOPOLOGIES),
        choices=TOPOLOGIES,
        help="Topologies to generate.",
    )
    parser.add_argument(
        "--doses", nargs="+", type=float,
        default=list(DEFAULT_DOSES),
        help="Dose levels to generate (0.0 to 0.70).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Compute dose feasibility without writing images.",
    )
    args = parser.parse_args()

    # Validate doses
    for d in args.doses:
        if d < 0.0 or d > 1.0:
            parser.error(f"Dose must be in [0.0, 1.0], got {d}")

    print(f"Phase 23 Occlusion Topology Generator")
    print(f"  Manifest:   {args.manifest}")
    print(f"  Stress root: {args.stress_root}")
    print(f"  Output:     {args.out}")
    print(f"  Topologies: {args.topologies}")
    print(f"  Doses:      {args.doses}")
    print(f"  Mode:       {'DRY-RUN' if args.dry_run else 'GENERATE'}")
    print()

    records = generate_all(
        manifest_path=args.manifest,
        stress_root=args.stress_root,
        output_dir=args.out,
        topologies=args.topologies,
        doses=args.doses,
        dry_run=args.dry_run,
    )

    # Write CSV
    csv_path = args.out.parent / "topology_views.csv"
    csv_sha = write_records_csv(records, csv_path)
    print(f"\nWrote {len(records)} records to {csv_path}")
    print(f"  CSV SHA-256: {csv_sha}")

    # Summary statistics
    print(f"\n{'=' * 60}")
    print(f"FEASIBILITY SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total views: {len(records)}")
    print(f"  Frames:     {len(set(r.frame_id for r in records))}")
    print(f"  Topologies: {len(set(r.topology for r in records))}")
    print(f"  Doses:      {len(set(r.requested_dose for r in records))}")

    # Per-topology dose error stats
    from collections import defaultdict
    topo_errors: dict[str, list[float]] = defaultdict(list)
    for r in records:
        if r.requested_dose > 0.0:
            topo_errors[r.topology].append(r.dose_error)

    print(f"\nDose error by topology (excluding dose=0.0):")
    for topo in sorted(topo_errors.keys()):
        errs = topo_errors[topo]
        print(f"  {topo:15s}: mean={np.mean(errs):.4f}  max={np.max(errs):.4f}  "
              f"median={np.median(errs):.4f}  n={len(errs)}")

    # Check dose=0 is identity
    zero_dose = [r for r in records if r.requested_dose == 0.0]
    if zero_dose:
        all_zero_identity = all(r.achieved_dose == 0.0 for r in zero_dose)
        print(f"\nZero-dose identity check: {'PASS' if all_zero_identity else 'FAIL'}")

    print(f"\nMode: {'DRY-RUN (no images written)' if args.dry_run else 'GENERATE (images written)'}")


if __name__ == "__main__":
    main()
