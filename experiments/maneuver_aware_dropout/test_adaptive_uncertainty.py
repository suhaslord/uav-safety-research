#!/usr/bin/env python3
"""Unit tests for maneuver-aware adaptive uncertainty analysis."""

import numpy as np
import pytest
from pathlib import Path
import tempfile
import csv

from analyze_adaptive_uncertainty import (
    load_baseline,
    detect_maneuvers_from_acceleration,
    CVKalman2D,
    run_filter,
)


def create_synthetic_baseline(path: Path, n_samples: int = 100):
    """Create synthetic trajectory for testing."""
    t = np.linspace(0, 10, n_samples)
    
    # Simple trajectory: forward then turn
    xy = np.zeros((n_samples, 2))
    vxy = np.zeros((n_samples, 2))
    
    for i, ti in enumerate(t):
        if ti < 5:
            # Forward motion
            xy[i] = [ti * 0.2, 0]
            vxy[i] = [0.2, 0]
        else:
            # Turn
            angle = (ti - 5) * 0.3
            xy[i] = [1.0 + 0.3 * np.cos(angle), 0.3 * np.sin(angle)]
            vxy[i] = [-0.3 * np.sin(angle) * 0.3, 0.3 * np.cos(angle) * 0.3]
    
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=[
            "time_s", "x_m", "y_m", "z_m", "vx_global_mps", "vy_global_mps"
        ])
        writer.writeheader()
        for i in range(n_samples):
            writer.writerow({
                "time_s": t[i],
                "x_m": xy[i, 0],
                "y_m": xy[i, 1],
                "z_m": 1.0,
                "vx_global_mps": vxy[i, 0],
                "vy_global_mps": vxy[i, 1],
            })
    
    return t, xy, vxy


def test_load_baseline():
    """Test baseline loading from CSV."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.csv"
        t_true, xy_true, vxy_true = create_synthetic_baseline(path)
        
        baseline = load_baseline(path)
        
        assert len(baseline.t) == len(t_true)
        assert baseline.xy.shape == xy_true.shape
        assert baseline.vxy.shape == vxy_true.shape
        assert np.allclose(baseline.t, t_true)


def test_maneuver_detection():
    """Test maneuver detection from acceleration."""
    n = 100
    t = np.linspace(0, 10, n)
    
    # Constant velocity: low maneuver score
    vxy_const = np.tile([0.2, 0], (n, 1))
    score_const = detect_maneuvers_from_acceleration(t, vxy_const)
    assert np.max(score_const) < 0.3, "Constant velocity should have low maneuver score"
    
    # Step change in velocity: high maneuver score
    vxy_step = np.zeros((n, 2))
    vxy_step[:50] = [0.2, 0]
    vxy_step[50:] = [0, 0.2]
    score_step = detect_maneuvers_from_acceleration(t, vxy_step)
    assert np.max(score_step) > 0.5, "Step change should have high maneuver score near transition"


def test_kalman_filter_nominal():
    """Test frozen CV Kalman filter on nominal trajectory."""
    t = np.linspace(0, 5, 100)
    truth = np.column_stack([t * 0.1, np.zeros(len(t))])
    
    # No dropout
    measurements = truth.copy()
    result = run_filter(t, truth, measurements, maneuver_score=None)
    
    assert result["est"].shape == truth.shape
    assert np.max(result["error"]) < 0.05, "Nominal error should be small"
    assert len(result["sigma"]) == len(t)


def test_kalman_filter_dropout():
    """Test filter behavior during dropout."""
    t = np.linspace(0, 5, 100)
    truth = np.column_stack([t * 0.1, np.zeros(len(t))])
    
    # Dropout in middle
    measurements = truth.copy()
    measurements[40:60] = np.nan
    
    result = run_filter(t, truth, measurements, maneuver_score=None)
    
    # Sigma should grow during dropout
    sigma_start = result["sigma"][39]  # Just before dropout
    sigma_end = result["sigma"][59]    # End of dropout
    assert sigma_end > sigma_start, "Uncertainty should grow during dropout"
    
    # Error can vary but sigma should increase
    assert np.max(result["sigma"][40:60]) > np.mean(result["sigma"][:40]), \
        "Max sigma during dropout should exceed mean before dropout"


def test_adaptive_vs_baseline():
    """Test that adaptive filter produces different uncertainty than baseline."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.csv"
        t, truth, vxy = create_synthetic_baseline(path)
        
        # Dropout during turn
        measurements = truth.copy()
        measurements[60:80] = np.nan
        
        # Detect maneuvers
        maneuver_score = detect_maneuvers_from_acceleration(t, vxy)
        
        # Run both filters
        baseline_result = run_filter(t, truth, measurements, maneuver_score=None)
        adaptive_result = run_filter(t, truth, measurements, maneuver_score=maneuver_score)
        
        # Adaptive should have higher uncertainty during/after turn
        baseline_sigma_turn = np.max(baseline_result["sigma"][60:80])
        adaptive_sigma_turn = np.max(adaptive_result["sigma"][60:80])
        
        assert adaptive_sigma_turn > baseline_sigma_turn, \
            "Adaptive filter should produce higher uncertainty during maneuvers"


def test_filter_covariance_positive_definite():
    """Test that filter covariance remains positive definite."""
    t = np.linspace(0, 5, 50)
    truth = np.column_stack([t * 0.1, np.zeros(len(t))])
    measurements = truth.copy()
    measurements[20:30] = np.nan
    
    kf = CVKalman2D(measurements[0])
    
    for i in range(1, len(t)):
        dt = t[i] - t[i-1]
        z = measurements[i] if np.isfinite(measurements[i]).all() else None
        _, sigma = kf.step(dt, z, q_scale=5.0)
        
        # Check covariance eigenvalues are positive
        eigvals = np.linalg.eigvalsh(kf.P)
        assert np.all(eigvals > 0), f"Covariance not positive definite at step {i}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
