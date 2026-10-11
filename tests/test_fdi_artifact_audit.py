"""Purely synthetic regression checks for the independent FDI evidence auditor.

No protected artifact, simulator output or flight-safety data are loaded.
"""
import io
import json
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from scripts import audit_fdi_h1_artifact as audit


def row(t, p=0.0, q=0.0, altitude=1.0):
    return {"time_s": str(t), "gyro_p_rps": str(p),
            "gyro_q_rps": str(q), "z_m": str(altitude)}


class ArtifactAuditRegressionTests(unittest.TestCase):
    def test_all_four_motor_sign_quadrants(self):
        patterns = {1: (2.0, .75), 2: (2.0, -.75),
                    3: (-2.0, -.75), 4: (-2.0, .75)}
        for label, (p, q) in patterns.items():
            with self.subTest(motor=label):
                prediction, time, altitude = audit.decision([
                    row(10.02, p, q), row(10.052, p, q),
                    row(10.084, p, q)
                ])
                self.assertEqual(prediction, label)
                self.assertEqual(time, 10.084)
                self.assertEqual(altitude, 1.0)

    def test_nonconsecutive_exceedances_are_not_detected(self):
        samples = [row(10.02, 3, 1), row(10.052, 3, 1),
                   row(10.084), row(10.116, 3, 1),
                   row(10.148, 3, 1)]
        self.assertEqual(audit.decision(samples)[0], 0)

    def test_censor_time_and_contact(self):
        self.assertEqual(audit.decision([
            row(10.71 + .032 * i, 3, 1) for i in range(3)
        ])[0], 0)
        self.assertEqual(audit.decision([
            row(10.02, 3, 1, .49),
            row(10.052, 3, 1), row(10.084, 3, 1)
        ])[0], 0)

    def test_healthy_gyro_excursion_can_false_alarm(self):
        # Limitation of the rule, not a measured flight outcome.
        self.assertEqual(audit.decision([
            row(9.0, 3, 1), row(9.032, 3, 1),
            row(9.064, 3, 1)
        ])[0], 1)

    def test_partial_zip_rejected_before_replay(self):
        # An archive with no manifest is never a valid 70-trace result.
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "partial.zip"
            with zipfile.ZipFile(path, "w") as z:
                z.writestr("report/heldout_results.json",
                           json.dumps({"input_manifest": [],
                                       "protected_test_seeds": list(audit.PROTECTED)}))
                z.writestr("report/trajectory_decisions.csv",
                           "seed,motor,prediction\n")
            with patch.object(sys, "argv", ["audit", str(path)]):
                with redirect_stdout(io.StringIO()):
                    with self.assertRaises((AssertionError, ValueError)):
                        audit.main()

    def test_expected_seed_split_exact(self):
        self.assertEqual(len(audit.SEEDS), 14)
        self.assertEqual(len(set(audit.SEEDS)), 14)
        self.assertTrue(set(audit.PROTECTED).isdisjoint(set(audit.SOURCE + audit.DEVELOPMENT)))


if __name__ == "__main__":
    unittest.main()
