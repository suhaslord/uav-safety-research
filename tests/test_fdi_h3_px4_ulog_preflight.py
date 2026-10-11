"""Offline, synthetic PX4 H3 ULog interface checks; no drone operation."""
import unittest
from types import SimpleNamespace

from scripts.fdi_h3_px4_ulog_preflight import ACTUATOR_TOPIC, GYRO_TOPIC, audit_ulog


def fake_topic(name, n=200, offset=0, timestamp_override=None):
    stamps = list(range(offset, offset + n * 20000, 20000)) if timestamp_override is None else timestamp_override
    data = {"timestamp": stamps}
    if name == GYRO_TOPIC:
        data.update({
            "xyz[0]": [0.03] * n,
            "xyz[1]": [0.04] * n,
            "xyz[2]": [0.05] * n,
        })
    if name == ACTUATOR_TOPIC:
        data.update({f"control[{i}]": [0.25] * n for i in range(4)})
    return SimpleNamespace(name=name, multi_id=0, data=data)


def ulog(*datasets):
    return SimpleNamespace(data_list=list(datasets))


class H3PX4ULogPreflightTests(unittest.TestCase):
    def test_complete_signal_inventory_is_only_manual_review_ready(self):
        r = audit_ulog(ulog(fake_topic(GYRO_TOPIC), fake_topic(ACTUATOR_TOPIC)))
        self.assertEqual(r["errors"], [])
        self.assertEqual(r["status"], "READY_FOR_MANUAL_SIGNAL_MAPPING")
        self.assertAlmostEqual(r["gyro_actuator_time_overlap_s"], 3.98)
        self.assertFalse(r["can_claim_h3_results"])
        self.assertFalse(r["fault_injection_verified"])
        self.assertFalse(r["verified_independent_dynamics"])

    def test_missing_motor_topic_fails_without_making_up_signal(self):
        r = audit_ulog(ulog(fake_topic(GYRO_TOPIC)))
        self.assertEqual(r["status"], "INCOMPLETE_TELEMETRY")
        self.assertTrue(any(ACTUATOR_TOPIC in x for x in r["errors"]))

    def test_nonfinite_gyro_rejected(self):
        gyro = fake_topic(GYRO_TOPIC)
        gyro.data["xyz[1]"][11] = float("nan")
        r = audit_ulog(ulog(gyro, fake_topic(ACTUATOR_TOPIC)))
        self.assertTrue(any("nonfinite" in x for x in r["errors"]))

    def test_reordered_timestamp_rejected(self):
        gyro = fake_topic(GYRO_TOPIC)
        gyro.data["timestamp"][100] = gyro.data["timestamp"][99]
        r = audit_ulog(ulog(gyro, fake_topic(ACTUATOR_TOPIC)))
        self.assertTrue(any("nonmonotonic" in x for x in r["errors"]))

    def test_limited_time_overlap_rejected(self):
        motor = fake_topic(ACTUATOR_TOPIC, offset=3900000)
        r = audit_ulog(ulog(fake_topic(GYRO_TOPIC), motor))
        self.assertTrue(any("overlap" in x for x in r["errors"]))

    def test_duplicate_topic_is_ambiguous(self):
        r = audit_ulog(ulog(fake_topic(GYRO_TOPIC), fake_topic(GYRO_TOPIC),
                            fake_topic(ACTUATOR_TOPIC)))
        self.assertTrue(any("ambiguous" in x for x in r["errors"]))

    def test_missing_gyro_axis_is_not_filled_from_other_axis(self):
        gyro = fake_topic(GYRO_TOPIC)
        del gyro.data["xyz[1]"]
        r = audit_ulog(ulog(gyro, fake_topic(ACTUATOR_TOPIC)))
        self.assertTrue(any("xyz[1]" in x for x in r["errors"]))


if __name__ == "__main__":
    unittest.main()
