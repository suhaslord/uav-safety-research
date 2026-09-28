from __future__ import annotations

import csv
from math import isclose
from pathlib import Path

from uav_safety.model_vase import MODEL_VASE_NAME, MODEL_VASE_SCHEMA, ModelVase
from uav_safety.perception import Observation
from uav_safety.reference_estimator import ReferenceObservation
from uav_safety.simulator_v3 import run_episode_v3
from uav_safety.supervisor_v3 import (
    RedundantSafetySupervisorV3,
    RedundantStateFusion,
    SupervisorV3Config,
)


ROOT = Path(__file__).resolve().parents[1]


def test_model_vase_is_a_thin_frozen_v3_orchestrator() -> None:
    cfg = SupervisorV3Config()
    vase = ModelVase(cfg)
    reference_fusion = RedundantStateFusion(cfg)
    reference_supervisor = RedundantSafetySupervisorV3(cfg)
    decisions = set()

    for step in range(48):
        raw = Observation(
            x=0.03 * step,
            z=max(0.1, 2.2 - 0.035 * step),
            vx=0.01 * (step % 7),
            vz=-0.34,
            confidence=0.82 if step % 6 else 0.38,
            sigma_pos=0.22 + 0.02 * (step % 5),
            dropped=step % 11 == 0,
        )
        filtered = Observation(
            x=raw.x + 0.025,
            z=raw.z,
            vx=raw.vx,
            vz=raw.vz,
            confidence=max(0.02, raw.confidence - 0.04),
            sigma_pos=raw.sigma_pos + 0.03,
            dropped=raw.dropped,
        )
        age = step % 5
        reference = ReferenceObservation(
            x=raw.x - 0.24,
            z=raw.z + 0.06,
            vx=raw.vx,
            vz=raw.vz,
            sigma_pos=0.42 + age * 0.02,
            fresh=age == 0,
            available=True,
            age_steps=age,
        )

        expected_fusion = reference_fusion.update(raw, filtered, reference)
        expected_decision = reference_supervisor.assess(raw, expected_fusion, reference)
        actual = vase.step(raw, filtered, reference)

        assert actual.fusion == expected_fusion
        assert actual.decision == expected_decision
        decisions.add(actual.decision.decision.value)

    assert decisions <= {"proceed", "hold", "abort"}
    assert vase.name == MODEL_VASE_NAME
    assert vase.schema == MODEL_VASE_SCHEMA


def test_vase_runtime_reproduces_committed_frozen_v3_rows() -> None:
    frozen_path = ROOT / "results/v3_frozen/episodes.csv"
    representatives: dict[str, dict[str, str]] = {}
    with frozen_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["architecture"] == "aegis_v3":
                representatives.setdefault(row["profile"], row)
    assert set(representatives) == {"clean", "blur", "low_light", "occlusion", "mixed"}

    for profile, row in representatives.items():
        actual = run_episode_v3(seed=int(row["seed"]), profile=profile).to_dict()
        for key, value in actual.items():
            frozen = row[key]
            if isinstance(value, bool):
                assert frozen.lower() == str(value).lower(), (profile, key)
            elif isinstance(value, int):
                frozen_number = float(frozen)
                assert frozen_number.is_integer() and int(frozen_number) == value, (profile, key)
            elif isinstance(value, float):
                assert isclose(float(frozen), value, rel_tol=1e-13, abs_tol=1e-13), (profile, key)
            else:
                assert frozen == value, (profile, key)
