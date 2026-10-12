"""Read-only H3 PX4 development evidence audit regression checks."""
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from scripts.fdi_h3_development_bundle_audit import CSV_FIELDS, audit_bundle


class BundleAuditTests(unittest.TestCase):
    def setUp(self):
        import hashlib
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.bundle = Path(self.tmp.name) / "sample.zip"
        self.raw = b"synthetic ULog placeholder only, not flight evidence"
        digest = hashlib.sha256(self.raw).hexdigest()
        self.preflight = {
            "study": "FDI-H3", "input_sha256": digest,
            "status": "READY_FOR_MANUAL_SIGNAL_MAPPING", "errors": [],
            "can_claim_h3_results": False, "fault_injection_verified": False,
            "topics": {"vehicle_angular_velocity": {"overlap_samples": 2}},
        }
        self.metadata = {
            "study": "FDI-H3", "input_sha256": digest,
            "status": "DEVELOPMENT_ONLY_UNMAPPED",
            "can_claim_h3_results": False, "fault_injection_verified": False,
            "independent_dynamics_verified": False, "physical_motor_map_verified": False,
            "preflight": self.preflight, "sample_count": 2,
            "start_log_timestamp_us": 1000000, "end_log_timestamp_us": 1020000,
            "max_observed_command_age_us": 20000, "max_command_age_limit_us": 100000,
        }
        self.mission = {"completed": True, "segments": [{"name": "synthetic"}]}
        self.receipt = {
            "study": "FDI-H3", "status": "DEVELOPMENT_EXPORT_CREATED",
            "raw_ulog_sha256": digest, "mission_metadata": self.mission,
            "preflight": self.preflight, "unmapped_trace_metadata": self.metadata,
            "px4_source_id": "PX4-PX4_AUTOPILOT_SHA=fixture",
            "can_claim_h3_results": False, "fault_injection_verified": False,
            "independent_dynamics_verified": False, "physical_motor_map_verified": False,
        }
        self.source_audit = None
        self.rows = [
            ["1000000", "1000000", "0", "0.1", "0.2", "0.3", "0.4", "0.5", "0.6", "0.7"],
            ["1020000", "1000000", "20000", "0.1", "0.2", "0.3", "0.4", "0.5", "0.6", "0.7"],
        ]

    def write_bundle(self):
        stream = io.StringIO()
        writer = csv.writer(stream)
        writer.writerow(CSV_FIELDS)
        writer.writerows(self.rows)
        parts = {
            "development_receipt.json": json.dumps(self.receipt),
            "mission_metadata.json": json.dumps(self.mission),
            "px4_h3_preflight.json": json.dumps(self.preflight),
            "px4_h3_unmapped_metadata.json": json.dumps(self.metadata),
            "px4_h3_unmapped.csv": stream.getvalue(),
            "px4_gazebo_raw.ulg": self.raw,
            "px4_source.env": "PX4-PX4_AUTOPILOT_SHA=fixture",
        }
        if self.source_audit is not None:
            parts["source_motor_map_audit.json"] = json.dumps(self.source_audit)
        with ZipFile(self.bundle, "w", compression=ZIP_DEFLATED) as archive:
            for name, contents in parts.items():
                archive.writestr(name, contents)
        return audit_bundle(self.bundle)

    def static_source_audit(self):
        return {
            "status": "STATIC_SOURCE_MAP_VERIFIED", "errors": [],
            "can_claim_h3_results": False,
            "physical_motor_map_verified": False,
            "applied_actuation_verified": False,
            "fault_injection_verified": False,
        }

    def test_archived_source_map_matches_receipt(self):
        self.source_audit = self.static_source_audit()
        self.receipt["source_motor_map_audit"] = self.source_audit.copy()
        self.assertEqual(self.write_bundle()["status"], "CONSISTENT_DEVELOPMENT_ONLY")

    def test_changed_source_map_report_rejected(self):
        self.source_audit = self.static_source_audit()
        self.receipt["source_motor_map_audit"] = self.source_audit.copy()
        self.source_audit["status"] = "REJECTED"
        report = self.write_bundle()
        self.assertEqual(report["status"], "REJECTED")
        self.assertIn("source motor map", " ".join(report["errors"]))

    def test_missing_archived_source_map_rejected(self):
        self.receipt["source_motor_map_audit"] = self.static_source_audit()
        self.assertIn("missing archived source audit", " ".join(self.write_bundle()["errors"]))

    def test_source_map_cannot_claim_applied_actuation(self):
        self.source_audit = self.static_source_audit()
        self.source_audit["applied_actuation_verified"] = True
        self.receipt["source_motor_map_audit"] = self.source_audit.copy()
        self.assertIn("must explicitly refuse applied_actuation_verified",
                      " ".join(self.write_bundle()["errors"]))

    def test_valid_fixture_is_consistent_but_not_h3_accuracy(self):
        result = self.write_bundle()
        self.assertEqual(result["status"], "CONSISTENT_DEVELOPMENT_ONLY")
        self.assertFalse(result["can_claim_h3_results"])
        self.assertEqual(result["rows_checked"], 2)

    def test_modified_raw_ulog_fails_checksum(self):
        self.raw += b"changed"
        self.assertIn("raw ULog checksum", " ".join(self.write_bundle()["errors"]))

    def test_future_command_is_rejected(self):
        self.rows[0][1] = "1000001"
        self.assertIn("future, stale", " ".join(self.write_bundle()["errors"]))

    def test_stale_command_is_rejected(self):
        self.rows[1][1], self.rows[1][2] = "900000", "120000"
        self.assertIn("future, stale", " ".join(self.write_bundle()["errors"]))

    def test_fake_h3_results_are_rejected(self):
        self.receipt["can_claim_h3_results"] = True
        self.assertIn("refuse can_claim_h3_results", " ".join(self.write_bundle()["errors"]))

    def test_missing_mission_is_rejected(self):
        self.mission["completed"] = False
        self.assertIn("mission was not completed", " ".join(self.write_bundle()["errors"]))

    def test_nonfinite_gyro_is_rejected(self):
        self.rows[1][3] = "nan"
        self.assertIn("nonfinite", " ".join(self.write_bundle()["errors"]))

    def test_mismatched_sample_count_is_rejected(self):
        self.metadata["sample_count"] = 12
        self.assertIn("row count", " ".join(self.write_bundle()["errors"]))


if __name__ == "__main__":
    unittest.main()
