"""Export a trained copula model to a compact JSON the Tauri app consumes.

We downsample each continuous marginal to ``n_quantiles`` order statistics to
keep the JSON small (≈100 KB for the tolerant cohort at 200 quantiles), then
serialize the correlation matrix and binary marginals verbatim.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .generator.copula import GaussianCopulaGenerator


def _quantile_grid(values: np.ndarray, n: int) -> list[float]:
    if len(values) == 0:
        return [0.0]
    if len(values) <= n:
        return [float(v) for v in np.sort(values)]
    qs = np.linspace(0.0, 1.0, n)
    return [float(v) for v in np.quantile(values, qs)]


def export_model_to_json(
    gen: GaussianCopulaGenerator,
    path: str | Path,
    n_quantiles: int = 200,
) -> Path:
    if gen.model is None:
        raise RuntimeError("generator has no fitted model")
    m = gen.model
    payload = {
        "format": "syntha-copula-v1",
        "cohort": m.cohort,
        "columns": list(m.columns),
        "binary_cols": sorted(m.binary_cols),
        "p_missing": {c: float(v) for c, v in m.p_missing.items()},
        "binary_p": {c: float(v) for c, v in m.binary_p.items()},
        "continuous_quantiles": {
            c: _quantile_grid(q, n_quantiles) for c, q in m.continuous_quantiles.items()
        },
        "correlation": m.correlation.tolist(),
        "n_train": m.n_train,
    }
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return out
