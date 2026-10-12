"""Test that H3 raw-gyro inventory never infers sensor or axis parity."""
import unittest
from types import SimpleNamespace

from scripts.fdi_h3_px4_raw_gyro_inventory import inventory


def sample():
    processed = SimpleNamespace(
        name="vehicle_angular_velocity",
        multi_id=0,
        data={"timestamp_sample": [1000, 2000, 3000]},
    )
    raw = SimpleNamespace(
        name="sensor_gyro",
        multi_id=2,
        data={
            "timestamp": [900, 1900, 2900],
            "timestamp_sample": [800, 1800, 2800],
            "device_id": [4, 4, 4],
            "x": [0.1, 0.2, 0.3],
            "y": [0.3, 0.2, 0.1],
            "z": [0.0, 0.0, 0.0],
        },
    )
    return SimpleNamespace(data_list=[processed, raw])


class RawGyroInventoryTests(unittest.TestCase):
    def test_raw_gyro_present_but_parity_unverified(self):
        report = inventory(sample(), source_sha256="a" * 64)
        self.assertEqual(report["status"], "RAW_GYRO_RECORDED_UNMAPPED")
        self.assertEqual(report["raw_gyro"][0]["ulog_instance"], 2)
        self.assertEqual(report["raw_gyro"][0]["max_raw_to_processed_sample_timestamp_gap_us"], 200)
        self.assertEqual(report["raw_gyro"][0]["device_ids_observed"], [4])
        self.assertFalse(report["raw_sensor_identity_verified"])
        self.assertFalse(report["gyro_axis_parity_verified"])
        self.assertFalse(report["can_claim_h3_results"])

    def test_missing_raw_gyro_is_explicit_blocker_not_successful_parity(self):
        log = sample()
        log.data_list.pop()
        result = inventory(log)
        self.assertEqual(result["status"], "RAW_GYRO_NOT_RECORDED")
        self.assertFalse(result["raw_sensor_identity_verified"])

    def test_multiple_raw_instances_are_not_silently_collapsed(self):
        log = sample()
        other = SimpleNamespace(name="sensor_gyro", multi_id=3, data=log.data_list[1].data)
        log.data_list.append(other)
        result = inventory(log)
        self.assertEqual(len(result["raw_gyro"]), 2)
        self.assertFalse(result["raw_sensor_identity_verified"])

    def test_bad_raw_timestamp_order_fails(self):
        log = sample()
        log.data_list[1].data["timestamp_sample"][2] = 700
        self.assertEqual(inventory(log)["status"], "REJECTED")

    def test_future_raw_sample_relative_to_publication_fails(self):
        log = sample()
        log.data_list[1].data["timestamp_sample"][0] = 1000
        self.assertIn("after publication", str(inventory(log)["errors"]))

    def test_nonfinite_raw_axis_fails(self):
        log = sample()
        log.data_list[1].data["x"][0] = float("nan")
        self.assertEqual(inventory(log)["status"], "REJECTED")

    def test_missing_processed_gyro_topic_fails(self):
        log = sample()
        log.data_list.pop(0)
        self.assertIn("processed", str(inventory(log)["errors"]))

    def test_raw_stream_can_begin_after_processed_without_future_borrowing(self):
        log = sample()
        log.data_list[1].data["timestamp_sample"] = [2200, 2400, 2600]
        log.data_list[1].data["timestamp"] = [2300, 2500, 2700]
        result = inventory(log)
        self.assertEqual(result["status"], "RAW_GYRO_RECORDED_UNMAPPED")
        self.assertEqual(result["raw_gyro"][0]["processed_samples_with_preceding_raw_sample"], 1)


if __name__ == "__main__":
    unittest.main()
