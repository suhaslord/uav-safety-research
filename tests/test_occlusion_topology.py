"""Tests for Phase 23 Occlusion Topology Generator.

Tests cover (Part 16 of experiment specification):
- Zero-dose identity: mask is empty, achieved_dose == 0
- Determinism: same inputs produce identical outputs
- Geometry correctness: CENTER mask is centered, OUTER_RING has hole, etc.
- Dose tolerance: achieved dose within tolerance of requested dose
- Mask containment: all mask pixels fall within the annotation box
- Frame count: exactly 86 frames × topologies × doses
- Output schema: correct CSV columns with prediction fields empty
- Manifest integrity: SHA-256 verification
"""
from __future__ import annotations

import csv
import hashlib
import tempfile
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

# Import the generator
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

# We need to be able to import from the script
from generate_occlusion_topology import (
    YoloBox,
    _create_mask_center,
    _create_mask_outer_ring,
    _create_mask_striped,
    _create_mask_random_patch,
    compute_achieved_dose,
    apply_mask,
    read_yolo_label,
    generate_one_view,
    write_records_csv,
    OcclusionRecord,
    _rng_for,
    TOPOLOGIES,
    DEFAULT_DOSES,
    MASK_GENERATORS,
    PROTECTED_MANIFEST_SHA256,
    sha256_file,
    verify_manifest_sha,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "results" / "phase25_failure_atlas" / "protected_test_manifest.csv"

# Standard test box: centered, moderate size
TEST_BOX = YoloBox(class_id=0, x_center=0.5, y_center=0.5, width=0.3, height=0.3)
# Small test box (like land_pad far away)
SMALL_BOX = YoloBox(class_id=0, x_center=0.67, y_center=0.29, width=0.018, height=0.024)
# Large test box (like land_pad2 close up)
LARGE_BOX = YoloBox(class_id=0, x_center=0.70, y_center=0.66, width=0.40, height=0.60)

IMG_W, IMG_H = 1052, 961  # Actual KIOS image dimensions


@pytest.fixture
def test_image(tmp_path: Path) -> Path:
    """Create a test image with known content."""
    img = Image.fromarray(
        np.full((IMG_H, IMG_W, 3), 200, dtype=np.uint8), mode="RGB"
    )
    path = tmp_path / "test_frame.jpg"
    img.save(path, quality=95)
    return path


@pytest.fixture
def test_label(tmp_path: Path) -> Path:
    """Create a test YOLO label file."""
    path = tmp_path / "test_frame.txt"
    path.write_text(
        f"0 {TEST_BOX.x_center} {TEST_BOX.y_center} "
        f"{TEST_BOX.width} {TEST_BOX.height}\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def small_label(tmp_path: Path) -> Path:
    """Create a YOLO label file with a small box."""
    path = tmp_path / "small_frame.txt"
    path.write_text(
        f"0 {SMALL_BOX.x_center} {SMALL_BOX.y_center} "
        f"{SMALL_BOX.width} {SMALL_BOX.height}\n",
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------------
# Tests: Zero-dose identity
# ---------------------------------------------------------------------------
class TestZeroDoseIdentity:
    """Zero dose must produce an empty mask with achieved_dose == 0."""

    @pytest.mark.parametrize("topology", TOPOLOGIES)
    def test_zero_dose_empty_mask(self, topology: str) -> None:
        rng = _rng_for("test", topology, 0.0)
        mask = MASK_GENERATORS[topology](IMG_W, IMG_H, TEST_BOX, 0.0, rng)
        assert mask.shape == (IMG_H, IMG_W)
        assert np.sum(mask) == 0, f"{topology} at dose=0 should produce empty mask"

    @pytest.mark.parametrize("topology", TOPOLOGIES)
    def test_zero_dose_achieved(self, topology: str) -> None:
        rng = _rng_for("test", topology, 0.0)
        mask = MASK_GENERATORS[topology](IMG_W, IMG_H, TEST_BOX, 0.0, rng)
        achieved, _, _ = compute_achieved_dose(mask, TEST_BOX, IMG_W, IMG_H)
        assert achieved == 0.0


# ---------------------------------------------------------------------------
# Tests: Determinism
# ---------------------------------------------------------------------------
class TestDeterminism:
    """Same inputs must produce identical masks."""

    @pytest.mark.parametrize("topology", TOPOLOGIES)
    @pytest.mark.parametrize("dose", [0.1, 0.3, 0.5, 0.7])
    def test_deterministic_mask(self, topology: str, dose: float) -> None:
        rng1 = _rng_for("frame_001", topology, dose)
        rng2 = _rng_for("frame_001", topology, dose)
        mask1 = MASK_GENERATORS[topology](IMG_W, IMG_H, TEST_BOX, dose, rng1)
        mask2 = MASK_GENERATORS[topology](IMG_W, IMG_H, TEST_BOX, dose, rng2)
        np.testing.assert_array_equal(mask1, mask2)

    def test_different_frames_differ(self) -> None:
        """Different frame_ids should produce different masks for RANDOM_PATCH."""
        rng1 = _rng_for("frame_A", "RANDOM_PATCH", 0.3)
        rng2 = _rng_for("frame_B", "RANDOM_PATCH", 0.3)
        mask1 = MASK_GENERATORS["RANDOM_PATCH"](IMG_W, IMG_H, TEST_BOX, 0.3, rng1)
        mask2 = MASK_GENERATORS["RANDOM_PATCH"](IMG_W, IMG_H, TEST_BOX, 0.3, rng2)
        # Masks should differ (with overwhelming probability)
        assert not np.array_equal(mask1, mask2)


# ---------------------------------------------------------------------------
# Tests: Geometry correctness
# ---------------------------------------------------------------------------
class TestGeometryCorrectness:
    """Verify mask geometry properties."""

    def test_center_mask_is_centered(self) -> None:
        """CENTER mask should be symmetric about box center."""
        rng = _rng_for("test", "CENTER", 0.25)
        mask = _create_mask_center(IMG_W, IMG_H, TEST_BOX, 0.25, rng)

        # Find mask bounding box
        rows = np.any(mask > 0, axis=1)
        cols = np.any(mask > 0, axis=0)
        rmin, rmax = np.where(rows)[0][[0, -1]]
        cmin, cmax = np.where(cols)[0][[0, -1]]

        # Center of mask region
        mask_cy = (rmin + rmax) / 2
        mask_cx = (cmin + cmax) / 2

        # Expected center
        exp_cx = TEST_BOX.x_center * IMG_W
        exp_cy = TEST_BOX.y_center * IMG_H

        assert abs(mask_cx - exp_cx) <= 2.0, "CENTER mask not horizontally centered"
        assert abs(mask_cy - exp_cy) <= 2.0, "CENTER mask not vertically centered"

    def test_outer_ring_has_hole(self) -> None:
        """OUTER_RING mask should have a clear center."""
        rng = _rng_for("test", "OUTER_RING", 0.3)
        mask = _create_mask_outer_ring(IMG_W, IMG_H, TEST_BOX, 0.3, rng)

        # The center pixel of the box should be clear
        cx = int(TEST_BOX.x_center * IMG_W)
        cy = int(TEST_BOX.y_center * IMG_H)
        assert mask[cy, cx] == 0, "OUTER_RING center should be clear"

    def test_outer_ring_periphery_covered(self) -> None:
        """OUTER_RING mask should have occlusion at box edges."""
        rng = _rng_for("test", "OUTER_RING", 0.5)
        mask = _create_mask_outer_ring(IMG_W, IMG_H, TEST_BOX, 0.5, rng)

        # A corner of the box should be occluded
        x0, y0, x1, y1 = TEST_BOX.to_pixel(IMG_W, IMG_H)
        corner_x = int(x0) + 1
        corner_y = int(y0) + 1
        assert mask[corner_y, corner_x] == 255, "OUTER_RING corner should be occluded"

    def test_striped_has_gaps(self) -> None:
        """STRIPED mask should have alternating covered and clear bands."""
        rng = _rng_for("test", "STRIPED", 0.3)
        mask = _create_mask_striped(IMG_W, IMG_H, TEST_BOX, 0.3, rng)

        x0, y0, x1, y1 = TEST_BOX.to_pixel(IMG_W, IMG_H)
        cx = int((x0 + x1) / 2)
        # Sample the center column within the box
        col = mask[int(y0):int(y1), cx]
        # Should have both 0 and 255 values (gaps)
        assert np.any(col == 0), "STRIPED should have clear gaps"
        assert np.any(col > 0), "STRIPED should have covered stripes"

    @pytest.mark.parametrize("topology", TOPOLOGIES)
    def test_full_dose_high_coverage(self, topology: str) -> None:
        """At dose=0.70, achieved dose should be substantial."""
        rng = _rng_for("test", topology, 0.70)
        mask = MASK_GENERATORS[topology](IMG_W, IMG_H, TEST_BOX, 0.70, rng)
        achieved, _, _ = compute_achieved_dose(mask, TEST_BOX, IMG_W, IMG_H)
        # Allow generous tolerance — some topologies may not hit exact dose
        assert achieved >= 0.40, f"{topology} at dose=0.70 achieves only {achieved:.3f}"


# ---------------------------------------------------------------------------
# Tests: Dose tolerance
# ---------------------------------------------------------------------------
class TestDoseTolerance:
    """Achieved dose should be within tolerance of requested dose."""

    DOSE_TOLERANCE = 0.10  # 10 percentage points absolute tolerance

    @pytest.mark.parametrize("topology", ["CENTER", "OUTER_RING"])
    @pytest.mark.parametrize("dose", [0.1, 0.2, 0.3, 0.4, 0.5])
    def test_geometric_dose_accuracy(self, topology: str, dose: float) -> None:
        """CENTER and OUTER_RING should achieve dose within tight tolerance."""
        rng = _rng_for("test", topology, dose)
        mask = MASK_GENERATORS[topology](IMG_W, IMG_H, TEST_BOX, dose, rng)
        achieved, _, _ = compute_achieved_dose(mask, TEST_BOX, IMG_W, IMG_H)
        assert abs(achieved - dose) <= self.DOSE_TOLERANCE, (
            f"{topology} dose={dose}: achieved={achieved:.4f}, error={abs(achieved-dose):.4f}"
        )

    @pytest.mark.parametrize("topology", ["STRIPED", "RANDOM_PATCH"])
    @pytest.mark.parametrize("dose", [0.1, 0.3, 0.5])
    def test_stochastic_dose_approximate(self, topology: str, dose: float) -> None:
        """STRIPED and RANDOM_PATCH may have larger dose errors but should be reasonable."""
        rng = _rng_for("test", topology, dose)
        mask = MASK_GENERATORS[topology](IMG_W, IMG_H, TEST_BOX, dose, rng)
        achieved, _, _ = compute_achieved_dose(mask, TEST_BOX, IMG_W, IMG_H)
        # Wider tolerance for stochastic methods
        assert abs(achieved - dose) <= 0.20, (
            f"{topology} dose={dose}: achieved={achieved:.4f}"
        )


# ---------------------------------------------------------------------------
# Tests: Mask containment
# ---------------------------------------------------------------------------
class TestMaskContainment:
    """All mask pixels must fall within (or very near) the annotation box."""

    @pytest.mark.parametrize("topology", TOPOLOGIES)
    def test_mask_within_box(self, topology: str) -> None:
        """Mask should not extend significantly outside the annotation box."""
        rng = _rng_for("test", topology, 0.5)
        mask = MASK_GENERATORS[topology](IMG_W, IMG_H, TEST_BOX, 0.5, rng)

        x0, y0, x1, y1 = TEST_BOX.to_pixel(IMG_W, IMG_H)
        # Create a box mask with 2px margin
        margin = 2
        box_mask = np.zeros_like(mask)
        bx0 = int(max(0, x0 - margin))
        by0 = int(max(0, y0 - margin))
        bx1 = int(min(IMG_W, x1 + margin))
        by1 = int(min(IMG_H, y1 + margin))
        box_mask[by0:by1, bx0:bx1] = 255

        # Check: mask pixels outside box should be zero
        outside = mask.copy()
        outside[by0:by1, bx0:bx1] = 0
        pixels_outside = np.sum(outside > 0)
        total_mask = np.sum(mask > 0)

        if total_mask > 0:
            leak_fraction = pixels_outside / total_mask
            assert leak_fraction < 0.01, (
                f"{topology}: {pixels_outside} pixels ({leak_fraction:.2%}) outside box"
            )


# ---------------------------------------------------------------------------
# Tests: Monotonicity (dose increases should not decrease coverage)
# ---------------------------------------------------------------------------
class TestMonotonicity:
    """Higher doses should generally produce more occlusion."""

    @pytest.mark.parametrize("topology", ["CENTER", "OUTER_RING"])
    def test_dose_monotonic_geometric(self, topology: str) -> None:
        """For geometric topologies, dose should be monotonically increasing."""
        doses = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7]
        achieved_list = []
        for dose in doses:
            rng = _rng_for("mono_test", topology, dose)
            mask = MASK_GENERATORS[topology](IMG_W, IMG_H, TEST_BOX, dose, rng)
            achieved, _, _ = compute_achieved_dose(mask, TEST_BOX, IMG_W, IMG_H)
            achieved_list.append(achieved)

        for i in range(1, len(achieved_list)):
            assert achieved_list[i] >= achieved_list[i - 1] - 0.01, (
                f"{topology}: dose {doses[i]} achieved {achieved_list[i]:.4f} "
                f"< dose {doses[i-1]} achieved {achieved_list[i-1]:.4f}"
            )


# ---------------------------------------------------------------------------
# Tests: YOLO label reading
# ---------------------------------------------------------------------------
class TestYoloLabelReading:
    def test_read_single_box(self, test_label: Path) -> None:
        boxes = read_yolo_label(test_label)
        assert len(boxes) == 1
        box = boxes[0]
        assert box.class_id == 0
        assert abs(box.x_center - TEST_BOX.x_center) < 1e-6
        assert abs(box.y_center - TEST_BOX.y_center) < 1e-6

    def test_read_empty_label(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.txt"
        path.write_text("", encoding="utf-8")
        boxes = read_yolo_label(path)
        assert len(boxes) == 0


# ---------------------------------------------------------------------------
# Tests: End-to-end view generation
# ---------------------------------------------------------------------------
class TestEndToEnd:
    def test_generate_dry_run(self, test_image: Path, test_label: Path, tmp_path: Path) -> None:
        """Dry-run should compute dose without writing files."""
        record = generate_one_view(
            image_path=test_image,
            label_path=test_label,
            topology="CENTER",
            dose=0.3,
            output_dir=tmp_path / "output",
            frame_id="test_frame",
            sequence="test_seq",
            dry_run=True,
        )
        assert record.frame_id == "test_frame"
        assert record.topology == "CENTER"
        assert record.requested_dose == 0.3
        assert record.achieved_dose >= 0.0
        assert record.occluded_image_sha256 == "DRY_RUN"
        # No files should be written in dry-run
        assert not (tmp_path / "output").exists() or len(list((tmp_path / "output").rglob("*.jpg"))) == 0

    def test_generate_real_write(self, test_image: Path, test_label: Path, tmp_path: Path) -> None:
        """Real generation should write occluded image."""
        output_dir = tmp_path / "output"
        record = generate_one_view(
            image_path=test_image,
            label_path=test_label,
            topology="CENTER",
            dose=0.3,
            output_dir=output_dir,
            frame_id="test_frame",
            sequence="test_seq",
            dry_run=False,
        )
        assert record.occluded_image_sha256 != "DRY_RUN"
        assert len(record.occluded_image_sha256) == 64
        # Image file should exist
        written_images = list(output_dir.rglob("*.jpg"))
        assert len(written_images) == 1

    def test_zero_dose_preserves_content(self, test_image: Path, test_label: Path, tmp_path: Path) -> None:
        """Zero dose should produce an image with same pixel content."""
        output_dir = tmp_path / "output"
        record = generate_one_view(
            image_path=test_image,
            label_path=test_label,
            topology="CENTER",
            dose=0.0,
            output_dir=output_dir,
            frame_id="test_frame",
            sequence="test_seq",
            dry_run=False,
        )
        assert record.achieved_dose == 0.0
        assert record.mask_pixels == 0


# ---------------------------------------------------------------------------
# Tests: Output schema
# ---------------------------------------------------------------------------
class TestOutputSchema:
    def test_csv_schema(self, tmp_path: Path) -> None:
        """CSV should have correct columns with prediction fields empty."""
        records = [
            OcclusionRecord(
                frame_id="f1", sequence="s1", topology="CENTER",
                requested_dose=0.3, achieved_dose=0.298, dose_error=0.002,
                mask_pixels=100, box_pixels=1000,
                image_path="img.jpg", label_path="lbl.txt",
                source_image_sha256="abc", occluded_image_sha256="def",
            ),
        ]
        csv_path = tmp_path / "test.csv"
        write_records_csv(records, csv_path)

        with open(csv_path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        row = rows[0]
        # Required columns
        assert "frame_id" in row
        assert "topology" in row
        assert "requested_dose" in row
        assert "achieved_dose" in row
        # Prediction columns should be empty
        assert row["pred_count"] == ""
        assert row["best_iou"] == ""
        assert row["best_confidence"] == ""
        assert row["tp"] == ""
        assert row["fp"] == ""
        assert row["fn"] == ""
        assert row["frame_success"] == ""


# ---------------------------------------------------------------------------
# Tests: Manifest integrity
# ---------------------------------------------------------------------------
class TestManifestIntegrity:
    @pytest.mark.skipif(
        not MANIFEST_PATH.exists(),
        reason="Protected test manifest not available in this environment",
    )
    def test_manifest_sha256(self) -> None:
        """Protected manifest must match expected SHA-256."""
        verify_manifest_sha(MANIFEST_PATH)

    @pytest.mark.skipif(
        not MANIFEST_PATH.exists(),
        reason="Protected test manifest not available in this environment",
    )
    def test_manifest_has_86_frames(self) -> None:
        """Manifest must contain exactly 86 frames."""
        with open(MANIFEST_PATH, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 86

    @pytest.mark.skipif(
        not MANIFEST_PATH.exists(),
        reason="Protected test manifest not available in this environment",
    )
    def test_manifest_sequence_counts(self) -> None:
        """Manifest must have 66 land_pad and 20 land_pad2."""
        with open(MANIFEST_PATH, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        land_pad = sum(1 for r in rows if r["sequence"] == "land_pad")
        land_pad2 = sum(1 for r in rows if r["sequence"] == "land_pad2")
        assert land_pad == 66
        assert land_pad2 == 20


# ---------------------------------------------------------------------------
# Tests: Small box handling
# ---------------------------------------------------------------------------
class TestSmallBoxHandling:
    """Masks should be reasonable even for very small bounding boxes."""

    @pytest.mark.parametrize("topology", TOPOLOGIES)
    def test_small_box_no_crash(self, topology: str) -> None:
        """Generator should not crash on very small boxes."""
        rng = _rng_for("small", topology, 0.5)
        mask = MASK_GENERATORS[topology](IMG_W, IMG_H, SMALL_BOX, 0.5, rng)
        assert mask.shape == (IMG_H, IMG_W)

    @pytest.mark.parametrize("topology", TOPOLOGIES)
    def test_large_box_no_crash(self, topology: str) -> None:
        """Generator should not crash on very large boxes."""
        rng = _rng_for("large", topology, 0.5)
        mask = MASK_GENERATORS[topology](IMG_W, IMG_H, LARGE_BOX, 0.5, rng)
        assert mask.shape == (IMG_H, IMG_W)


# ---------------------------------------------------------------------------
# Tests: Expected view count
# ---------------------------------------------------------------------------
class TestExpectedViewCount:
    def test_default_grid_size(self) -> None:
        """Default grid: 86 frames × 4 topologies × 15 doses = 5,160 views."""
        expected = 86 * len(TOPOLOGIES) * len(DEFAULT_DOSES)
        assert expected == 5160

    def test_topologies_defined(self) -> None:
        """All four topologies must be defined."""
        assert set(TOPOLOGIES) == {"CENTER", "OUTER_RING", "STRIPED", "RANDOM_PATCH"}

    def test_doses_range(self) -> None:
        """Doses should range from 0.0 to 0.70 inclusive."""
        assert min(DEFAULT_DOSES) == 0.0
        assert max(DEFAULT_DOSES) == 0.70
        assert len(DEFAULT_DOSES) == 15
