"""Unit checks for H2: frozen causal faults, censoring, cluster statistics."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate_fdi_h2 import (
    SEEDS, FAULT_LOSSES, ONSETS, path_name, gyro_decision, metric, cluster_bootstrap,
    PREMATURE_COLUMN,
)


def sample(t, p=0, q=0, z=1.0):
    return {"time_s": str(t), "gyro_p_rps": str(p),
            "gyro_q_rps": str(q), "z_m": str(z)}


class H2Tests(unittest.TestCase):
    def test_expected_filenames(self):
        names = {path_name(s, o, 0, 0) for s in SEEDS for o in ONSETS}
        names |= {path_name(s, o, loss, m) for s in SEEDS for o in ONSETS
                  for loss in FAULT_LOSSES for m in (1, 2, 3, 4)}
        self.assertEqual(len(names), 108)

    def test_quadrants_frozen_from_h1(self):
        patterns = {1: (3, 1.5), 2: (3, -1.5), 3: (-3, -1.5), 4: (-3, 1.5)}
        for motor, (p, q) in patterns.items():
            with self.subTest(motor=motor):
                data = [sample(8.01, p, q), sample(8.042, p, q), sample(8.074, p, q)]
                verdict = gyro_decision(data, 97, 8., .5, motor, 0.)
                self.assertEqual(verdict["scored_prediction"], motor)
                self.assertFalse(verdict["premature"])

    def test_pre_onset_alarms_do_not_get_credit(self):
        data = [sample(7.0, 3, 1), sample(7.032, 3, 1), sample(7.064, 3, 1)]
        verdict = gyro_decision(data, 97, 8., 1., 1, 0.)
        self.assertEqual(verdict["scored_prediction"], PREMATURE_COLUMN)
        self.assertTrue(verdict["premature"])

    def test_healthy_alarm_is_false_positive(self):
        data = [sample(7.0, 3, 1), sample(7.032, 3, 1), sample(7.064, 3, 1)]
        verdict = gyro_decision(data, 97, 8., 0., 0, 0.)
        self.assertEqual(verdict["scored_prediction"], 1)
        self.assertFalse(verdict["premature"])

    def test_censor_before_simulated_contact(self):
        data = [sample(8.01, 3, 1, .49)] * 5
        self.assertEqual(gyro_decision(data, 97, 8., 1., 1, 0.)["scored_prediction"], 0)

    def test_noisy_replay_deterministic(self):
        data = [sample(t * .032, 0, 0) for t in range(400)]
        a = gyro_decision(data, 97, 8., .5, 1, .5)
        b = gyro_decision(data, 97, 8., .5, 1, .5)
        self.assertEqual(a, b)

    def test_balanced_accuracy_and_seed_bootstrap(self):
        rows = [{"seed":s, "onset_s":o, "truth_motor":m,
                 "scored_prediction":m, "alert_time_s":o+.1 if m else None,
                 "premature":False} for s in SEEDS for o in ONSETS for m in range(5)]
        self.assertEqual(metric(rows)["balanced_accuracy"], 1.)
        self.assertEqual(cluster_bootstrap(rows)["percentile_95_interval"], [1., 1.])
        for row in rows: row["scored_prediction"] = 0
        self.assertAlmostEqual(metric(rows)["balanced_accuracy"], .2)
        self.assertEqual(cluster_bootstrap(rows)["percentile_95_interval"], [.2, .2])


if __name__ == "__main__":
    unittest.main()
