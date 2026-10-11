"""Local, simulator-free checks of the frozen FDI-H1 evaluator."""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_trajectory_generalization import (
    TEST_SEEDS, cluster_bootstrap, metric, select_columns, COMMAND_FEATURES,
)


class FDIH1Tests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {
                "split": "test", "seed": seed, "failed_motor": motor,
                "full_prediction": motor, "command_only_prediction": 0,
                "always_healthy_prediction": 0, "scored_windows": 3,
            }
            for seed in TEST_SEEDS for motor in range(5)
        ]

    def test_class_is_trajectory_not_overlapping_window(self):
        self.assertEqual(len(self.rows), 40)
        self.assertEqual(metric(self.rows, "full_prediction")["balanced_accuracy"], 1.0)
        self.assertEqual(metric(self.rows, "always_healthy_prediction")["balanced_accuracy"], 0.2)

    def test_seed_cluster_bootstrap_is_deterministic(self):
        full = cluster_bootstrap(self.rows, "full_prediction")
        baseline = cluster_bootstrap(self.rows, "always_healthy_prediction")
        self.assertEqual(full["percentile_95_interval"], [1.0, 1.0])
        self.assertEqual(baseline["percentile_95_interval"], [0.2, 0.2])
        self.assertEqual(full, cluster_bootstrap(self.rows, "full_prediction"))
        self.assertEqual(full["seed_clusters"], 8)

    def test_command_ablation_removes_position_and_gyro(self):
        x = np.arange(2 * 100 * 10, dtype=np.float32).reshape(2, -1)
        selected = select_columns(x, command_only=True)
        self.assertEqual(selected.shape, (2, 4 * 100))
        np.testing.assert_array_equal(
            selected.reshape(2, 100, 4),
            x.reshape(2, 100, 10)[:, :, COMMAND_FEATURES],
        )
        np.testing.assert_array_equal(select_columns(x, False), x)


if __name__ == "__main__":
    unittest.main()
