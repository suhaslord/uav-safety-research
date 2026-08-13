from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import math
import random
from typing import Iterable

import numpy as np

PAPER_WINDOW = 100
PAPER_FAULT_THRESHOLD = 0.1
PAPER_MOTOR_COUNT = 4
PAPER_HIDDEN_DIM = 128
PAPER_FC_DIM = 64


@dataclass(frozen=True)
class FaultDecision:
    fault_detected: bool
    isolated_motor: int | None
    minimum_score: float
    scores: tuple[float, ...]


@dataclass(frozen=True)
class TrainingConfig:
    window: int = PAPER_WINDOW
    threshold: float = PAPER_FAULT_THRESHOLD
    hidden_dim: int = PAPER_HIDDEN_DIM
    fc_dim: int = PAPER_FC_DIM
    motor_count: int = PAPER_MOTOR_COUNT
    epsilon: float = 0.05
    learning_rate: float = 2e-2
    batch_size: int = 256
    epochs: int = 60
    seed: int = 20260813


@dataclass
class FeatureStandardizer:
    mean: np.ndarray
    scale: np.ndarray

    @classmethod
    def fit(cls, x: np.ndarray) -> "FeatureStandardizer":
        arr = np.asarray(x, dtype=np.float64)
        if arr.ndim != 3:
            raise ValueError("expected [samples, window, features]")
        mean = arr.reshape(-1, arr.shape[-1]).mean(axis=0)
        scale = arr.reshape(-1, arr.shape[-1]).std(axis=0)
        scale = np.where(scale < 1e-8, 1.0, scale)
        return cls(mean=mean, scale=scale)

    def transform(self, x: np.ndarray) -> np.ndarray:
        return (np.asarray(x, dtype=np.float32) - self.mean.astype(np.float32)) / self.scale.astype(np.float32)

    def to_json(self) -> dict:
        return {"mean": self.mean.tolist(), "scale": self.scale.tolist()}

    @classmethod
    def from_json(cls, data: dict) -> "FeatureStandardizer":
        return cls(mean=np.asarray(data["mean"], dtype=np.float64), scale=np.asarray(data["scale"], dtype=np.float64))


def healthy_label(motor_count: int = PAPER_MOTOR_COUNT) -> np.ndarray:
    return np.ones(motor_count, dtype=np.float32)


def single_fault_label(motor_index: int, motor_count: int = PAPER_MOTOR_COUNT) -> np.ndarray:
    if not 0 <= motor_index < motor_count:
        raise ValueError("motor_index out of range")
    out = healthy_label(motor_count)
    out[motor_index] = 0.0
    return out


def make_trace_windows(outputs: np.ndarray, commands: np.ndarray, *, window: int = PAPER_WINDOW) -> tuple[np.ndarray, np.ndarray]:
    """Build the paper-style finite history [y, u]."""
    y = np.asarray(outputs, dtype=np.float32)
    u = np.asarray(commands, dtype=np.float32)
    if y.ndim != 2 or u.ndim != 2:
        raise ValueError("outputs and commands must be 2-D")
    if y.shape[0] != u.shape[0]:
        raise ValueError("outputs and commands must have equal sample counts")
    if window <= 0:
        raise ValueError("window must be positive")
    if y.shape[0] < window:
        return np.empty((0, window, y.shape[1] + u.shape[1]), dtype=np.float32), np.empty(0, dtype=int)
    joined = np.concatenate([y, u], axis=1)
    windows = np.stack([joined[i - window + 1 : i + 1] for i in range(window - 1, joined.shape[0])])
    return windows, np.arange(window - 1, joined.shape[0], dtype=int)


def decide_fault(scores: Iterable[float], threshold: float = PAPER_FAULT_THRESHOLD) -> FaultDecision:
    arr = np.asarray(tuple(scores), dtype=np.float64)
    if arr.ndim != 1 or arr.size == 0:
        raise ValueError("scores must be a non-empty vector")
    idx = int(np.argmin(arr))
    minimum = float(arr[idx])
    detected = bool(minimum < threshold)
    return FaultDecision(detected, idx if detected else None, minimum, tuple(float(v) for v in arr))


def tolerance_hinge_loss_numpy(prediction: np.ndarray, target: np.ndarray, epsilon: float) -> float:
    pred = np.asarray(prediction, dtype=np.float64)
    tgt = np.asarray(target, dtype=np.float64)
    if pred.shape != tgt.shape:
        raise ValueError("prediction and target shapes differ")
    if pred.ndim == 1:
        pred, tgt = pred[None, :], tgt[None, :]
    return float(np.maximum(np.linalg.norm(pred - tgt, axis=-1) - float(epsilon), 0.0).mean())


def _require_torch():
    try:
        import torch
        import torch.nn as nn
    except ImportError as exc:
        raise RuntimeError("PyTorch is required for Ornik FDI training/inference") from exc
    return torch, nn


def build_lstm_detector(input_dim: int, *, hidden_dim: int = PAPER_HIDDEN_DIM, fc_dim: int = PAPER_FC_DIM, motor_count: int = PAPER_MOTOR_COUNT):
    torch, nn = _require_torch()
    class OrnikLSTM(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.lstm = nn.LSTM(input_size=input_dim, hidden_size=hidden_dim, batch_first=True)
            self.fc1 = nn.Linear(hidden_dim, fc_dim)
            self.fc2 = nn.Linear(fc_dim, motor_count)
        def forward(self, x):
            seq, _ = self.lstm(x)
            return self.fc2(torch.relu(self.fc1(seq[:, -1, :])))
    return OrnikLSTM()


def set_deterministic_seed(seed: int) -> None:
    random.seed(seed); np.random.seed(seed)
    try:
        torch, _ = _require_torch()
    except RuntimeError:
        return
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    try:
        torch.use_deterministic_algorithms(True)
    except Exception:
        pass


def train_lstm(windows: np.ndarray, targets: np.ndarray, *, config: TrainingConfig, model_out: Path, standardizer_out: Path) -> dict:
    torch, _ = _require_torch()
    x, y = np.asarray(windows, dtype=np.float32), np.asarray(targets, dtype=np.float32)
    if x.ndim != 3 or y.ndim != 2 or x.shape[0] != y.shape[0]:
        raise ValueError("invalid training arrays")
    if y.shape[1] != config.motor_count:
        raise ValueError("target motor count differs from config")
    set_deterministic_seed(config.seed)
    standardizer = FeatureStandardizer.fit(x); x = standardizer.transform(x)
    model = build_lstm_detector(x.shape[-1], hidden_dim=config.hidden_dim, fc_dim=config.fc_dim, motor_count=config.motor_count)
    optimizer = torch.optim.SGD(model.parameters(), lr=config.learning_rate)
    xt, yt = torch.from_numpy(x), torch.from_numpy(y)
    generator = torch.Generator().manual_seed(config.seed); history = []
    for _ in range(config.epochs):
        order = torch.randperm(len(xt), generator=generator); losses = []
        for start in range(0, len(order), config.batch_size):
            idx = order[start:start + config.batch_size]
            pred = model(xt[idx]); loss = torch.relu(torch.linalg.vector_norm(pred - yt[idx], dim=1) - config.epsilon).mean()
            optimizer.zero_grad(); loss.backward(); optimizer.step(); losses.append(float(loss.detach()))
        history.append(float(np.mean(losses)) if losses else math.nan)
    model_out.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "input_dim": int(x.shape[-1]), "hidden_dim": config.hidden_dim, "fc_dim": config.fc_dim, "motor_count": config.motor_count, "window": config.window, "threshold": config.threshold, "training_config": config.__dict__}, model_out)
    standardizer_out.write_text(json.dumps(standardizer.to_json(), indent=2, sort_keys=True) + "\n")
    return {"epochs": config.epochs, "final_loss": history[-1] if history else None, "loss_history": history, "samples": int(len(x)), "input_dim": int(x.shape[-1])}


def load_lstm(model_path: Path, standardizer_path: Path):
    torch, _ = _require_torch(); checkpoint = torch.load(model_path, map_location="cpu", weights_only=True)
    model = build_lstm_detector(int(checkpoint["input_dim"]), hidden_dim=int(checkpoint["hidden_dim"]), fc_dim=int(checkpoint["fc_dim"]), motor_count=int(checkpoint["motor_count"]))
    model.load_state_dict(checkpoint["state_dict"]); model.eval()
    return model, FeatureStandardizer.from_json(json.loads(standardizer_path.read_text())), checkpoint


def predict_scores(model, standardizer: FeatureStandardizer, windows: np.ndarray) -> np.ndarray:
    torch, _ = _require_torch(); x = standardizer.transform(np.asarray(windows, dtype=np.float32))
    with torch.no_grad():
        return model(torch.from_numpy(x)).cpu().numpy()
