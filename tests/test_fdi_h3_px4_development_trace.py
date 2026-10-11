"""Synthetic-only tests of PX4 development trace alignment (no simulator)."""
import unittest
from types import SimpleNamespace

from scripts.fdi_h3_px4_development_trace import make_development_trace
from scripts.fdi_h3_px4_ulog_preflight import ACTUATOR_TOPIC, GYRO_TOPIC


def fake_topic(name, timestamps=None):
    times = list(range(0, 4_000_000, 20_000)) if timestamps is None else timestamps
    n = len(times)
    data = {"timestamp": times}
    if name == GYRO_TOPIC:
        data.update({f"xyz[{i}]": [0.03 + i * 0.01] * n for i in range(3)})
    else:
        data.update({f"control[{i}]": [i / 10.0] * n for i in range(4)})
    return SimpleNamespace(name=name, multi_id=0, data=data)


def fake_ulog(gyro=None, motors=None):
    return SimpleNamespace(data_list=[
        gyro if gyro is not None else fake_topic(GYRO_TOPIC),
        motors if motors is not None else fake_topic(ACTUATOR_TOPIC),
    ])


class H3DevelopmentTraceTests(unittest.TestCase):
    def test_exactly_aligned_sample_stream_stays_unscored(self):
        rows, meta = make_development_trace(fake_ulog(), input_sha256="a" * 64)
        self.assertEqual(len(rows), 200)
        self.assertEqual(rows[75]["command_age_us"], 0)
        self.assertEqual(rows[75]["gyro_log_timestamp_us"], 1_500_000)
        self.assertEqual(rows[75]["actuator_command_log_timestamp_us"], 1_500_000)
        self.assertEqual(meta["input_sha256"], "a" * 64)
        self.assertEqual(meta["status"], "DEVELOPMENT_ONLY_UNMAPPED")
        self.assertFalse(meta["can_claim_h3_results"])
        self.assertFalse(meta["fault_injection_verified"])
        self.assertFalse(meta["physical_motor_map_verified"])
        self.assertNotIn("predictions", meta)
        self.assertNotIn("motor_id", rows[0])

    def test_later_command_never_borrowed_before_its_timestamp(self):
        motors = fake_topic(
            ACTUATOR_TOPIC, timestamps=list(range(20_000, 4_020_000, 20_000))
        )
        rows, _ = make_development_trace(fake_ulog(motors=motors))
        self.assertEqual(rows[0]["gyro_log_timestamp_us"], 20_000)
        self.assertEqual(rows[0]["actuator_command_log_timestamp_us"], 20_000)
        self.assertTrue(
            all(r["actuator_command_log_timestamp_us"] <= r["gyro_log_timestamp_us"]
                for r in rows)
        )

    def test_stale_command_refused_even_if_broad_preflight_passes(self):
        motor = fake_topic(ACTUATOR_TOPIC)
        motor.data["timestamp"] = [
            stamp + (120_000 if index >= 75 else 0)
            for index, stamp in enumerate(motor.data["timestamp"])
        ]
        with self.assertRaisesRegex(ValueError, "stale"):
            make_development_trace(fake_ulog(motors=motor))

    def test_missing_required_gyro_channel_is_rejected(self):
        gyro = fake_topic(GYRO_TOPIC)
        del gyro.data["xyz[1]"]
        with self.assertRaisesRegex(ValueError, "preflight rejected"):
            make_development_trace(fake_ulog(gyro=gyro))

    def test_nonfinite_actuator_data_does_not_enter_trace(self):
        motor = fake_topic(ACTUATOR_TOPIC)
        motor.data["control[2]"][14] = float("nan")
        with self.assertRaisesRegex(ValueError, "preflight rejected"):
            make_development_trace(fake_ulog(motors=motor))


if __name__ == "__main__":
    unittest.main()
