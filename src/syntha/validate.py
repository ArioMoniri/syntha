"""Synthetic-data validation report.

For each continuous column shared between source and synthetic:
  * Kolmogorov–Smirnov two-sample statistic + p-value
  * Wasserstein-1 distance (in raw column units)
  * Mean/std absolute error

For each binary column:
  * Prevalence absolute error

Across the joint distribution:
  * Frobenius norm of the difference between source and synthetic Spearman
    correlation matrices, on shared columns with sufficient observations.

Output: a structured ``ValidationReport`` plus a JSON-serializable dict
suitable for archiving alongside a generated synthetic CSV.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp, wasserstein_distance


@dataclass
class ContinuousMetric:
    column: str
    n_source: int
    n_synthetic: int
    ks_stat: float
    ks_pvalue: float
    wasserstein: float
    mean_abs_error: float
    std_abs_error: float


@dataclass
class BinaryMetric:
    column: str
    source_prevalence: float
    synthetic_prevalence: float
    abs_error: float


@dataclass
class ValidationReport:
    n_source: int
    n_synthetic: int
    correlation_frobenius: float
    continuous: list[ContinuousMetric] = field(default_factory=list)
    binary: list[BinaryMetric] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "n_source": self.n_source,
            "n_synthetic": self.n_synthetic,
            "correlation_frobenius": self.correlation_frobenius,
            "continuous": [asdict(c) for c in self.continuous],
            "binary": [asdict(b) for b in self.binary],
        }

    def summary(self) -> dict:
        """Compact summary suitable for CI assertions or README badges."""
        ks_max = max((c.ks_stat for c in self.continuous), default=0.0)
        ks_mean = float(np.mean([c.ks_stat for c in self.continuous])) if self.continuous else 0.0
        bin_max = max((b.abs_error for b in self.binary), default=0.0)
        return {
            "n_source": self.n_source,
            "n_synthetic": self.n_synthetic,
            "ks_max": ks_max,
            "ks_mean": ks_mean,
            "binary_max_abs_error": bin_max,
            "correlation_frobenius": self.correlation_frobenius,
        }


def _spearman_diff(a: pd.DataFrame, b: pd.DataFrame, cols: list[str]) -> float:
    ca = a[cols].corr(method="spearman").fillna(0.0).to_numpy()
    cb = b[cols].corr(method="spearman").fillna(0.0).to_numpy()
    return float(np.linalg.norm(ca - cb, ord="fro"))


def validate(
    source: pd.DataFrame,
    synthetic: pd.DataFrame,
    continuous_cols: list[str],
    binary_cols: list[str],
    min_observations: int = 30,
) -> ValidationReport:
    report = ValidationReport(
        n_source=len(source), n_synthetic=len(synthetic),
        correlation_frobenius=0.0,
    )

    usable_cont = []
    for c in continuous_cols:
        if c not in source.columns or c not in synthetic.columns:
            continue
        s = pd.to_numeric(source[c], errors="coerce").dropna().to_numpy()
        t = pd.to_numeric(synthetic[c], errors="coerce").dropna().to_numpy()
        if len(s) < min_observations or len(t) < min_observations:
            continue
        ks = ks_2samp(s, t)
        report.continuous.append(ContinuousMetric(
            column=c, n_source=int(len(s)), n_synthetic=int(len(t)),
            ks_stat=float(ks.statistic), ks_pvalue=float(ks.pvalue),
            wasserstein=float(wasserstein_distance(s, t)),
            mean_abs_error=float(abs(s.mean() - t.mean())),
            std_abs_error=float(abs(s.std() - t.std())),
        ))
        usable_cont.append(c)

    for c in binary_cols:
        if c not in source.columns or c not in synthetic.columns:
            continue
        sp = float(pd.to_numeric(source[c], errors="coerce").dropna().mean())
        tp = float(pd.to_numeric(synthetic[c], errors="coerce").dropna().mean())
        if np.isnan(sp) or np.isnan(tp):
            continue
        report.binary.append(BinaryMetric(
            column=c, source_prevalence=sp,
            synthetic_prevalence=tp, abs_error=abs(sp - tp),
        ))

    if usable_cont:
        report.correlation_frobenius = _spearman_diff(source, synthetic, usable_cont)
    return report


def save_report(report: ValidationReport, path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return out
