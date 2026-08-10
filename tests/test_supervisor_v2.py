from uav_safety.perception import Observation
from uav_safety.supervisor_v2 import (
    DecisionV2,
    SupervisorV2Config,
    TemporalObservationFilter,
    TemporalSafetySupervisorV2,
)


def obs(confidence=0.95, sigma=0.08, dropped=False, z=2.0, x=0.0, vx=0.0, vz=-0.4):
    return Observation(
        x=x,
        z=z,
        vx=vx,
        vz=vz,
        confidence=confidence,
        sigma_pos=sigma,
        dropped=dropped,
    )


def test_single_bad_frame_does_not_abort():
    sup = TemporalSafetySupervisorV2()
    decision = sup.assess(obs(confidence=0.03, sigma=1.5, dropped=True, z=0.5))
    assert decision.decision != DecisionV2.ABORT


def test_persistent_uncertainty_can_enter_hold():
    cfg = SupervisorV2Config(hold_risk=0.40, hold_persistence=3)
    sup = TemporalSafetySupervisorV2(cfg)
    decision = None
    for _ in range(8):
        decision = sup.assess(obs(confidence=0.20, sigma=0.9, x=1.0))
    assert decision is not None
    assert decision.decision == DecisionV2.HOLD


def test_hysteresis_releases_after_clear_streak():
    cfg = SupervisorV2Config(
        hold_risk=0.35,
        release_risk=0.30,
        hold_persistence=2,
        release_persistence=3,
        risk_alpha=1.0,
    )
    sup = TemporalSafetySupervisorV2(cfg)
    for _ in range(4):
        sup.assess(obs(confidence=0.10, sigma=1.0, x=1.2))
    assert sup.state == DecisionV2.HOLD

    decision = None
    for _ in range(4):
        decision = sup.assess(obs(confidence=0.99, sigma=0.02, x=0.0, vx=0.0, vz=-0.2))
    assert decision is not None
    assert decision.decision == DecisionV2.PROCEED


def test_dropout_filter_propagates_instead_of_freezing():
    filt = TemporalObservationFilter(dt=0.1)
    filt.update(obs(x=1.0, vx=2.0))
    filtered = filt.update(obs(x=1.0, vx=2.0, dropped=True))
    assert filtered.x > 1.0
    assert filtered.dropped
