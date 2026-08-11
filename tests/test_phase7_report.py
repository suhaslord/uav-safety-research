from __future__ import annotations

import pytest

from scripts.render_phase7_report import render_report


def _bundle() -> dict:
    return {
        "schema": "aegisland.phase7.dashboard-bundle.v1",
        "metadata": {
            "run_role": "development_external_validity_factorial",
            "git_sha": "abc123",
            "episode_seed": 979797,
            "episode_seed_status": "development_seen",
            "episodes_per_condition_fault_plant": 5,
            "image_rng_model": "frame_indexed_v1",
            "sensor_transport_model": "scheduled_delivery_queue_v1",
            "sensor_rng_model": "channel_isolated_time_indexed_v1",
            "reference_lateral_freshness_model": "gnss_delivery_only_v1",
            "component_reference_freshness_model": "per_component_delivered_v1",
            "shared_dropout_model": "single_common_event_blackout_v1",
        },
        "summary": [
            {
                "condition": "mixed",
                "fault_scenario": "shared_lateral_bias",
                "plant_model": "phase7",
                "episodes": 5,
                "success_rate": 0.4,
                "success_ci_low": 0.1176,
                "success_ci_high": 0.7693,
                "unsafe_touchdown_rate": 0.6,
                "unsafe_ci_low": 0.2307,
                "unsafe_ci_high": 0.8824,
                "abort_rate": 0.0,
                "mean_shared_dropout_event_rate": 0.0,
                "mean_image_drop_rate": 0.0,
                "mean_reference_available_rate": 0.95,
                "mean_reference_age_steps": 2.4,
            }
        ],
        "paired_plant_effects": [
            {
                "condition": "mixed",
                "fault_scenario": "shared_lateral_bias",
                "paired_episodes": 5,
                "phase7_minus_legacy_success_pp": -20.0,
                "phase7_minus_legacy_unsafe_pp": 20.0,
            }
        ],
    }


def test_report_preserves_development_warning_and_provenance():
    rendered = render_report(_bundle())
    assert "Development evidence only" in rendered
    assert "abc123" in rendered
    assert "979797" in rendered
    assert "frame indexed v1" in rendered
    assert "shared lateral bias" in rendered
    assert "60.0%" in rendered
    assert "+20.0 pp" in rendered


def test_report_escapes_user_supplied_title():
    rendered = render_report(_bundle(), title="<script>alert(1)</script>")
    assert "<script>alert(1)</script>" not in rendered
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered


def test_report_rejects_unknown_bundle_schema():
    bundle = _bundle()
    bundle["schema"] = "wrong"
    with pytest.raises(ValueError, match="unsupported dashboard bundle schema"):
        render_report(bundle)
