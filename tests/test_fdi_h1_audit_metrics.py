"""Synthetic regression tests for the independent FDI evidence auditor.

These intentionally do not read the protected 70-trace artifact.
"""
from copy import deepcopy

import pytest

from scripts.audit_fdi_h1_artifact import PROTECTED, verify_report_metrics


def synthetic_records(*, always_healthy=False):
    return [
        {"seed": seed, "motor": motor,
         "prediction": 0 if always_healthy else motor,
         "alert_time_s": None if always_healthy or motor == 0 else 10.272}
        for seed in PROTECTED for motor in range(5)
    ]


def synthetic_report(*, always_healthy=False):
    accuracy = .2 if always_healthy else 1.0
    correct_fault_rate = 0.0 if always_healthy else 1.0
    confusion = [[0] * 5 for _ in range(5)]
    for motor in range(5):
        confusion[motor][0 if always_healthy else motor] = len(PROTECTED)
    return {
        "protected_result": {
            "trajectories": 40,
            "balanced_accuracy": accuracy,
            "healthy_false_alarm_rate": 0.0,
            "fault_detection_rate": correct_fault_rate,
            "correct_fault_isolation_rate": correct_fault_rate,
            "median_correct_detection_latency_s": None if always_healthy else .272,
            "class_recall": dict(zip(
                ("healthy", "motor_1", "motor_2", "motor_3", "motor_4"),
                (1.0, 0.0, 0.0, 0.0, 0.0) if always_healthy else (1.0,) * 5)),
            "confusion_matrix_rows_true_cols_predicted": confusion,
        },
        "protected_seed_cluster_bootstrap": {
            "random_seed": 20261012,
            "bootstrap_draws": 2000,
            "percentile_95_interval": [accuracy, accuracy],
        },
        "always_healthy_balanced_accuracy": .2,
    }


@pytest.mark.parametrize("always_healthy", [False, True])
def test_replays_complete_good_and_bad_synthetic_outcomes(always_healthy):
    report = synthetic_report(always_healthy=always_healthy)
    matrix, delays = verify_report_metrics(
        report, synthetic_records(always_healthy=always_healthy))
    assert matrix == report["protected_result"]["confusion_matrix_rows_true_cols_predicted"]
    assert len(delays) == (0 if always_healthy else 32)


@pytest.mark.parametrize("field,value", [
    ("balanced_accuracy", .75),
    ("correct_fault_isolation_rate", .5),
    ("healthy_false_alarm_rate", .25),
    ("median_correct_detection_latency_s", 0.5),
])
def test_falsified_published_metric_is_rejected(field, value):
    report = synthetic_report()
    report["protected_result"][field] = value
    with pytest.raises(ValueError, match=field):
        verify_report_metrics(report, synthetic_records())


def test_falsified_seed_cluster_interval_is_rejected():
    report = synthetic_report()
    report["protected_seed_cluster_bootstrap"]["percentile_95_interval"] = [.6, 1]
    with pytest.raises(ValueError, match="seed_cluster_bootstrap"):
        verify_report_metrics(report, synthetic_records())


def test_missing_paired_seed_scenario_is_rejected():
    with pytest.raises(ValueError, match="each motor condition"):
        verify_report_metrics(synthetic_report(), synthetic_records()[:-1])


def test_null_latency_in_bad_outcome_is_not_replaced_by_zero():
    report = synthetic_report(always_healthy=True)
    report["protected_result"]["median_correct_detection_latency_s"] = 0
    with pytest.raises(ValueError, match="median_correct_detection_latency_s"):
        verify_report_metrics(report, synthetic_records(always_healthy=True))
