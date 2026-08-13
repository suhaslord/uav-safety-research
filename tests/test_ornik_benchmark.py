from __future__ import annotations

import numpy as np

from uav_safety.ornik_benchmark_metrics import detection_outcome, recovery_outcome, thrust_effectiveness_to_speed_scale
from uav_safety.ornik_fdi import decide_fault, healthy_label, make_trace_windows, single_fault_label, tolerance_hinge_loss_numpy


def test_paper_threshold_is_strictly_below_point_one():
    assert decide_fault([1.0, 0.099, 1.0, 1.0]).fault_detected
    assert not decide_fault([1.0, 0.1, 1.0, 1.0]).fault_detected


def test_isolation_is_argmin_and_labels_are_single_fault():
    d = decide_fault([0.8, 0.7, 0.02, 0.6]); assert d.isolated_motor == 2
    assert np.array_equal(healthy_label(), np.ones(4, dtype=np.float32))
    assert np.array_equal(single_fault_label(3), np.array([1,1,1,0], dtype=np.float32))


def test_window_shape_preserves_y_u_history():
    y=np.zeros((105,6),np.float32); u=np.zeros((105,4),np.float32); w,ends=make_trace_windows(y,u,window=100)
    assert w.shape == (6,100,10) and ends[0] == 99 and ends[-1] == 104


def test_hinge_is_zero_inside_epsilon():
    assert tolerance_hinge_loss_numpy(np.array([[1.0,0.01]]),np.array([[1.0,0.0]]),0.02) == 0.0


def test_thrust_effectiveness_maps_to_sqrt_speed_scale():
    assert thrust_effectiveness_to_speed_scale(0.25) == 0.5
    assert thrust_effectiveness_to_speed_scale(1.0) == 1.0


def test_non_recovery_never_gets_fake_time():
    t=np.arange(0.0,4.0,0.1); degraded=t>=1.0; recovery=np.zeros_like(degraded)
    r=recovery_outcome(t,degraded,recovery,onset_s=0.5,dwell_s=0.5)
    assert r['non_recovery'] is True and r['recovery_time_s'] is None


def test_recovery_clock_starts_at_first_degraded_entry():
    t=np.arange(0.0,5.0,0.1); degraded=t>=1.5; recovery=t>=2.5
    r=recovery_outcome(t,degraded,recovery,onset_s=0.5,dwell_s=0.5)
    assert r['recovered'] is True and abs(r['recovery_time_s']-1.0) < 1e-9


def test_undetected_fault_is_false_negative_with_null_latency():
    t=np.array([5.0,5.1,5.2]); scores=np.full((3,4),0.9)
    r=detection_outcome(t,scores,threshold=.1,fault_onset_s=5.0,true_fault_motor=1)
    assert r['false_negative'] is True and r['detection_latency_s'] is None


def test_nominal_detection_is_false_positive():
    t=np.array([1.0,1.1]); scores=np.array([[1,1,1,1],[1,0.01,1,1]],float)
    r=detection_outcome(t,scores,threshold=.1,fault_onset_s=None,true_fault_motor=None)
    assert r['false_positive'] is True
