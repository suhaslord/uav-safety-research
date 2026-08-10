from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Iterable

import numpy as np

from .perception import PROFILES, PerceptionProfile
from .reference_estimator import ReferenceEstimatorConfig


@dataclass(frozen=True)
class RobustnessScenario:
    """One explicit out-of-distribution simulation stress condition."""

    name: str
    axis: str
    description: str
    perception_profile: PerceptionProfile
    reference_config: ReferenceEstimatorConfig
    level: float | str

    def metadata(self) -> dict:
        return {
            "name": self.name,
            "axis": self.axis,
            "description": self.description,
            "level": self.level,
            "perception_profile": asdict(self.perception_profile),
            "reference_config": asdict(self.reference_config),
        }


def scale_perception(
    base: PerceptionProfile,
    severity: float,
    *,
    bias_x: float | None = None,
) -> PerceptionProfile:
    """Scale an abstract perception stress profile without mutating PROFILES.

    Severity scales position/velocity noise and dropout probability. Persistent
    lateral bias is scaled unless an explicit bias is supplied. Confidence is
    reduced only for severity above 1.0, which intentionally leaves some
    calibration mismatch for robustness testing.
    """

    if severity <= 0:
        raise ValueError("severity must be > 0")

    conf = base.confidence_scale
    if severity > 1.0:
        conf = max(0.20, conf / np.sqrt(severity))

    return PerceptionProfile(
        sigma_x=float(base.sigma_x * severity),
        sigma_z=float(base.sigma_z * severity),
        sigma_vx=float(base.sigma_vx * severity),
        sigma_vz=float(base.sigma_vz * severity),
        dropout_prob=float(np.clip(base.dropout_prob * severity, 0.0, 0.85)),
        bias_x=float(base.bias_x * severity if bias_x is None else bias_x),
        confidence_scale=float(np.clip(conf, 0.20, 1.0)),
    )


def degradation_scenarios() -> list[RobustnessScenario]:
    base = PROFILES["mixed"]
    ref = ReferenceEstimatorConfig()
    levels = (0.60, 0.80, 1.00, 1.20, 1.40, 1.60)
    return [
        RobustnessScenario(
            name=f"mixed_severity_{level:.2f}",
            axis="degradation_strength",
            description=f"Mixed perception stress scaled to {level:.2f}x the frozen profile.",
            perception_profile=scale_perception(base, level),
            reference_config=ref,
            level=level,
        )
        for level in levels
    ]


def reference_quality_scenarios() -> list[RobustnessScenario]:
    perception = PROFILES["mixed"]
    nominal = ReferenceEstimatorConfig()
    specs = (
        ("nominal", 1.0, 5),
        ("weaker_1", 1.5, 7),
        ("weaker_2", 2.0, 10),
        ("weaker_3", 3.0, 15),
    )
    scenarios: list[RobustnessScenario] = []
    for name, noise_mult, update_steps in specs:
        cfg = replace(
            nominal,
            update_every_steps=update_steps,
            sigma_x=nominal.sigma_x * noise_mult,
            sigma_z=nominal.sigma_z * noise_mult,
            sigma_vx=nominal.sigma_vx * noise_mult,
            sigma_vz=nominal.sigma_vz * noise_mult,
            max_sigma_pos=max(nominal.max_sigma_pos, 1.8 * noise_mult),
        )
        scenarios.append(RobustnessScenario(
            name=f"reference_{name}",
            axis="reference_quality",
            description=(
                f"Reference estimator noise {noise_mult:.1f}x nominal with one update "
                f"every {update_steps} simulation steps."
            ),
            perception_profile=perception,
            reference_config=cfg,
            level=name,
        ))
    return scenarios


def reference_dropout_scenarios() -> list[RobustnessScenario]:
    perception = PROFILES["mixed"]
    nominal = ReferenceEstimatorConfig()
    levels = (0.00, 0.12, 0.25, 0.40, 0.60, 0.75)
    return [
        RobustnessScenario(
            name=f"reference_dropout_{level:.2f}",
            axis="reference_dropout",
            description=f"Reference update dropout probability set to {level:.2f}.",
            perception_profile=perception,
            reference_config=replace(nominal, dropout_prob=level),
            level=level,
        )
        for level in levels
    ]


def bias_magnitude_scenarios() -> list[RobustnessScenario]:
    base = PROFILES["mixed"]
    ref = ReferenceEstimatorConfig()
    levels = (0.00, 0.20, 0.40, 0.62, 0.80, 1.00, 1.20)
    return [
        RobustnessScenario(
            name=f"persistent_bias_{bias:.2f}m",
            axis="bias_magnitude",
            description=(
                f"Mixed-profile noise/dropout held fixed while persistent lateral bias "
                f"is set to {bias:.2f} m."
            ),
            perception_profile=replace(base, bias_x=bias),
            reference_config=ref,
            level=bias,
        )
        for bias in levels
    ]


def seed_family_scenarios() -> list[RobustnessScenario]:
    """Profiles used for multi-family seed generalization tests."""

    ref = ReferenceEstimatorConfig()
    return [
        RobustnessScenario(
            name="seed_family_mixed",
            axis="seed_families",
            description="Frozen mixed profile evaluated across multiple unseen seed families.",
            perception_profile=PROFILES["mixed"],
            reference_config=ref,
            level="mixed",
        ),
        RobustnessScenario(
            name="seed_family_occlusion",
            axis="seed_families",
            description="Frozen occlusion profile evaluated across multiple unseen seed families.",
            perception_profile=PROFILES["occlusion"],
            reference_config=ref,
            level="occlusion",
        ),
    ]


SCENARIO_BUILDERS = {
    "degradation_strength": degradation_scenarios,
    "reference_quality": reference_quality_scenarios,
    "reference_dropout": reference_dropout_scenarios,
    "bias_magnitude": bias_magnitude_scenarios,
    "seed_families": seed_family_scenarios,
}


def get_scenarios(axis: str) -> list[RobustnessScenario]:
    if axis not in SCENARIO_BUILDERS:
        raise ValueError(f"Unknown robustness axis: {axis}")
    return SCENARIO_BUILDERS[axis]()


def all_nonseed_scenarios() -> Iterable[RobustnessScenario]:
    for axis in ("degradation_strength", "reference_quality", "reference_dropout", "bias_magnitude"):
        yield from get_scenarios(axis)
