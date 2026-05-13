"""Tests for the polyserial + tetrachoric estimators.

Each test constructs a known latent-Gaussian truth, samples (continuous,
binary) or (binary, binary) pairs from it, and verifies the estimator
recovers the truth.
"""
import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm, spearmanr

from syntha.generator.mixed_corr import (
    mixed_correlation_matrix,
    polyserial_correlation,
    spearman_to_gaussian,
    tetrachoric_correlation,
)


def _sample_bivariate_normal(n: int, rho: float, rng: np.random.Generator) -> np.ndarray:
    """Sample n pairs from N(0, [[1, ρ], [ρ, 1]])."""
    z1 = rng.standard_normal(n)
    eps = rng.standard_normal(n)
    z2 = rho * z1 + np.sqrt(max(0.0, 1.0 - rho * rho)) * eps
    return np.column_stack([z1, z2])


# ── Polyserial ────────────────────────────────────────────────
@pytest.mark.parametrize("rho_true", [-0.7, -0.4, 0.0, 0.3, 0.6])
def test_polyserial_recovers_latent_correlation(rho_true):
    """Sample latent (Z1, Z2) bivariate normal; expose Y = some monotonic
    transform of Z1 (continuous) and X = 1{Z2 > τ} (binary at p=0.2).
    Polyserial should recover rho_true regardless of the transform."""
    rng = np.random.default_rng(abs(int(rho_true * 1000)) + 100)
    z = _sample_bivariate_normal(5000, rho_true, rng)
    # Apply a monotonic transform to Z1 to be a "continuous lab".
    y_continuous = np.exp(z[:, 0])  # log-normal shape
    # Threshold Z2 at the 80th percentile so p(X=1) ≈ 0.20.
    x_binary = (z[:, 1] > norm.ppf(0.80)).astype(int)

    rho_hat = polyserial_correlation(y_continuous, x_binary)
    assert abs(rho_hat - rho_true) < 0.07, (
        f"polyserial recovered {rho_hat:.3f}; expected {rho_true:.3f}"
    )


def test_polyserial_strongly_beats_spearman_pipeline_on_binary():
    """The whole point of v0.5.1: on binary↔continuous, polyserial recovers
    a magnitude that the old Spearman→Gaussian pipeline attenuates ~50%."""
    rng = np.random.default_rng(7)
    rho_true = 0.5
    z = _sample_bivariate_normal(10_000, rho_true, rng)
    y = z[:, 0]
    p = 0.10  # rare binary, as comorbidities tend to be
    x = (z[:, 1] > norm.ppf(1.0 - p)).astype(int)

    # OLD path: rank-correlation then Kruskal transform
    rho_s = spearmanr(y, x).correlation
    rho_old = spearman_to_gaussian(rho_s)
    # NEW path: polyserial directly
    rho_new = polyserial_correlation(y, x)

    # The old method should attenuate substantially; the new method should
    # be within ~10% of truth.
    assert abs(rho_old) < 0.40, f"sanity: old method shrunk to {rho_old:.3f}"
    assert abs(rho_new - rho_true) < 0.07, (
        f"polyserial recovered {rho_new:.3f}; expected {rho_true:.3f}"
    )
    # New is materially better than old.
    assert abs(rho_new) > abs(rho_old) + 0.10


def test_polyserial_returns_zero_for_constant_binary():
    rng = np.random.default_rng(1)
    y = rng.standard_normal(500)
    x = np.zeros(500, dtype=int)
    assert polyserial_correlation(y, x) == 0.0


# ── Tetrachoric ───────────────────────────────────────────────
@pytest.mark.parametrize("rho_true", [-0.6, -0.3, 0.0, 0.4, 0.7])
def test_tetrachoric_recovers_latent_correlation(rho_true):
    """Sample latent (Z1, Z2) bivariate normal at known rho. Threshold both
    at the 70th percentile to get rare-event binaries. Estimator should
    recover rho_true."""
    rng = np.random.default_rng(abs(int(rho_true * 1000)) + 50)
    z = _sample_bivariate_normal(10_000, rho_true, rng)
    x = (z[:, 0] > norm.ppf(0.70)).astype(int)
    y = (z[:, 1] > norm.ppf(0.70)).astype(int)
    rho_hat = tetrachoric_correlation(x, y)
    assert abs(rho_hat - rho_true) < 0.08, (
        f"tetrachoric recovered {rho_hat:.3f}; expected {rho_true:.3f}"
    )


def test_tetrachoric_strongly_beats_spearman_pipeline_on_binary_binary():
    rng = np.random.default_rng(11)
    rho_true = 0.55
    z = _sample_bivariate_normal(15_000, rho_true, rng)
    x = (z[:, 0] > norm.ppf(0.90)).astype(int)  # 10% prevalence
    y = (z[:, 1] > norm.ppf(0.90)).astype(int)

    rho_s = spearmanr(x, y).correlation
    rho_old = spearman_to_gaussian(rho_s)
    rho_new = tetrachoric_correlation(x, y)

    assert abs(rho_old) < 0.35, f"sanity: old method shrunk to {rho_old:.3f}"
    assert abs(rho_new - rho_true) < 0.10, (
        f"tetrachoric recovered {rho_new:.3f}; expected {rho_true:.3f}"
    )


# ── Mixed matrix dispatch ─────────────────────────────────────
def test_mixed_correlation_matrix_uses_right_estimator_per_pair():
    rng = np.random.default_rng(42)
    n = 4000
    # Build a 3-variable latent system: 2 continuous + 1 binary.
    # Truth: cont1 ↔ cont2 ρ=0.6, cont1 ↔ bin ρ=0.4, cont2 ↔ bin ρ=0.0
    z1 = rng.standard_normal(n)
    z2 = 0.6 * z1 + np.sqrt(1 - 0.36) * rng.standard_normal(n)
    # Build the binary via a third latent with target correlations.
    eps_b = rng.standard_normal(n)
    z_b = 0.4 * z1 + np.sqrt(1 - 0.16) * eps_b  # ρ(cont1, b) = 0.4
    b = (z_b > norm.ppf(0.80)).astype(int)

    # cont2: monotonic transform of z2 so the rank correlation with cont1
    # is preserved (z2 ** 2 would be non-monotonic and destroy it).
    df = pd.DataFrame({"cont1": np.exp(z1), "cont2": 3 * z2 + 10, "bin1": b})
    C = mixed_correlation_matrix(
        df, binary_cols={"bin1"}, continuous_cols={"cont1", "cont2"},
    )
    assert C.shape == (3, 3)
    assert np.allclose(np.diag(C), 1.0)
    # cont1 ↔ cont2: Spearman→Gaussian recovers ~0.6
    assert abs(C[0, 1] - 0.6) < 0.05
    # cont1 ↔ bin1: polyserial should recover ~0.4
    assert 0.30 < C[0, 2] < 0.50
