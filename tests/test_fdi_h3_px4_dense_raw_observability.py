"""Synthetic-only tests; no PX4 executable or actual motor is run."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts.fdi_h3_px4_dense_logger_plan import plan_text, validate_plan, write_plan
from scripts.fdi_h3_px4_dense_raw_gate import check_density


def source_fixture(raw_count=1500, raw_step=20_000):
    processed = SimpleNamespace(name="vehicle_angular_velocity", data={
        "timestamp_sample": [i * 10_000 for i in range(3000)]
    })
    raw = SimpleNamespace(name="sensor_gyro", multi_id=0, data={
        "timestamp_sample": [i * raw_step for i in range(raw_count)],
        "timestamp": [i * raw_step + 100 for i in range(raw_count)],
        "x": [0.1] * raw_count, "y": [0.2] * raw_count,
        "z": [0.3] * raw_count, "device_id": [1310988] * raw_count
    })
    return SimpleNamespace(data_list=[processed, raw])


class LoggerPlanTests(unittest.TestCase):
    def test_plan_is_valid_and_keeps_all_h3_evidence_channels(self):
        self.assertEqual(validate_plan(plan_text()), [])
        for topic in ("sensor_gyro", "vehicle_angular_velocity", "actuator_motors",
                      "sensor_selection", "vehicle_local_position"):
            self.assertIn(topic + " ", plan_text())

    def test_plan_rejects_duplicate_topics(self):
        self.assertIn("duplicate", str(validate_plan(plan_text() + "sensor_gyro 10\n")))

    def test_plan_rejects_sparse_raw_rate(self):
        body = plan_text().replace("sensor_gyro 10\n", "sensor_gyro 1000\n")
        self.assertTrue(validate_plan(body))

    def test_plan_rejects_missing_command_channel(self):
        body = plan_text().replace("actuator_motors 20\n", "")
        self.assertTrue(validate_plan(body))

    def test_plan_writes_checksum_bound_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "logger_topics.txt"
            receipt_path = Path(tmp) / "logger_receipt.json"
            receipt = write_plan(config, receipt_path)
            self.assertEqual(receipt["status"], "FROZEN_DEVELOPMENT_LOGGER_PLAN")
            self.assertTrue(config.is_file())
            self.assertTrue(receipt_path.is_file())
            self.assertFalse(receipt["can_claim_h3_results"])


class DenseRawGateTests(unittest.TestCase):
    def test_sufficient_recorded_raw_data_passes_only_development_gate(self):
        result = check_density(source_fixture(), source_sha256="a" * 64)
        self.assertEqual(result["status"], "DENSE_RAW_GYRO_OBSERVED_DEVELOPMENT_ONLY")
        self.assertFalse(result["raw_sensor_identity_verified"])
        self.assertFalse(result["gyro_axis_parity_verified"])
        self.assertFalse(result["can_claim_h3_results"])

    def test_old_41_sample_logging_is_rejected(self):
        self.assertEqual(check_density(source_fixture(41, 1_000_000))["status"], "REJECTED")

    def test_large_interior_gap_rejected(self):
        log = source_fixture()
        raw = log.data_list[1].data
        raw["timestamp_sample"] = [i * 20_000 if i < 650 else (i * 20_000 + 1_000_000)
                                   for i in range(1500)]
        raw["timestamp"] = [t + 100 for t in raw["timestamp_sample"]]
        result = check_density(log)
        self.assertEqual(result["status"], "REJECTED")
        self.assertGreater(result["raw_instances"][0]["max_logged_raw_gap_us"], 250_000)

    def test_fraction_too_small_rejected(self):
        self.assertEqual(check_density(source_fixture(240, 20_000))["status"], "REJECTED")

    def test_raw_unordered_clock_rejected(self):
        log = source_fixture()
        log.data_list[1].data["timestamp_sample"][2] = 0
        self.assertEqual(check_density(log)["status"], "REJECTED")

    def test_absent_raw_topic_rejected(self):
        log = source_fixture()
        log.data_list.pop()
        self.assertEqual(check_density(log)["status"], "REJECTED")


if __name__ == "__main__":
    unittest.main()
