from __future__ import annotations

from dataclasses import asdict, dataclass
from math import sqrt
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class EpisodeOutcome:
    episode_id: str
    evidence_role: str
    policy: str
    faulted: bool
    fault_motor: int | None
    effectiveness: float
    onset_s: float | None
    detected: bool
    isolated_motor: int | None
    detection_latency_s: float | None
    false_positive: bool
    false_negative: bool
    isolation_correct: bool | None
    envelope_violations: int
    recovered: bool
    recovery_time_s: float | None
    terminal_failure: bool
    abstained: bool

    def to_dict(self) -> dict:
        return asdict(self)


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total <= 0:
        return (0.0, 0.0)
    p = successes / total
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    margin = (z / denom) * sqrt((p * (1 - p) / total) + (z * z / (4 * total * total)))
    return max(0.0, center - margin), min(1.0, center + margin)


def summarize_outcomes(outcomes: Iterable[EpisodeOutcome] | pd.DataFrame) -> dict:
    df = outcomes.copy() if isinstance(outcomes, pd.DataFrame) else pd.DataFrame([o.to_dict() for o in outcomes])
    if df.empty:
        return {"episodes": 0}
    n = len(df); failures = int(df["terminal_failure"].astype(bool).sum())
    recovered = df["recovered"].astype(bool); faulted = df["faulted"].astype(bool); detected = df["detected"].astype(bool)
    fp = int(df["false_positive"].astype(bool).sum()); fn = int(df["false_negative"].astype(bool).sum())
    non_recovery = int((faulted & ~recovered).sum()); isolatable = df["isolation_correct"].notna()
    isolation_correct = int(df.loc[isolatable, "isolation_correct"].astype(bool).sum())
    recovery = pd.to_numeric(df.loc[recovered, "recovery_time_s"], errors="coerce").dropna()
    latency = pd.to_numeric(df.loc[faulted & detected, "detection_latency_s"], errors="coerce").dropna()
    failure_ci = wilson_interval(failures, n)
    return {
        "episodes": int(n),
        "failure_probability": failures / n,
        "failure_probability_ci95": [failure_ci[0], failure_ci[1]],
        "recovered_episodes": int(recovered.sum()),
        "mean_recovery_time_s_recovered_only": float(recovery.mean()) if len(recovery) else None,
        "median_recovery_time_s_recovered_only": float(recovery.median()) if len(recovery) else None,
        "non_recovery_rate_faulted": non_recovery / int(faulted.sum()) if faulted.any() else 0.0,
        "mean_detection_latency_s_detected_faults": float(latency.mean()) if len(latency) else None,
        "median_detection_latency_s_detected_faults": float(latency.median()) if len(latency) else None,
        "isolation_accuracy_detected_faults": isolation_correct / int(isolatable.sum()) if isolatable.any() else None,
        "false_positive_count": fp,
        "false_negative_count": fn,
        "false_positive_rate_nominal": fp / int((~faulted).sum()) if (~faulted).any() else None,
        "false_negative_rate_faulted": fn / int(faulted.sum()) if faulted.any() else None,
        "safety_envelope_violations": int(pd.to_numeric(df["envelope_violations"], errors="coerce").fillna(0).sum()),
        "abstention_rate": float(df["abstained"].astype(bool).mean()),
    }


def first_sustained_recovery(time_s: np.ndarray, in_nominal_envelope: np.ndarray, *, degraded_start_s: float, dwell_s: float) -> float | None:
    t = np.asarray(time_s, dtype=float); ok = np.asarray(in_nominal_envelope, dtype=bool)
    if len(t) != len(ok):
        raise ValueError("time and envelope arrays differ")
    start = int(np.searchsorted(t, degraded_start_s, side="left"))
    for i in range(start, len(t)):
        if not ok[i]:
            continue
        j = int(np.searchsorted(t, t[i] + dwell_s, side="left"))
        if j < len(t) and bool(np.all(ok[i:j + 1])):
            return float(t[i] - degraded_start_s)
    return None
