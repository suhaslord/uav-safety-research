"""Replay checks using synthetic ULog-shaped objects, no Gazebo or aircraft."""
import csv
import io
from types import SimpleNamespace
import unittest

from scripts.fdi_h3_px4_ulog_csv_replay import replay
from scripts.fdi_h3_px4_development_trace import FIELDS


def fixture():
    times = list(range(0, 1_000_000, 20_000))
    gyro = {"timestamp": times,
            **{f"xyz[{i}]": [float(i + n / 100) for n in range(len(times))]
               for i in range(3)}}
    motor = {"timestamp": times,
             **{f"control[{i}]": [float(i / 10 + n / 100)
                                  for n in range(len(times))]
                for i in range(4)}}
    ulog = SimpleNamespace(data_list=[
        SimpleNamespace(name="vehicle_angular_velocity", data=gyro),
        SimpleNamespace(name="actuator_motors", data=motor)])
    rows = []
    for n, stamp in enumerate(times):
        rows.append([stamp, stamp, 0] +
                    [gyro[f"xyz[{i}]"][n] for i in range(3)] +
                    [motor[f"control[{i}]"][n] for i in range(4)])
    return ulog, rows


def csv_rows(rows):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(FIELDS)
    writer.writerows(rows)
    return buf.getvalue()


class ReplayTests(unittest.TestCase):
    def test_exact_replay_matches(self):
        ulog, rows = fixture()
        result = replay(ulog, csv_rows(rows))
        self.assertEqual(result["status"], "ULOG_CSV_REPLAY_MATCH")
        self.assertEqual(result["rows_checked"], 50)
        self.assertFalse(result["can_claim_h3_results"])

    def test_modified_logged_gyro_fails(self):
        ulog, rows = fixture()
        rows[9][3] = 123.0
        self.assertIn("differs from ULog", str(replay(ulog, csv_rows(rows))["errors"]))

    def test_changed_actuator_channel_fails(self):
        ulog, rows = fixture()
        rows[3][8] = -0.5
        self.assertEqual(replay(ulog, csv_rows(rows))["status"], "REJECTED")

    def test_extra_row_is_rejected(self):
        ulog, rows = fixture()
        rows.append(rows[-1])
        self.assertIn("extra rows", str(replay(ulog, csv_rows(rows))["errors"]))

    def test_missing_rows_rejected(self):
        ulog, rows = fixture()
        rows.pop()
        self.assertEqual(replay(ulog, csv_rows(rows))["status"], "REJECTED")

    def test_future_timestamp_is_rejected(self):
        ulog, rows = fixture()
        rows[3][1] = 80000
        self.assertEqual(replay(ulog, csv_rows(rows))["status"], "REJECTED")

    def test_nonfinite_is_rejected(self):
        ulog, rows = fixture()
        rows[4][4] = "nan"
        self.assertEqual(replay(ulog, csv_rows(rows))["status"], "REJECTED")

    def test_ambiguous_topic_is_rejected(self):
        ulog, rows = fixture()
        ulog.data_list.append(ulog.data_list[0])
        self.assertEqual(replay(ulog, csv_rows(rows))["status"], "REJECTED")


if __name__ == "__main__":
    unittest.main()
