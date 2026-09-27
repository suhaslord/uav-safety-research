"""Prediction-only Phase 26 confidence rule; labels enter evaluation afterward."""

from __future__ import annotations

from math import isfinite
from typing import Mapping, Sequence


def top_prediction(predictions: Sequence[Mapping[str, object]]) -> Mapping[str, object] | None:
    """Return the highest-scoring mapped target, breaking ties by input order."""
    ranked = []
    for item in predictions:
        if item.get("class") != "landing_target":
            continue
        score = item.get("score")
        if not isinstance(score, (int, float)) or not isfinite(score) or not 0 <= score <= 1:
            raise ValueError("Prediction score must be finite and between 0 and 1")
        ranked.append(item)
    return max(ranked, key=lambda row: row["score"], default=None)


def confidence_score(predictions: Sequence[Mapping[str, object]]) -> float:
    """A runtime score with no access to ground truth."""
    best = top_prediction(predictions)
    return float(best["score"]) if best is not None else 0.0


def accept(predictions: Sequence[Mapping[str, object]], threshold: float | None) -> bool:
    """None means the development gate failed and the rule always abstains."""
    if threshold is None:
        return False
    if not 0 < threshold <= 1:
        raise ValueError("The frozen threshold must be strictly positive and <= 1")
    return confidence_score(predictions) >= threshold


def _iou(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != 4 or len(b) != 4:
        raise ValueError("Boxes need four xyxy coordinates")
    if any(not isfinite(float(v)) for v in (*a, *b)):
        raise ValueError("Box coordinates must be finite")
    if a[2] <= a[0] or a[3] <= a[1] or b[2] <= b[0] or b[3] <= b[1]:
        raise ValueError("Boxes must have positive area")
    w = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    h = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    intersection = w * h
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return intersection / (area_a + area_b - intersection)


def top_localization_correct(
    predictions: Sequence[Mapping[str, object]], targets: Sequence[Sequence[float]]
) -> bool:
    """Evaluation only. Call after freezing the prediction-only decision."""
    best = top_prediction(predictions)
    return best is not None and any(_iou(best["box"], target) >= 0.50 for target in targets)


def select_development_threshold(
    labeled_scores: Sequence[tuple[float, bool]],
) -> dict[str, object]:
    """Prespecified 0.05..0.95 grid; never call with sealed-test outcomes."""
    if not labeled_scores:
        raise ValueError("Development set is empty")
    for score, correct in labeled_scores:
        if not isfinite(score) or not 0 <= score <= 1 or not isinstance(correct, bool):
            raise ValueError("Invalid development score or correctness label")
    trace = []
    for step in range(1, 20):
        threshold = step / 20
        accepted = [correct for score, correct in labeled_scores if score >= threshold]
        errors = accepted.count(False)
        trace.append({"threshold": threshold, "accepted": len(accepted),
                      "accepted_errors": errors,
                      "accepted_error_rate": errors / len(accepted) if accepted else None})
    eligible = [row for row in trace if row["accepted"] and row["accepted_error_rate"] <= 0.05]
    chosen = max(eligible, key=lambda row: (row["accepted"], row["threshold"]), default=None)
    return {"threshold": chosen["threshold"] if chosen else None,
            "status": "selected" if chosen else "development_gate_failed_abstain_all",
            "development_count": len(labeled_scores), "trace": trace}
