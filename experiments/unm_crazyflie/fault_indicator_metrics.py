from __future__ import annotations

from dataclasses import dataclass, asdict
import numpy as np


@dataclass
class DetectionMetrics:
    detected: bool
    detection_rate: float
    first_alert_s: float
    response_time_s: float
    false_alarm_rate: float
    false_alarm_count: int
    alert_count: int
    precision: float
    recall: float


def _runs(mask: np.ndarray, min_consecutive: int) -> np.ndarray:
    """Apply a causal persistence filter to a threshold mask.

    A run is not considered an alert until ``min_consecutive`` samples have
    actually been observed. Earlier samples in the run therefore stay false;
    marking them retroactively would make measured response times too short.
    """
    mask = np.asarray(mask, dtype=bool)
    out = np.zeros_like(mask)
    if min_consecutive <= 1:
        return mask
    start = 0
    n = len(mask)
    while start < n:
        if not mask[start]:
            start += 1
            continue
        end = start
        while end < n and mask[end]:
            end += 1
        if end - start >= min_consecutive:
            out[start + min_consecutive - 1 : end] = True
        start = end
    return out


def alert_mask(indicator: np.ndarray, threshold: float, min_consecutive: int = 1) -> np.ndarray:
    indicator = np.asarray(indicator, dtype=float)
    finite = np.isfinite(indicator)
    return _runs(finite & (indicator > threshold), min_consecutive)


def event_window_false_alarm_rate(
    t: np.ndarray,
    indicator: np.ndarray,
    threshold: float,
    event_times_s: np.ndarray,
    window_s: float,
    exclude_mask: np.ndarray | None = None,
    min_consecutive: int = 1,
) -> float:
    """Fraction of observable, non-fault samples near normal events that alert."""
    t = np.asarray(t, dtype=float)
    indicator = np.asarray(indicator, dtype=float)
    events = np.asarray(event_times_s, dtype=float)
    near_event = np.zeros(len(t), dtype=bool)
    for event in events:
        near_event |= np.abs(t - event) <= window_s
    if exclude_mask is not None:
        near_event &= ~np.asarray(exclude_mask, dtype=bool)
    near_event &= np.isfinite(indicator)
    count = int(np.count_nonzero(near_event))
    if count == 0:
        return float("nan")
    alerts = alert_mask(indicator, threshold, min_consecutive)
    return float(np.count_nonzero(alerts & near_event) / count)


def evaluate_indicator(
    t: np.ndarray,
    indicator: np.ndarray,
    fault_mask: np.ndarray,
    threshold: float,
    min_consecutive: int = 1,
    evaluation_mask: np.ndarray | None = None,
) -> DetectionMetrics:
    """Evaluate alerts only where the detector is armed and observable.

    ``evaluation_mask`` can exclude startup/settling periods. Non-finite
    indicator samples are always excluded from rate denominators rather than
    being silently counted as true negatives.
    """
    t = np.asarray(t, dtype=float)
    indicator = np.asarray(indicator, dtype=float)
    fault_mask = np.asarray(fault_mask, dtype=bool)
    if evaluation_mask is None:
        evaluation_mask = np.ones(len(t), dtype=bool)
    else:
        evaluation_mask = np.asarray(evaluation_mask, dtype=bool)

    eligible = evaluation_mask & np.isfinite(indicator)
    alerts = alert_mask(indicator, threshold, min_consecutive) & eligible

    fault_eligible = fault_mask & eligible
    fault_alerts = alerts & fault_mask
    nonfault = (~fault_mask) & eligible
    false_alerts = alerts & nonfault

    fault_samples = int(np.count_nonzero(fault_eligible))
    nonfault_samples = int(np.count_nonzero(nonfault))
    tp = int(np.count_nonzero(fault_alerts))
    fp = int(np.count_nonzero(false_alerts))
    total_alerts = int(np.count_nonzero(alerts))

    detected = bool(tp)
    if detected:
        first_idx = int(np.flatnonzero(fault_alerts)[0])
        fault_start_candidates = np.flatnonzero(fault_mask & evaluation_mask)
        fault_start_idx = int(fault_start_candidates[0])
        first_alert_s = float(t[first_idx])
        response_time_s = max(0.0, first_alert_s - float(t[fault_start_idx]))
    else:
        first_alert_s = float("nan")
        response_time_s = float("nan")

    recall = tp / fault_samples if fault_samples else float("nan")
    precision = tp / total_alerts if total_alerts else float("nan")
    return DetectionMetrics(
        detected=detected,
        detection_rate=1.0 if detected else 0.0,
        first_alert_s=first_alert_s,
        response_time_s=response_time_s,
        false_alarm_rate=fp / nonfault_samples if nonfault_samples else float("nan"),
        false_alarm_count=fp,
        alert_count=total_alerts,
        precision=precision,
        recall=recall,
    )


def summarize(metrics: list[DetectionMetrics]) -> dict[str, float]:
    def mean_finite(values):
        arr = np.asarray(values, dtype=float)
        arr = arr[np.isfinite(arr)]
        return float(np.mean(arr)) if len(arr) else float("nan")

    return {
        "trials": len(metrics),
        "detection_rate": float(np.mean([m.detection_rate for m in metrics])) if metrics else float("nan"),
        "mean_response_time_s": mean_finite([m.response_time_s for m in metrics]),
        "mean_false_alarm_rate": mean_finite([m.false_alarm_rate for m in metrics]),
        "mean_precision": mean_finite([m.precision for m in metrics]),
        "mean_recall": mean_finite([m.recall for m in metrics]),
    }


def to_dict(metrics: DetectionMetrics) -> dict:
    return asdict(metrics)
