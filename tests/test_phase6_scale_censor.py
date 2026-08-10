import numpy as np

from uav_safety.image_temporal import Phase6LandingPadRenderer
from uav_safety.phase6_scale_censor import analyze_scale_censor


def test_near_ground_off_center_marker_is_scale_censored():
    renderer = Phase6LandingPadRenderer()
    frame = renderer.render(
        x_offset_m=1.0,
        altitude_m=0.18,
        rng=np.random.default_rng(1234),
        condition="clean",
        severity=1.0,
    )
    diag = analyze_scale_censor(frame)
    assert diag.scale_censored
    assert diag.border_foreground_pixels >= 10
    assert diag.touched_sides >= 1


def test_mid_altitude_centered_marker_is_not_scale_censored():
    renderer = Phase6LandingPadRenderer()
    frame = renderer.render(
        x_offset_m=0.0,
        altitude_m=2.0,
        rng=np.random.default_rng(1234),
        condition="clean",
        severity=1.0,
    )
    diag = analyze_scale_censor(frame)
    assert not diag.scale_censored
    assert diag.border_foreground_pixels < 10


def test_high_altitude_blur_is_not_field_of_view_censored():
    renderer = Phase6LandingPadRenderer()
    frame = renderer.render(
        x_offset_m=0.4,
        altitude_m=7.5,
        rng=np.random.default_rng(4321),
        condition="blur",
        severity=1.0,
    )
    diag = analyze_scale_censor(frame)
    assert not diag.scale_censored
