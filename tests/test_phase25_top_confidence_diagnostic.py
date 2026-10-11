"""Isolated tests for the retrospective top-confidence Phase 25 audit."""
import tempfile
import unittest
from pathlib import Path

from scripts.diagnose_phase25_top_confidence import box, iou, update_top, diagnostics


class Phase25TopPredictionAuditTests(unittest.TestCase):
    def test_top_box_can_be_wrong_when_another_box_is_correct(self):
        gt = (0.10, 0.10, 0.30, 0.30)
        correct = {"index": 1, "confidence": 0.31, "box": gt}
        wrong = {"index": 0, "confidence": 0.92, "box": (0.60, 0.60, 0.90, 0.90)}
        selected = update_top(update_top(None, correct), wrong)
        self.assertEqual(selected["index"], 0)
        self.assertEqual(iou(selected["box"], gt), 0.0)
        self.assertEqual(iou(correct["box"], gt), 1.0)

    def test_equal_confidence_uses_original_prediction_index(self):
        a = {"index": 8, "confidence": 0.8, "box": (0.0, 0.0, 0.1, 0.1)}
        b = {"index": 2, "confidence": 0.8, "box": (0.3, 0.3, 0.4, 0.4)}
        self.assertEqual(update_top(a, b), b)
        self.assertEqual(update_top(b, a), b)

    def test_zero_area_clipped_prediction_is_incorrect_not_exception(self):
        degeneracy = {"x0": "0.0", "y0": "0.25", "x1": "0.0", "y1": "0.5"}
        candidate = box(degeneracy, allow_degenerate=True)
        self.assertEqual(iou(candidate, (0.1, 0.1, 0.5, 0.5)), 0.0)
        with self.assertRaises(ValueError):
            box(degeneracy)

    def test_inverted_prediction_and_out_of_range_rejected(self):
        for values in ({"x0":"0.6","y0":"0.1","x1":"0.2","y1":"0.5"},
                       {"x0":"-0.1","y0":"0.1","x1":"0.2","y1":"0.5"}):
            with self.assertRaises(ValueError):
                box(values, allow_degenerate=True)

    def test_missing_authenticated_manifest_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(FileNotFoundError):
                diagnostics(Path(root))


if __name__ == "__main__":
    unittest.main()
