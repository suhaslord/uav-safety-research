from __future__ import annotations

import numpy as np

from uav_safety.simulator_phase7 import _phase7_image_rng


def test_frame_indexed_camera_rng_is_independent_of_previous_frame_draw_count():
    seed = 4242

    previous_a = _phase7_image_rng(seed, 7)
    previous_a.normal(size=5000)
    frame_a = _phase7_image_rng(seed, 8).normal(size=32)

    previous_b = _phase7_image_rng(seed, 7)
    previous_b.normal(size=3)
    frame_b = _phase7_image_rng(seed, 8).normal(size=32)

    np.testing.assert_array_equal(frame_a, frame_b)


def test_different_frame_indices_get_different_camera_streams():
    a = _phase7_image_rng(4242, 8).normal(size=16)
    b = _phase7_image_rng(4242, 9).normal(size=16)
    assert not np.array_equal(a, b)
