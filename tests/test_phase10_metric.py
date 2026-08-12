from __future__ import annotations

from uav_safety.phase10_metric import AegisT10, MetricFrame, Phase10MetricConfig


def frame(index, t, *, obs=True, x=0.0, z=2.0, kind="aruco", area=20000.0):
    return MetricFrame(t_s=t, frame_index=index, observation_available=obs, observed_lateral_x_m=x if obs else None, observed_altitude_m=z if obs else None, detector_kind=kind if obs else None, reprojection_rms_px=0.2 if obs else None, detected_area_px2=area if obs else None)


def test_aruco_initializes_and_updates_causally():
    model=AegisT10(); first=model.update(frame(0,0.0,x=.2,z=2.0)); second=model.update(frame(1,.3,x=.4,z=1.9)); assert first.metric_estimate_available; assert first.fresh_geometry_update; assert first.source=="aruco_update"; assert second.lateral_x_m==.4; assert second.altitude_m==1.9; assert second.lateral_velocity_mps>0


def test_gross_quad_is_rejected_but_prediction_is_explicit():
    model=AegisT10(); model.update(frame(0,0.0,x=0,z=2)); model.update(frame(1,.3,x=.3,z=2)); out=model.update(frame(2,.6,x=6,z=9,kind="quad_fallback",area=1500)); assert out.metric_estimate_available; assert not out.fresh_geometry_update; assert out.source=="quad_rejected_temporal_prediction"; assert abs(out.lateral_x_m)<2; assert out.altitude_m<4


def test_missing_front_end_observation_does_not_claim_metric_output():
    model=AegisT10(); model.update(frame(0,0)); out=model.update(frame(1,.3,obs=False)); assert not out.front_end_observation_available; assert not out.metric_estimate_available; assert out.source=="no_front_end_observation"


def test_first_quad_is_retained_as_untrusted_bootstrap():
    model=AegisT10(); out=model.update(frame(0,0,x=-1,z=1.2,kind="quad_fallback",area=30000)); assert out.metric_estimate_available; assert not out.fresh_geometry_update; assert out.source=="quad_bootstrap_untrusted"


def test_unknown_observation_kind_fails_closed():
    model=AegisT10(); out=model.update(frame(0,0,kind="mystery")); assert not out.metric_estimate_available; assert out.source=="unsupported_observation_kind"


def test_default_config_is_stable():
    cfg=Phase10MetricConfig(); assert cfg.beta_lateral==.65; assert cfg.beta_altitude==.15; assert cfg.quad_max_lateral_innovation_m==.75
