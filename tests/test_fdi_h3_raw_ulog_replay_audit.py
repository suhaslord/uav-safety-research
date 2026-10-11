"""Synthetic-only regression checks for the independent H3 ULog replay."""
import copy
import unittest
from types import SimpleNamespace

from scripts.fdi_h3_raw_ulog_replay_audit import (
    FIELDS, GYRO, MOTORS, audit_replay,
)


def fixture():
    gyro_times = list(range(0, 2_400_000, 20_000))
    # Finish both recorded topics at the same observed timestamp, matching the\n    # exporter's strict intersection rather than inventing extra gyro rows.\n    motor_times = list(range(0, 2_400_000, 100_000)) + [gyro_times[-1]]
    g = {"timestamp": gyro_times}
    m = {"timestamp": motor_times}
    for i in range(3):
        g[f"xyz[{i}]"] = [0.05 + i * 0.03 + j * 1e-4 for j in range(len(gyro_times))]
    for i in range(4):
        m[f"control[{i}]"] = [i * 0.1 + j * 1e-4 for j in range(len(motor_times))]
    ulog = SimpleNamespace(data_list=[
        SimpleNamespace(name=GYRO, data=g),
        SimpleNamespace(name=MOTORS, data=m),
    ])
    rows = []
    for index, time in enumerate(gyro_times):
        motor_index = max(j for j, motor_time in enumerate(motor_times)
                          if motor_time <= time)
        command_time = motor_times[motor_index]
        values = [
            time, command_time, time - command_time,
            *(g[f"xyz[{i}]"][index] for i in range(3)),
            *(m[f"control[{i}]"][motor_index] for i in range(4)),
        ]
        rows.append(dict(zip(FIELDS, [str(value) for value in values])))
    metadata = {
        "study": "FDI-H3", "status": "DEVELOPMENT_ONLY_UNMAPPED",
        "input_sha256": "d" * 64, "sample_count": len(rows),
        "start_log_timestamp_us": gyro_times[0],
        "end_log_timestamp_us": gyro_times[-1],
        "max_command_age_limit_us": 100_000,
        "max_observed_command_age_us": 80_000,
        "can_claim_h3_results": False,
        "independent_dynamics_verified": False,
        "physical_motor_map_verified": False,
        "fault_injection_verified": False,
    }
    return ulog, rows, metadata


class H3RawUlogReplayTests(unittest.TestCase):
    def replay(self, mutator=None):
        ulog, rows, metadata = fixture()
        if mutator:
            mutator(ulog, rows, metadata)
        return audit_replay(ulog, rows, metadata, raw_sha256="d" * 64)

    def test_exactly_replayed_sensor_values_and_timestamps(self):
        r = self.replay()
        self.assertEqual(r["status"], "MATCHED_DEVELOPMENT_ONLY", r["errors"])
        self.assertEqual(r["rows_checked"], 120)
        self.assertEqual(r["max_observed_command_age_us"], 80000)
        self.assertFalse(r["can_claim_h3_results"])
        self.assertFalse(r["physical_motor_map_verified"])

    def test_rejects_altered_gyro_value(self):
        r = self.replay(lambda _u, rows, _m: rows[6].__setitem__(
            "gyro_xyz1_unmapped_radps", "123.456"))
        self.assertIn("gyro_xyz1_unmapped", " ".join(r["errors"]))

    def test_rejects_altered_motor_command(self):
        r = self.replay(lambda _u, rows, _m: rows[4].__setitem__(
            "commanded_actuator_2_unmapped", "-3.0"))
        self.assertIn("commanded_actuator_2_unmapped", " ".join(r["errors"]))

    def test_rejects_future_actuator_timestamp(self):
        r = self.replay(lambda _u, rows, _m: rows[0].__setitem__(
            "actuator_command_log_timestamp_us", "100000"))
        self.assertIn("actuator_command_log_timestamp_us", " ".join(r["errors"]))

    def test_rejects_missing_gyro_sample(self):
        r = self.replay(lambda _u, rows, _m: rows.pop(20))
        self.assertIn("row count", " ".join(r["errors"]))

    def test_rejects_raw_log_checksum_mismatch(self):
        r = self.replay(lambda _u, _r, m: m.__setitem__("input_sha256", "e" * 64))
        self.assertIn("checksum", " ".join(r["errors"]))

    def test_rejects_claiming_protected_h3_results(self):
        r = self.replay(lambda _u, _r, m: m.__setitem__("can_claim_h3_results", True))
        self.assertIn("explicitly keep can_claim_h3_results false", " ".join(r["errors"]))

    def test_rejects_nonfinite_raw_gyro_sample(self):
        def mutate(u, _r, _m):
            u.data_list[0].data["xyz[0]"][8] = float("nan")
        r = self.replay(mutate)
        self.assertIn("nonfinite", " ".join(r["errors"]))

    def test_rejects_ambiguous_actuator_topic(self):
        def mutate(u, _r, _m):
            u.data_list.append(copy.deepcopy(u.data_list[1]))
        r = self.replay(mutate)
        self.assertIn("exactly once", " ".join(r["errors"]))

    def test_rejects_inconsistent_command_age(self):
        r = self.replay(lambda _u, rows, _m: rows[7].__setitem__(
            "command_age_us", "99999"))
        self.assertIn("command_age_us", " ".join(r["errors"]))

    def test_rejects_nonmonotone_raw_timestamps(self):
        def mutate(u, _r, _m):
            u.data_list[1].data["timestamp"][5] = 200_000
        r = self.replay(mutate)
        self.assertIn("non-monotone", " ".join(r["errors"]))

    def test_rejects_mismatched_max_command_age(self):
        r = self.replay(lambda _u, _r, m: m.__setitem__("max_observed_command_age_us", 40))
        self.assertIn("maximum command age", " ".join(r["errors"]))


if __name__ == "__main__":
    unittest.main()
