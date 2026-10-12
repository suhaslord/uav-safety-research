"""Read-only synthetic tests for H3 sample vs publication time integrity."""
import unittest
from types import SimpleNamespace

from scripts.fdi_h3_px4_sample_clock_audit import inspect


def example():
    gyro = {
        "timestamp": [1200, 2200, 3200, 4200],
        "timestamp_sample": [1000, 2000, 3000, 4000],
    }
    actuator = {"timestamp": [900, 1900, 2900, 3900]}
    return SimpleNamespace(data_list=[
        SimpleNamespace(name="vehicle_angular_velocity", data=gyro),
        SimpleNamespace(name="actuator_motors", data=actuator),
    ])


class SampleClockTests(unittest.TestCase):
    def test_observed_sample_clock_stays_unscored(self):
        result = inspect(example(), source_sha256="a" * 64)
        self.assertEqual(result["status"], "SAMPLE_CLOCK_OBSERVED_DEVELOPMENT_ONLY")
        self.assertEqual(result["gyro_rows"], 4)
        self.assertEqual(result["sample_publish_delay_us"]["maximum"], 200)
        self.assertEqual(result["sample_publish_delay_us"]["distinct_sample_publication_rows"], 4)
        self.assertEqual(result["causal_command_at_gyro_sample"]["age_median_us"], 100)
        self.assertEqual(result["raw_ulog_sha256"], "a" * 64)
        self.assertFalse(result["can_claim_h3_results"])
        self.assertFalse(result["gyro_axis_parity_verified"])
        self.assertFalse(result["cross_topic_clock_sync_verified"])
        self.assertFalse(result["applied_actuation_verified"])

    def test_identical_sample_and_publish_clock_is_explicitly_unverified(self):
        log = example()
        log.data_list[0].data["timestamp_sample"] = list(
            log.data_list[0].data["timestamp"]
        )
        report = inspect(log)
        self.assertEqual(report["sample_publish_delay_us"]["identical_sample_publication_rows"], 4)
        self.assertEqual(report["sample_publish_delay_us"]["distinct_sample_publication_rows"], 0)
        self.assertIn("not independent evidence", report["clock_interpretation"])
        self.assertFalse(report["cross_topic_clock_sync_verified"])

    def test_future_sample_timestamp_rejected(self):
        log = example()
        log.data_list[0].data["timestamp_sample"][1] = 2500
        self.assertEqual(inspect(log)["status"], "REJECTED")

    def test_missing_sample_timestamp_rejected(self):
        log = example()
        del log.data_list[0].data["timestamp_sample"]
        self.assertIn("missing timestamp_sample", inspect(log)["errors"])

    def test_out_of_order_gyro_sample_timestamps_rejected(self):
        log = example()
        log.data_list[0].data["timestamp_sample"][2] = 2000
        self.assertEqual(inspect(log)["status"], "REJECTED")

    def test_bad_timestamp_type_rejected(self):
        log = example()
        log.data_list[0].data["timestamp_sample"][0] = "1000"
        self.assertIn("noninteger", str(inspect(log)["errors"]))

    def test_boolean_gyro_sample_timestamp_rejected(self):
        log = example()
        log.data_list[0].data["timestamp_sample"][0] = True
        result = inspect(log)
        self.assertEqual(result["status"], "REJECTED")
        self.assertIn("noninteger timestamp_sample", result["errors"])

    def test_boolean_actuator_timestamp_rejected(self):
        log = example()
        log.data_list[1].data["timestamp"][0] = False
        result = inspect(log)
        self.assertEqual(result["status"], "REJECTED")
        self.assertIn("noninteger timestamp", result["errors"])

    def test_boolean_publication_timestamp_rejected(self):
        log = example()
        log.data_list[0].data["timestamp"][0] = True
        self.assertEqual(inspect(log)["status"], "REJECTED")

    def test_duplicate_actuator_topic_rejected(self):
        log = example()
        log.data_list.append(log.data_list[1])
        self.assertIn("ambiguous", str(inspect(log)["errors"]))

    def test_no_preceding_actuator_command_rejected(self):
        log = example()
        log.data_list[1].data["timestamp"] = [4500, 5500, 6500, 7500]
        self.assertIn("no causally preceding", str(inspect(log)["errors"]))

    def test_future_commands_never_borrowed(self):
        log = example()
        log.data_list[1].data["timestamp"] = [1500, 2500, 3500, 4500]
        result = inspect(log)
        self.assertEqual(result["status"], "SAMPLE_CLOCK_OBSERVED_DEVELOPMENT_ONLY")
        self.assertEqual(result["causal_command_at_gyro_sample"]["samples_without_prior_command"], 1)
        self.assertEqual(result["causal_command_at_gyro_sample"]["samples_with_prior_command"], 3)
        self.assertEqual(result["causal_command_at_gyro_sample"]["age_median_us"], 500)

    def test_lagging_commands_report_staleness_not_accuracy(self):
        log = example()
        log.data_list[0].data["timestamp"] = [101200, 202200, 303200, 404200]
        log.data_list[0].data["timestamp_sample"] = [101000, 202000, 303000, 404000]
        log.data_list[1].data["timestamp"] = [0, 1, 2, 3]
        result = inspect(log)
        self.assertEqual(result["causal_command_at_gyro_sample"]["stale_over_100ms"], 4)
        self.assertFalse(result["fault_injection_verified"])

    def test_mismatched_sample_array_rejected(self):
        log = example()
        log.data_list[0].data["timestamp_sample"].pop()
        self.assertIn("different lengths", str(inspect(log)["errors"]))


if __name__ == "__main__":
    unittest.main()
