"""Gaussian copula generator for mixed continuous + binary data with missingness.

The fit step records:
  * per-column missingness rate (independent Bernoulli at sample time);
  * per-column marginal — Bernoulli probability for binary, empirical quantile
    function for continuous;
  * a Spearman-rank correlation matrix on conditionally-non-missing pairs,
    projected to the nearest positive semi-definite matrix.

The sample step draws from a centered multivariate normal with that correlation,
maps to U(0,1) via the standard-normal CDF, then inverts each marginal.
Continuous columns are reconstructed via empirical-quantile interpolation;
binary columns by thresholding at (1 - p).
"""
from __future__ import annotations

import pickle
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm


def _nearest_psd(matrix: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    """Eigenvalue clipping to obtain a PSD correlation matrix."""
    sym = (matrix + matrix.T) / 2.0
    eigvals, eigvecs = np.linalg.eigh(sym)
    eigvals = np.clip(eigvals, eps, None)
    rebuilt = (eigvecs * eigvals) @ eigvecs.T
    d = np.sqrt(np.clip(np.diag(rebuilt), eps, None))
    return rebuilt / np.outer(d, d)


@dataclass
class CopulaModel:
    columns: list[str]
    binary_cols: set[str]
    p_missing: dict[str, float]
    binary_p: dict[str, float]
    continuous_quantiles: dict[str, np.ndarray]  # sorted observed values
    correlation: np.ndarray
    n_train: int = 0
    cohort: str = "unknown"
    extras: dict = field(default_factory=dict)


class GaussianCopulaGenerator:
    def __init__(self, random_seed: int = 42) -> None:
        self.random_seed = random_seed
        self.model: CopulaModel | None = None

    def fit(
        self,
        df: pd.DataFrame,
        binary_cols: list[str],
        continuous_cols: list[str],
        cohort: str = "unknown",
    ) -> "GaussianCopulaGenerator":
        columns = binary_cols + continuous_cols
        p_missing = {c: float(df[c].isna().mean()) for c in columns}

        binary_p = {}
        for c in binary_cols:
            obs = df[c].dropna()
            binary_p[c] = float(obs.mean()) if len(obs) else 0.0

        continuous_quantiles = {}
        for c in continuous_cols:
            obs = df[c].dropna().to_numpy()
            obs = obs[np.isfinite(obs)]
            if len(obs) == 0:
                obs = np.array([0.0])
            continuous_quantiles[c] = np.sort(obs)

        # Spearman rank correlation handles non-linear monotonic relationships
        # and is invariant to the marginal transforms.
        spearman = df[columns].corr(method="spearman").to_numpy()
        spearman = np.where(np.isfinite(spearman), spearman, 0.0)
        np.fill_diagonal(spearman, 1.0)
        # Convert Spearman ρ to Gaussian copula parameter via 2*sin(πρ/6).
        gaussian_rho = 2.0 * np.sin(np.pi * spearman / 6.0)
        np.fill_diagonal(gaussian_rho, 1.0)
        correlation = _nearest_psd(gaussian_rho)

        self.model = CopulaModel(
            columns=columns,
            binary_cols=set(binary_cols),
            p_missing=p_missing,
            binary_p=binary_p,
            continuous_quantiles=continuous_quantiles,
            correlation=correlation,
            n_train=len(df),
            cohort=cohort,
        )
        return self

    def sample(self, n: int) -> pd.DataFrame:
        if self.model is None:
            raise RuntimeError("call fit() before sample()")
        m = self.model
        rng = np.random.default_rng(self.random_seed)

        # Cholesky factor of correlation matrix (already PSD).
        L = np.linalg.cholesky(m.correlation + 1e-10 * np.eye(len(m.columns)))
        z = rng.standard_normal((n, len(m.columns))) @ L.T
        u = norm.cdf(z)

        out = {}
        for i, col in enumerate(m.columns):
            if col in m.binary_cols:
                p = m.binary_p[col]
                out[col] = (u[:, i] < p).astype(np.int8)
            else:
                q = m.continuous_quantiles[col]
                # Empirical-quantile inverse via interpolation on the order
                # statistics of the training values.
                idx = u[:, i] * (len(q) - 1)
                lo = np.floor(idx).astype(int)
                hi = np.minimum(lo + 1, len(q) - 1)
                frac = idx - lo
                out[col] = q[lo] * (1 - frac) + q[hi] * frac

        df = pd.DataFrame(out)
        # Apply column-wise missingness independently.
        for col in m.columns:
            p = m.p_missing[col]
            if p > 0:
                mask = rng.random(n) < p
                df.loc[mask, col] = np.nan

        # Cast count-like continuous to integers (drugs, counts, age).
        int_cast = {
            "age", "n_drugs", "n_medications", "drug_class_count",
            "charlson_cci", "comorbidity_count", "n_ep_labs_available_x",
            "keyword_total_flags", "platelets_latest", "wbc_latest",
        }
        for c in int_cast & set(df.columns):
            df[c] = df[c].round().astype("Int64")
        return df

    # --- persistence ------------------------------------------------------
    def save(self, path: str | Path) -> None:
        if self.model is None:
            raise RuntimeError("nothing to save: call fit() first")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"model": self.model, "seed": self.random_seed}, f)

    @classmethod
    def load(cls, path: str | Path) -> "GaussianCopulaGenerator":
        with open(path, "rb") as f:
            blob = pickle.load(f)
        gen = cls(random_seed=blob["seed"])
        gen.model = blob["model"]
        return gen
