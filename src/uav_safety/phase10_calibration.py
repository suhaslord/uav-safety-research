from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable
import json
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class SourceSigma:
    sigma_lateral_m: float
    sigma_altitude_m: float
    samples: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Phase10UncertaintyCalibrator:
    """Small empirical uncertainty model fit only on declared development data.

    Calibration is source-aware because fresh ArUco geometry and temporal
    prediction through rejected quads have visibly different error scales.
    """

    by_source: dict[str, SourceSigma]
    fallback: SourceSigma
    quantile: float = 0.68
    min_sigma_lateral_m: float = 0.03
    min_sigma_altitude_m: float = 0.03

    @classmethod
    def fit(
        cls,
        samples: Iterable[dict],
        *,
        quantile: float = 0.68,
        min_samples_per_source: int = 3,
        min_sigma_lateral_m: float = 0.03,
        min_sigma_altitude_m: float = 0.03,
    ) -> "Phase10UncertaintyCalibrator":
        records = list(samples)
        if not records:
            raise ValueError("calibration samples must be non-empty")
        if not 0.5 <= quantile < 1.0:
            raise ValueError("quantile must be in [0.5, 1.0)")

        usable = []
        for row in records:
            ex = float(row["abs_lateral_error_m"])
            ez = float(row["abs_altitude_error_m"])
            if np.isfinite(ex) and np.isfinite(ez):
                usable.append((str(row["source"]), abs(ex), abs(ez)))
        if not usable:
            raise ValueError("no finite calibration residuals")

        all_x = np.asarray([r[1] for r in usable], dtype=float)
        all_z = np.asarray([r[2] for r in usable], dtype=float)
        fallback = SourceSigma(
            sigma_lateral_m=max(min_sigma_lateral_m, float(np.quantile(all_x, quantile))),
            sigma_altitude_m=max(min_sigma_altitude_m, float(np.quantile(all_z, quantile))),
            samples=len(usable),
        )

        by_source: dict[str, SourceSigma] = {}
        for source in sorted({r[0] for r in usable}):
            source_rows = [r for r in usable if r[0] == source]
            if len(source_rows) < min_samples_per_source:
                sx = max(min_sigma_lateral_m, max(r[1] for r in source_rows), fallback.sigma_lateral_m)
                sz = max(min_sigma_altitude_m, max(r[2] for r in source_rows), fallback.sigma_altitude_m)
            else:
                sx = max(min_sigma_lateral_m, float(np.quantile([r[1] for r in source_rows], quantile)))
                sz = max(min_sigma_altitude_m, float(np.quantile([r[2] for r in source_rows], quantile)))
            by_source[source] = SourceSigma(sx, sz, len(source_rows))

        return cls(
            by_source=by_source,
            fallback=fallback,
            quantile=quantile,
            min_sigma_lateral_m=min_sigma_lateral_m,
            min_sigma_altitude_m=min_sigma_altitude_m,
        )

    def sigma(self, source: str) -> tuple[float, float]:
        record = self.by_source.get(source, self.fallback)
        return float(record.sigma_lateral_m), float(record.sigma_altitude_m)

    def to_dict(self) -> dict:
        return {
            "schema": "aegisland.phase10.uncertainty-calibration.v1",
            "quantile": self.quantile,
            "min_sigma_lateral_m": self.min_sigma_lateral_m,
            "min_sigma_altitude_m": self.min_sigma_altitude_m,
            "fallback": self.fallback.to_dict(),
            "by_source": {key: value.to_dict() for key, value in sorted(self.by_source.items())},
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "Phase10UncertaintyCalibrator":
        if payload.get("schema") != "aegisland.phase10.uncertainty-calibration.v1":
            raise ValueError("unsupported Phase 10 calibration schema")
        return cls(
            by_source={str(key): SourceSigma(**value) for key, value in payload["by_source"].items()},
            fallback=SourceSigma(**payload["fallback"]),
            quantile=float(payload["quantile"]),
            min_sigma_lateral_m=float(payload["min_sigma_lateral_m"]),
            min_sigma_altitude_m=float(payload["min_sigma_altitude_m"]),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Phase10UncertaintyCalibrator":
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
