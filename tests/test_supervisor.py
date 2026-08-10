from uav_safety.config import SupervisorConfig
from uav_safety.perception import Observation
from uav_safety.supervisor import Decision, SafetySupervisor


def test_clean_high_confidence_observation_proceeds():
    sup = SafetySupervisor(SupervisorConfig())
    obs = Observation(x=0.05, z=3.0, vx=0.0, vz=-0.3, confidence=0.95, sigma_pos=0.05, dropped=False)
    decision = sup.assess(obs)
    assert decision.decision == Decision.PROCEED


def test_low_confidence_near_ground_aborts():
    sup = SafetySupervisor(SupervisorConfig())
    obs = Observation(x=0.2, z=0.7, vx=0.0, vz=-0.4, confidence=0.08, sigma_pos=0.8, dropped=True)
    decision = sup.assess(obs)
    assert decision.decision == Decision.ABORT
