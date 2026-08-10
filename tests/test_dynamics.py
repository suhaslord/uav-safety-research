from uav_safety.config import SimConfig
from uav_safety.dynamics import State, step_dynamics


def test_zero_command_keeps_state_near_stationary():
    cfg = SimConfig(drag=0.0)
    state = State(x=1.0, z=2.0, vx=0.0, vz=0.0)
    nxt = step_dynamics(state, 0.0, 0.0, 0.0, 0.0, cfg)
    assert nxt.x == 1.0
    assert nxt.z == 2.0


def test_altitude_never_becomes_negative():
    cfg = SimConfig()
    state = State(x=0.0, z=0.01, vx=0.0, vz=-2.0)
    nxt = step_dynamics(state, 0.0, 0.0, 0.0, 0.0, cfg)
    assert nxt.z >= 0.0
