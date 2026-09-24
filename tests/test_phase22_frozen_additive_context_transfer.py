from __future__ import annotations

import numpy as np

from scripts import run_phase22_frozen_additive_context_transfer as p22


def _synthetic_model():
    return {
        "intercept": 0.04,
        "main_effects": {
            "edge": -0.010,
            "oblique": -0.012,
            "dim": -0.008,
            "blur_noise": -0.009,
            "low_contrast": -0.011,
        },
    }


def test_phase22_evidence_partitions_are_fresh_and_disjoint():
    roles = [p22.FIT_FAMILIES, *p22.STAGE_FAMILIES.values()]
    flat = [family for role in roles for family in role]
    assert len(flat) == len(set(flat)) == 120
    assert p22.FIT_FAMILIES == tuple(range(2313, 2337))
    assert p22.STAGE_FAMILIES["dev"] == tuple(range(2337, 2361))
    assert p22.STAGE_FAMILIES["transfer"] == tuple(range(2361, 2385))
    assert p22.STAGE_FAMILIES["validation"] == tuple(range(2385, 2409))
    assert p22.STAGE_FAMILIES["final"] == tuple(range(2409, 2433))
    assert p22.FIT_SEED == 2222220
    assert p22.STAGE_SEEDS == {
        "dev": 2222221,
        "transfer": 2222222,
        "validation": 2222223,
        "final": 2222224,
    }


def test_additive_prediction_uses_only_intercept_and_five_main_effects():
    model = _synthetic_model()
    empty = frozenset()
    full = frozenset(p22.FACTORS)
    expected_empty = model["intercept"] - sum(model["main_effects"].values())
    expected_full = model["intercept"] + sum(model["main_effects"].values())
    assert np.isclose(p22._predict(model, empty), expected_empty)
    assert np.isclose(p22._predict(model, full), expected_full)
    assert set(model) == {"intercept", "main_effects"}
    assert set(model["main_effects"]) == set(p22.FACTORS)


def test_prediction_metrics_are_exact_for_exact_additive_surface():
    model = _synthetic_model()
    observed = {
        subset: p22._predict(model, subset)
        for subset in p22.p21.p20._all_subsets()
    }
    metrics = p22._prediction_metrics(observed, model)
    assert np.isclose(metrics["r2"], 1.0)
    assert np.isclose(metrics["prediction_advantage_mae"], 0.0)
    assert np.isclose(metrics["prediction_advantage_rmse"], 0.0)
    assert np.isclose(metrics["attenuation_abs_error"], 0.0)
    assert metrics["eligible_stable_sign_cells"] >= 10
    assert np.isclose(metrics["stable_sign_accuracy"], 1.0)
    assert len(metrics["predictions"]) == 32


def test_phase22_thresholds_and_claim_boundary_are_locked():
    assert p22.THRESHOLDS["prediction_r2_min"] == 0.65
    assert p22.THRESHOLDS["prediction_advantage_mae_max"] == 0.025
    assert p22.THRESHOLDS["stable_sign_margin"] == 0.02
    assert p22.THRESHOLDS["stable_sign_accuracy_min"] == 0.90
    assert p22.THRESHOLDS["attenuation_abs_error_max"] == 0.07
    assert p22.FROZEN_PHASE21_FINAL_RESULT_SHA256 == "bc85a746cf1b770fb4119feb3979789975ed5201065d94de47c6dcc3a051d9ee"


def test_fit_model_extractor_keeps_no_interactions():
    spectrum = {
        "grand_mean": 0.03,
        "first_order_coefficients": {factor: -0.01 for factor in p22.FACTORS},
        "coefficients": {
            "none": 0.03,
            "edge": -0.01,
            "edge+oblique": 0.50,
        },
    }
    model = p22._model_from_spectrum(spectrum)
    assert model == {
        "intercept": 0.03,
        "main_effects": {factor: -0.01 for factor in p22.FACTORS},
    }
    assert "coefficients" not in model
