"""Purely synthetic regression checks for the independent FDI evidence auditor.

No protected artifact, simulator output or flight-safety data are loaded.
"""
import hashlib
import io
import json
import subprocess
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

    def test_optimized_python_cannot_skip_audit_assertions(self):
        # Python -O removes assert statements. The auditor must fail
        # explicitly instead of printing an unverified success report.
        completed = subprocess.run(
            [sys.executable, "-O", str(Path(audit.__file__)), "invalid.zip"],
            capture_output=True, text=True, check=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("assertions enabled", completed.stderr)

    def test_evaluator_source_checksum_matches_supplied_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "frozen-evaluator.py"
            source.write_bytes(b"# synthetic frozen code\\n")
            report = {"analysis_script_sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
            self.assertTrue(audit.verify_evaluator_source(report, source))
            source.write_bytes(b"# changed after freeze\\n")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                audit.verify_evaluator_source(report, source)

    def test_nonfinite_numeric_telemetry_is_rejected_for_each_field(self):
        clean = {key: "0.0" for key in audit.NUMERIC_TELEMETRY_FIELDS}
        audit.validate_numeric_telemetry(clean, "synthetic.csv")
        for key in audit.NUMERIC_TELEMETRY_FIELDS:
            with self.subTest(field=key):
                poisoned = dict(clean)
                poisoned[key] = "nan"
                with self.assertRaisesRegex(ValueError, key):
                    audit.validate_numeric_telemetry(poisoned, "synthetic.csv")
        incomplete = dict(clean)
        del incomplete["cmd_m4"]
        with self.assertRaisesRegex(ValueError, "cmd_m4"):
            audit.validate_numeric_telemetry(incomplete, "synthetic.csv")

    def test_external_archive_fingerprint_detects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.zip"
            path.write_bytes(b"synthetic archive placeholder")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertTrue(audit.verify_expected_archive_sha256(path, digest))
            path.write_bytes(path.read_bytes() + b"modified")
            with self.assertRaisesRegex(ValueError, "differs"):
                audit.verify_expected_archive_sha256(path, digest)
            with self.assertRaisesRegex(ValueError, "64 hexadecimal"):
                audit.verify_expected_archive_sha256(path, "invalid")

    def test_exact_historical_trace_row_contract(self):
        self.assertEqual(audit.EXPECTED_ROWS_PER_TRACE, 750)
        audit.validate_trace_length(750, 750, "synthetic.csv")
        for actual, manifest in ((749, 749), (751, 751), (750, 749), (749, 750)):
            with self.subTest(actual=actual, manifest=manifest):
                with self.assertRaisesRegex(ValueError, "Unexpected trace length"):
                    audit.validate_trace_length(actual, manifest, "synthetic.csv")

    def test_frozen_webots_container_digest_is_exact(self):
        self.assertTrue(audit.validate_container_provenance([audit.PINNED_WEBOTS_DIGEST]))
        for bad in (
            [],
            None,
            ["cyberbotics/webots@sha256:" + "f" * 64],
            ["cyberbotics/webots:R2025a-ubuntu22.04"],
        ):
            with self.subTest(digests=bad):
                with self.assertRaisesRegex(ValueError, "does not match"):
                    audit.validate_container_provenance(bad)

    def test_expected_seed_split_exact(self):
        self.assertEqual(len(audit.SEEDS), 14)
        self.assertEqual(len(set(audit.SEEDS)), 14)
        self.assertTrue(set(audit.PROTECTED).isdisjoint(set(audit.SOURCE + audit.DEVELOPMENT)))


if __name__ == "__main__":
    unittest.main()
