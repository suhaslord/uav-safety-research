"""Regression tests for the unexecuted FDI-R1 experimental design.

These tests use no protected CSVs, do not run Webots, and do not tune the
frozen FDI-H1 motor-fault rule.
"""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fdi_robustness_plan as plan


class R1DesignTests(unittest.TestCase):
    def test_command_seeds_are_new_and_prespecified(self):
        self.assertEqual(plan.NEW_SEEDS, (89, 97, 101, 103, 107, 109, 113, 127))
        self.assertTrue(set(plan.NEW_SEEDS).isdisjoint(plan.HISTORICAL_SEEDS))

    def test_every_seed_has_nine_paired_scenarios(self):
        cases = plan.planned_scenarios()
        self.assertEqual(len(cases), 72)
        self.assertEqual(Counter(r["command_seed"] for r in cases),
                         dict.fromkeys(plan.NEW_SEEDS, 9))
        self.assertEqual(Counter(r["condition"] for r in cases),
                         {"healthy": 8, "full_loss": 32, "partial_50pct": 32})
        self.assertTrue(plan.validate_scenarios(cases))

    def test_changed_fault_severity_or_onset_is_rejected(self):
        for field, value in [
            ("retained_motor_fraction", .25),
            ("failed_motor", 0),
            ("command_seed", 53),
            ("fault_onset_s", 10.5),
            ("gyro_noise_std_rad_per_s", .05),
            ("case_id", "changed"),
        ]:
            with self.subTest(field=field):
                cases = copy.deepcopy(plan.planned_scenarios())
                cases[1][field] = value
                with self.assertRaises(ValueError):
                    plan.validate_scenarios(cases)

    def test_duplicate_scenario_is_rejected(self):
        cases = plan.planned_scenarios()
        cases[-1] = dict(cases[0])
        with self.assertRaises(ValueError):
            plan.validate_scenarios(cases)

    def test_manifest_is_marked_unexecuted_with_frozen_source_hash(self):
        manifest = plan.make_manifest()
        self.assertIn("unexecuted", manifest["status"])
        self.assertEqual(manifest["command_seed_clusters"], 8)
        evaluator = Path(plan.__file__).with_name("evaluate_fdi_early.py")
        self.assertEqual(manifest["frozen_early_detector_source_sha256"],
                         hashlib.sha256(evaluator.read_bytes()).hexdigest())

    def test_manifest_is_byte_reproducible_and_not_overwritten(self):
        script = Path(plan.__file__)
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "plan_one.json"
            second = Path(directory) / "plan_two.json"
            def invoke(path):
                return subprocess.run(
                    [sys.executable, str(script), "--output", str(path)],
                    capture_output=True, text=True, check=False,
                )
            self.assertEqual(invoke(first).returncode, 0)
            self.assertEqual(invoke(second).returncode, 0)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(len(json.loads(first.read_text())["planned_cases"]), 72)
            self.assertNotEqual(invoke(first).returncode, 0)
            self.assertEqual(first.read_bytes(), second.read_bytes())


if __name__ == "__main__":
    unittest.main()
