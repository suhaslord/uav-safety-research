"""End-to-end negative-outcome ZIP audit using *generated synthetic data only*.

No protected historical traces are read or represented as real simulation data.
This catches accidental hardcoding of the archived 100% result.
"""
import csv
from copy import deepcopy
import hashlib
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
from test_fdi_h1_audit_metrics import synthetic_report


class SyntheticZipAuditTests(unittest.TestCase):
    def test_valid_complete_synthetic_archive_with_zero_fault_detections(self):
        # All forty protected trajectories predict healthy: deliberately
        # unsuccessful on every motor fault, yet a VALID negative result.
        report = synthetic_report(always_healthy=True)
        development = deepcopy(report["protected_result"])
        development["trajectories"] = 30
        development["confusion_matrix_rows_true_cols_predicted"] = [
            [6 if col == 0 else 0 for col in range(5)] for _ in range(5)
        ]
        report["development_descriptive_result"] = development
        report.update({
            "git_sha": "a" * 40,
            "protected_test_trajectories": 40,
            "protected_test_seeds": list(audit.PROTECTED),
            "source_development_seeds": list(audit.SOURCE),
            "development_seeds": list(audit.DEVELOPMENT),
            "input_manifest": [],
            "predefined_rule": {
                "p_abs_threshold_rad_per_s": 2.0,
                "q_abs_threshold_rad_per_s": 0.75,
                "consecutive_alert_samples": 3,
                "fault_onset_s": 10.0,
                "time_censor_s": 10.70,
                "altitude_censor_m": 0.50,
                "first_alarm_wins": True,
            },
        })
        fields = ["time_s", "x_m", "y_m", "z_m", "gyro_p_rps", "gyro_q_rps",
                  "gyro_r_rps", "cmd_m1", "cmd_m2", "cmd_m3", "cmd_m4",
                  "failed_motor", "fault_active", "seed"]
        decision_stream = io.StringIO()
        decision_writer = csv.DictWriter(
            decision_stream, fieldnames=[
                "split", "seed", "motor", "prediction", "alert_time_s",
                "alert_altitude_m", "false_alert_before_onset"])
        decision_writer.writeheader()
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "negative-synthetic.zip"
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
                for seed in audit.SEEDS:
                    split = ("protected_test" if seed in audit.PROTECTED else
                             "development" if seed in audit.DEVELOPMENT else
                             "source_development")
                    for motor in range(5):
                        name = f"seed{seed}_motor{motor}.csv"
                        stream = io.StringIO()
                        writer = csv.DictWriter(stream, fieldnames=fields)
                        writer.writeheader()
                        for index in range(1, 751):
                            t = index * .032
                            writer.writerow({
                                "time_s": f"{t:.6f}", "x_m": "0", "y_m": "0",
                                "z_m": "1", "gyro_p_rps": "0", "gyro_q_rps": "0",
                                "gyro_r_rps": "0", "cmd_m1": "0", "cmd_m2": "0",
                                "cmd_m3": "0", "cmd_m4": "0", "failed_motor": motor,
                                "fault_active": int(motor > 0 and t >= 10),
                                "seed": seed,
                            })
                        content = stream.getvalue().encode()
                        z.writestr("raw/" + name, content)
                        report["input_manifest"].append({
                            "file": name, "rows": 750,
                            "sha256": hashlib.sha256(content).hexdigest(),
                            "split": split,
                        })
                        decision_writer.writerow({
                            "split": split, "seed": seed, "motor": motor,
                            "prediction": 0, "alert_time_s": "",
                            "alert_altitude_m": "",
                            "false_alert_before_onset": False,
                        })
                z.writestr("report/trajectory_decisions.csv", decision_stream.getvalue())
                z.writestr("report/heldout_results.json", json.dumps(report))
                z.writestr("git_sha.txt", "a" * 40 + "\n")
                z.writestr("docker_image_digest.json",
                           json.dumps([audit.PINNED_WEBOTS_DIGEST]))
            output = io.StringIO()
            with patch.object(sys, "argv", ["audit", str(archive)]), redirect_stdout(output):
                audit.main()
            results = json.loads(output.getvalue())
        self.assertEqual(results["files_checked"], 70)
        self.assertEqual(results["descriptive_development_trajectories"], 30)
        self.assertEqual(results["balanced_accuracy"], .2)
        self.assertEqual(results["correct_fault_isolations"], 0)
        self.assertIsNone(results["median_correct_fault_detection_latency_seconds"])
        self.assertIsNone(results["detection_altitude_range_m"])


if __name__ == "__main__":
    unittest.main()
