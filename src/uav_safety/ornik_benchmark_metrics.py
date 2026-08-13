from __future__ import annotations

from math import sqrt
from typing import Iterable

import numpy as np


def thrust_effectiveness_to_speed_scale(effectiveness: float) -> float:
    """Map a thrust-effectiveness fraction to rotor-speed scale for F proportional to omega^2."""
    effectiveness = float(effectiveness)
    if not 0.0 <= effectiveness <= 1.0:
        raise ValueError("effectiveness must be in [0, 1]")
    return sqrt(effectiveness)


def _first_sustained_true(time_s: np.ndarray, mask: np.ndarray, start_index: int, dwell_s: float) -> int | None:
    t = np.asarray(time_s, dtype=float)
    ok = np.asarray(mask, dtype=bool)
    if len(t) != len(ok):
        raise ValueError("time and mask lengths differ")
    for i in range(max(0, int(start_index)), len(ok)):
        if not ok[i]:
            continue
        end_t = t[i] + float(dwell_s)
        j = int(np.searchsorted(t, end_t, side="left"))
        if j >= len(ok):
            return None
        if bool(ok[i : j + 1].all()):
            return i
    return None


def recovery_outcome(
    time_s: np.ndarray,
    degraded_mask: np.ndarray,
    recovery_mask: np.ndarray,
    *,
    onset_s: float,
    dwell_s: float,
) -> dict:
    """Measure recovery from first degraded-envelope entry; preserve non-recovery as null."""
    t = np.asarray(time_s, dtype=float)
    degraded = np.asarray(degraded_mask, dtype=bool)
    recovered = np.asarray(recovery_mask, dtype=bool)
    if len(t) != len(degraded) or len(t) != len(recovered):
        raise ValueError("recovery arrays must have equal lengths")
    if not len(t):
        return {"degraded_entered": False, "recovered": False, "non_recovery": True, "recovery_time_s": None}
    start = int(np.searchsorted(t, float(onset_s), side="left"))
    degraded_idx = next((i for i in range(start, len(t)) if degraded[i]), None)
    if degraded_idx is None:
        return {"degraded_entered": False, "recovered": True, "non_recovery": False, "recovery_time_s": 0.0}
    recovery_idx = _first_sustained_true(t, recovered, degraded_idx, dwell_s)
    if recovery_idx is None:
        return {"degraded_entered": True, "recovered": False, "non_recovery": True, "recovery_time_s": None}
    return {
        "degraded_entered": True,
        "recovered": True,
        "non_recovery": False,
        "recovery_time_s": float(t[recovery_idx] - t[degraded_idx]),
    }


def detection_outcome(
    time_s: np.ndarray,
    score_rows: np.ndarray,
    *,
    threshold: float,
    fault_onset_s: float | None,
    true_fault_motor: int | None,
) -> dict:
    from .ornik_fdi import decide_fault

    t = np.asarray(time_s, dtype=float)
    scores = np.asarray(score_rows, dtype=float)
    if scores.ndim != 2 or len(t) != len(scores):
        raise ValueError("scores must be [time, motor]")
    decisions = [decide_fault(row, threshold) for row in scores]
    if fault_onset_s is None or true_fault_motor is None:
        fp_idx = next((i for i, d in enumerate(decisions) if d.fault_detected), None)
        return {
            "detected": fp_idx is not None,
            "detection_latency_s": None,
            "isolated_motor": None if fp_idx is None else decisions[fp_idx].isolated_motor,
            "isolation_correct": None,
            "false_positive": fp_idx is not None,
            "false_negative": False,
        }
    onset_idx = int(np.searchsorted(t, float(fault_onset_s), side="left"))
    false_positive = any(d.fault_detected for d in decisions[:onset_idx])
    det_idx = next((i for i in range(onset_idx, len(decisions)) if decisions[i].fault_detected), None)
    if det_idx is None:
        return {"detected": False, "detection_latency_s": None, "isolated_motor": None,
                "isolation_correct": False, "false_positive": bool(false_positive), "false_negative": True}
    isolated = decisions[det_idx].isolated_motor
    return {
        "detected": True,
        "detection_latency_s": max(0.0, float(t[det_idx] - float(fault_onset_s))),
        "isolated_motor": isolated,
        "isolation_correct": isolated == int(true_fault_motor),
        "false_positive": bool(false_positive),
        "false_negative": False,
    }
