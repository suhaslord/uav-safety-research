from __future__ import annotations

import math
from typing import Iterable

import numpy as np


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total <= 0:
        return 0.0, 0.0
    p = successes / total
    denom = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / denom
    half = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * total)) / total) / denom
    return max(0.0, center - half), min(1.0, center + half)


def first_sustained_true(
    time_s: Iterable[float],
    mask: Iterable[bool],
    *,
    start_index: int,
    dwell_s: float,
) -> int | None:
    t = np.asarray(list(time_s), dtype=float)
    ok = np.asarray(list(mask), dtype=bool)
    if len(t) != len(ok):
        raise ValueError("time and mask lengths differ")
    if dwell_s < 0:
        raise ValueError("dwell_s must be >= 0")
    for i in range(max(0, int(start_index)), len(ok)):
        if not ok[i]:
            continue
        if dwell_s == 0:
            return i
        end_t = t[i] + float(dwell_s)
        j = int(np.searchsorted(t, end_t, side="left"))
        if j >= len(ok):
            return None
        if bool(ok[i : j + 1].all()):
            return i
    return None


def recovery_outcome(
    time_s: Iterable[float],
    degraded_mask: Iterable[bool],
    recovery_mask: Iterable[bool],
    *,
    onset_s: float,
    dwell_s: float,
) -> dict:
    """Measure recovery without assigning a fake time to non-recovery."""

    t = np.asarray(list(time_s), dtype=float)
    degraded = np.asarray(list(degraded_mask), dtype=bool)
    recovered = np.asarray(list(recovery_mask), dtype=bool)
    if len(t) != len(degraded) or len(t) != len(recovered):
        raise ValueError("recovery arrays must have equal lengths")
    if not len(t):
        return {
            "degraded_entered": False,
            "degraded_entry_s": None,
            "recovered": False,
            "recovery_index": None,
            "recovery_time_s": None,
            "non_recovery": True,
        }

    start = int(np.searchsorted(t, float(onset_s), side="left"))
    degraded_idx = next((i for i in range(start, len(t)) if degraded[i]), None)
    if degraded_idx is None:
        return {
            "degraded_entered": False,
            "degraded_entry_s": None,
            "recovered": True,
            "recovery_index": None,
            "recovery_time_s": 0.0,
            "non_recovery": False,
        }

    recovery_idx = first_sustained_true(
        t,
        recovered,
        start_index=degraded_idx,
        dwell_s=dwell_s,
    )
    if recovery_idx is None:
        return {
            "degraded_entered": True,
            "degraded_entry_s": float(t[degraded_idx]),
            "recovered": False,
            "recovery_index": None,
            "recovery_time_s": None,
            "non_recovery": True,
        }

    return {
        "degraded_entered": True,
        "degraded_entry_s": float(t[degraded_idx]),
        "recovered": True,
        "recovery_index": int(recovery_idx),
        "recovery_time_s": float(t[recovery_idx] - t[degraded_idx]),
        "non_recovery": False,
    }


def terminal_failure(outcome: str, failure_outcomes: Iterable[str]) -> bool:
    return str(outcome) in {str(value) for value in failure_outcomes}
