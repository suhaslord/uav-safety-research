"""Non-simulator robustness checks for the frozen early FDI detector.

These tests introduce controlled perturbations to *synthetic* gyroscope
sequences, not protected flight traces. They cannot establish flight safety.
"""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate_fdi_early import early_decision, metrics, THRESHOLD_P, THRESHOLD_Q, PERSISTENCE


def sample(t, p=0.0, q=0.0, z=1.0):
    return {"time_s": str(t), "gyro_p_rps": str(p),
            "gyro_q_rps": str(q), "z_m": str(z)}


class FrozenDetectorRobustnessTests(unittest.TestCase):
    def test_threshold_boundaries_and_persistence(self):
        self.assertEqual((THRESHOLD_P, THRESHOLD_Q, PERSISTENCE), (2.0, 0.75, 3))
        for p, q, expected in [(2.0, .75, 1), (2.0, -.75, 2),
                               (-2.0, -.75, 3), (-2.0, .75, 4)]:
            with self.subTest(p=p, q=q):
                rows = [sample(10.01 + i*.032, p, q) for i in range(3)]
                self.assertEqual(early_decision(rows)["prediction"], expected)
        self.assertEqual(early_decision([sample(10.01, 3, 1),
                                         sample(10.042, 3, 1)])["prediction"], 0)

    def test_intermittent_fault_signal_resets_streak(self):
        rows = [sample(10.01, 3, 1), sample(10.042, 3, 1),
                sample(10.074, 0, 0), sample(10.106, 3, 1),
                sample(10.138, 3, 1), sample(10.170, 3, 1)]
        result = early_decision(rows)
        self.assertEqual(result["prediction"], 1)
        self.assertAlmostEqual(result["alert_time_s"], 10.170)

    def test_seeded_noise_repeatability(self):
        def perturb(seed):
            rng = random.Random(seed)
            return [sample(10.01 + i*.032,
                           3 + rng.gauss(0, .05), 1.5 + rng.gauss(0, .05))
                    for i in range(10)]
        self.assertEqual(perturb(20261011), perturb(20261011))
        self.assertEqual(early_decision(perturb(20261011)),
                         early_decision(perturb(20261011)))
        self.assertEqual(early_decision(perturb(20261011))["prediction"], 1)

    def test_noise_alone_does_not_guarantee_detection(self):
        # A synthetic subthreshold gyro signal is not a valid motor diagnosis,
        # even when the scenario label says a fault occurred.
        rows = [sample(10.01 + i*.032, 1.5, .5) for i in range(8)]
        self.assertEqual(early_decision(rows)["prediction"], 0)

    def test_first_alarm_wins_even_if_later_quadrant_changes(self):
        rows = [sample(10.01 + i*.032, 3, 1) for i in range(3)]
        rows += [sample(10.11 + i*.032, -3, -1) for i in range(3)]
        self.assertEqual(early_decision(rows)["prediction"], 1)

    def test_no_alert_after_time_censor(self):
        rows = [sample(10.71 + i*.032, 3, 1) for i in range(4)]
        self.assertEqual(early_decision(rows)["prediction"], 0)

    def test_noise_can_cause_false_alarm(self):
        # Explicit negative counterexample: the frozen rule has no way
        # to distinguish sustained healthy gyro excursion from a fault.
        rows = [sample(9.0+i*.032, 2.1, .8) for i in range(3)]
        decision = early_decision(rows)
        self.assertTrue(decision["false_alert_before_onset"])
        self.assertEqual(decision["prediction"], 1)

    def test_historical_scoring_pre_onset_caveat(self):
        # Diagnostic of a limitation in the FROZEN scoring routine:
        # a correct motor label before onset is still classed as correct,
        # even though protocol semantics say a premature alert is an error.
        early = early_decision([sample(9 + i*.032, 3, 1) for i in range(3)])
        self.assertTrue(early["false_alert_before_onset"])
        records = [{"motor": m, "prediction": m,
                    "alert_time_s": early["alert_time_s"] if m == 1 else
                                    (10.272 if m else None)} for m in range(5)]
        self.assertEqual(metrics(records)["balanced_accuracy"], 1.0)
        # This synthetic counterexample does not occur in the archived
        # held-out data; do not silently reinterpret its result.

    def test_censor_prevents_post_contact_classification(self):
        rows = [sample(10.01, 3, 1, .49),
                sample(10.042, 3, 1), sample(10.074, 3, 1),
                sample(10.106, 3, 1)]
        self.assertEqual(early_decision(rows)["prediction"], 0)


if __name__ == "__main__":
    unittest.main()
