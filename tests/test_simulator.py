from uav_safety.simulator import run_episode


def test_episode_is_reproducible():
    a = run_episode(seed=1234, profile="clean", supervised=False)
    b = run_episode(seed=1234, profile="clean", supervised=False)
    assert a.to_dict() == b.to_dict()


def test_supervised_episode_records_risk():
    result = run_episode(seed=9, profile="mixed", supervised=True)
    assert 0.0 <= result.max_risk <= 1.0
    assert result.interventions >= 0
