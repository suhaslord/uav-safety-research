import unittest
import numpy as np

from fault_indicator_metrics import (
    evaluate_indicator,
    event_window_false_alarm_rate,
    summarize,
)


class DetectionMetricTests(unittest.TestCase):
    def test_detection_latency_and_false_alarm(self):
        t = np.arange(0.0, 10.0, 1.0)
        signal = np.zeros_like(t)
        fault = (t >= 4.0) & (t <= 6.0)
        signal[5:7] = 10.0
        signal[1] = 10.0
        m = evaluate_indicator(t, signal, fault, threshold=5.0)
        self.assertTrue(m.detected)
        self.assertEqual(m.response_time_s, 1.0)
        self.assertEqual(m.false_alarm_count, 1)

    def test_persistence_filter_rejects_single_spike(self):
        t = np.arange(6.0)
        signal = np.array([0, 8, 0, 8, 8, 0], dtype=float)
        fault = np.array([False, False, False, True, True, False])
        m = evaluate_indicator(t, signal, fault, threshold=5.0, min_consecutive=2)
        self.assertTrue(m.detected)
        self.assertEqual(m.false_alarm_count, 0)

    def test_summary(self):
        t = np.arange(5.0)
        fault = np.array([False, True, True, False, False])
        a = evaluate_indicator(t, np.array([0, 0, 9, 0, 0]), fault, 5.0)
        b = evaluate_indicator(t, np.zeros(5), fault, 5.0)
        s = summarize([a, b])
        self.assertAlmostEqual(s["detection_rate"], 0.5)

    def test_turn_window_false_alarm_rate_excludes_fault(self):
        t = np.arange(0.0, 10.0, 1.0)
        signal = np.zeros_like(t)
        signal[2] = 9.0
        signal[5] = 9.0
        fault = (t >= 5.0) & (t <= 6.0)
        rate = event_window_false_alarm_rate(
            t,
            signal,
            threshold=5.0,
            event_times_s=np.array([2.0, 5.0]),
            window_s=0.0,
            exclude_mask=fault,
        )
        self.assertEqual(rate, 1.0)


if __name__ == "__main__":
    unittest.main()
