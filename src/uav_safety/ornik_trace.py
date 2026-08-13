from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

import numpy as np
import pandas as pd

from .ornik_fdi import make_trace_windows, decide_fault, load_lstm, predict_scores
from .ornik_metrics import EpisodeOutcome, first_sustained_recovery


@dataclass(frozen=True)
class EnvelopeConfig:
    max_abs_x_m: float = 6.0
    max_abs_y_m: float = 6.0
    min_altitude_m: float = 0.15
    max_altitude_m: float = 8.0
    max_abs_body_rate_rad_s: float = 3.0
    terminal_body_rate_rad_s: float = 8.0
    terminal_lateral_m: float = 10.0
    terminal_altitude_m: float = 12.0
    recovery_dwell_s: float = 1.0


def trace_features(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    y = df[["x_m", "y_m", "z_ned_m", "wx_rad_s", "wy_rad_s", "wz_rad_s"]].to_numpy(dtype=np.float32)
    u = df[["u0", "u1", "u2", "u3"]].to_numpy(dtype=np.float32)
    return y, u


def evaluate_detector(df: pd.DataFrame, *, model_path: Path, standardizer_path: Path, threshold: float, window: int) -> pd.DataFrame:
    model, standardizer, _ = load_lstm(model_path, standardizer_path)
    y, u = trace_features(df); windows, end_indices = make_trace_windows(y, u, window=window)
    scores = predict_scores(model, standardizer, windows); rows = []
    for source_idx, score in zip(end_indices, scores, strict=True):
        d = decide_fault(score, threshold)
        rows.append({"source_index": int(source_idx), "timestamp_s": float(df.iloc[source_idx]["timestamp_s"]), "relative_time_s": float(df.iloc[source_idx]["relative_time_s"]), "fault_detected": d.fault_detected, "isolated_motor": d.isolated_motor, "minimum_score": d.minimum_score, **{f"theta_{i}": d.scores[i] for i in range(len(d.scores))}})
    return pd.DataFrame(rows)


def state_envelope(df: pd.DataFrame, cfg: EnvelopeConfig) -> tuple[np.ndarray, np.ndarray]:
    rates = np.max(np.abs(df[["wx_rad_s", "wy_rad_s", "wz_rad_s"]].to_numpy(dtype=float)), axis=1)
    x = np.abs(df["x_m"].to_numpy(dtype=float)); y = np.abs(df["y_m"].to_numpy(dtype=float)); alt = df["altitude_m"].to_numpy(dtype=float)
    nominal = (x <= cfg.max_abs_x_m) & (y <= cfg.max_abs_y_m) & (alt >= cfg.min_altitude_m) & (alt <= cfg.max_altitude_m) & (rates <= cfg.max_abs_body_rate_rad_s)
    terminal = (x > cfg.terminal_lateral_m) | (y > cfg.terminal_lateral_m) | (alt > cfg.terminal_altitude_m) | (rates > cfg.terminal_body_rate_rad_s)
    return nominal, terminal


def summarize_episode(df: pd.DataFrame, detections: pd.DataFrame, *, episode_id: str, evidence_role: str, policy: str, fault_motor: int | None, effectiveness: float, onset_timestamp_s: float | None, envelope: EnvelopeConfig) -> EpisodeOutcome:
    faulted = fault_motor is not None and onset_timestamp_s is not None
    hit = detections[detections["fault_detected"].astype(bool)] if not detections.empty else pd.DataFrame()
    first = None if hit.empty else hit.iloc[0]
    detected = first is not None; isolated = int(first["isolated_motor"]) if detected else None
    latency = max(0.0, float(first["timestamp_s"]) - float(onset_timestamp_s)) if faulted and detected else None
    false_positive = bool((not faulted) and detected); false_negative = bool(faulted and not detected)
    isolation_correct = None if not (faulted and detected) else bool(isolated == int(fault_motor))
    nominal, terminal = state_envelope(df, envelope)
    if onset_timestamp_s is None:
        post = np.ones(len(df), dtype=bool); degraded_start = float(df["timestamp_s"].iloc[0])
    else:
        post = df["timestamp_s"].to_numpy(dtype=float) >= float(onset_timestamp_s); degraded_start = float(onset_timestamp_s)
    violations = int((post & ~nominal).sum())
    recovery_time = None; recovered = True if not faulted else False
    if faulted:
        recovery_time = first_sustained_recovery(df["timestamp_s"].to_numpy(dtype=float), nominal, degraded_start_s=degraded_start, dwell_s=envelope.recovery_dwell_s)
        recovered = recovery_time is not None
    return EpisodeOutcome(episode_id, evidence_role, policy, faulted, fault_motor, float(effectiveness), None if onset_timestamp_s is None else float(onset_timestamp_s - df["timestamp_s"].iloc[0]), detected, isolated, latency, false_positive, false_negative, isolation_correct, violations, recovered, recovery_time, bool(np.any(post & terminal)), bool(faulted and not detected))


def read_fault_receipt(path: Path) -> dict | None:
    if not path.exists() or not path.read_text().strip():
        return None
    timestamp_us, motor, effectiveness = path.read_text().strip().splitlines()[0].split(",")
    return {"timestamp_us": int(timestamp_us), "timestamp_s": int(timestamp_us) * 1e-6, "motor_index": int(motor), "effectiveness": float(effectiveness)}
