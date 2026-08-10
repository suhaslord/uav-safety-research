import numpy as np

from uav_safety.perception import Observation
from uav_safety.phase6_velocity import RobustImageVelocityFilter


def obs(x: float, *, dropped: bool = False, vx: float = 0.0) -> Observation:
    return Observation(
        x=x,
        z=2.0,
        vx=vx,
        vz=-0.5,
        confidence=0.9 if not dropped else 0.25,
        sigma_pos=0.18 if not dropped else 0.9,
        dropped=dropped,
    )


def test_robust_velocity_rejects_single_position_outlier():
    filt = RobustImageVelocityFilter()
    values = [0.0, 0.0, 0.01, 0.0, 0.95, 0.01, 0.0, -0.01, 0.0]
    last = None
    diag = None
    for value in values:
        last, diag = filt.update(obs(value))

    assert last is not None and diag is not None
    assert abs(last.vx) < 0.40
    assert abs(diag.robust_vx) < 0.25


def test_robust_velocity_tracks_smooth_positive_motion():
    filt = RobustImageVelocityFilter()
    dt = filt.cfg.dt
    target_vx = 0.50
    last = None
    for k in range(28):
        x = target_vx * (k * dt)
        last, _ = filt.update(obs(x))

    assert last is not None
    assert 0.35 < last.vx < 0.62


def test_dropped_frame_does_not_create_velocity_spike():
    filt = RobustImageVelocityFilter()
    last = None
    for k in range(12):
        last, _ = filt.update(obs(0.20 * k * filt.cfg.dt))

    assert last is not None
    before = last.vx
    dropped, diag = filt.update(obs(4.0, dropped=True, vx=2.5))

    assert dropped.dropped
    assert not diag.updated
    assert abs(dropped.vx) <= abs(before) + 1e-9
    assert abs(dropped.vx) < 0.50


def test_velocity_filter_is_deterministic():
    a = RobustImageVelocityFilter()
    b = RobustImageVelocityFilter()
    rng = np.random.default_rng(123)
    sequence = np.cumsum(rng.normal(0.01, 0.025, size=30))

    for value in sequence:
        oa, da = a.update(obs(float(value)))
        ob, db = b.update(obs(float(value)))
        assert oa == ob
        assert np.isclose(da.robust_vx, db.robust_vx)
        assert np.isclose(da.stabilized_vx, db.stabilized_vx)
