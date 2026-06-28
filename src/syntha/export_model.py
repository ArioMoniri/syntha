"""Export a trained copula model to a compact JSON the Tauri app consumes.

We downsample each continuous marginal to ``n_quantiles`` order statistics to
keep the JSON small (≈100 KB for the tolerant cohort at 200 quantiles), then
serialize the correlation matrix and binary marginals verbatim.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from . import schema
from .generator.copula import CopulaModel, GaussianCopulaGenerator


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
    date_lo: str | None = None,
    date_hi: str | None = None,
) -> Path:
    """Export the fitted copula to v2 JSON.

    v2 adds:
      * ``date_lo`` / ``date_hi`` — ISO-8601 strings used by the desktop app
        to synthesize ``episode_date`` values without needing the source CSV.
      * ``curation_columns`` — names that the desktop app should drop from
        the default CSV output (single source of truth, lives in schema.py).

    v1 readers are unaffected: the new fields are additive and the desktop
    bundle falls back to a reasonable default when they are absent.
    """
    if gen.model is None:
        raise RuntimeError("generator has no fitted model")
    m = gen.model
    payload = {
        "format": "syntha-copula-v2",
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
        "date_lo": date_lo or "2015-01-01",
        "date_hi": date_hi or "2024-12-31",
        "curation_columns": list(schema.CURATION_COLUMNS),
    }
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return out


def load_generator_from_json(
    payload: dict | str | Path,
    random_seed: int = 42,
) -> GaussianCopulaGenerator:
    """Reconstruct a :class:`GaussianCopulaGenerator` directly from a v1/v2 JSON.

    Lets callers (MCP server, downstream consumers) sample from the bundled
    model JSONs without a ModelRegistry or the source CSV. Accepts:

    * a ``dict`` already parsed from JSON,
    * a path-like to a JSON file,
    * a string containing JSON text.
    """
    if isinstance(payload, (str, Path)):
        p = Path(payload)
        if p.exists():
            payload = json.loads(p.read_text(encoding="utf-8"))
        elif isinstance(payload, str) and payload.lstrip().startswith("{"):
            payload = json.loads(payload)
        else:
            raise FileNotFoundError(f"model JSON not found: {payload!r}")
    fmt = payload.get("format", "")
    if not fmt.startswith("syntha-copula-v"):
        raise ValueError(f"unknown model JSON format: {fmt!r}")

    columns = list(payload["columns"])
    binary_cols = set(payload["binary_cols"])
    p_missing = {c: float(v) for c, v in payload.get("p_missing", {}).items()}
    binary_p = {c: float(v) for c, v in payload.get("binary_p", {}).items()}
    continuous_quantiles = {
        c: np.asarray(q, dtype=float) for c, q in payload.get("continuous_quantiles", {}).items()
    }
    correlation = np.asarray(payload["correlation"], dtype=float)
    model = CopulaModel(
        columns=columns,
        binary_cols=binary_cols,
        p_missing=p_missing,
        binary_p=binary_p,
        continuous_quantiles=continuous_quantiles,
        correlation=correlation,
        n_train=int(payload.get("n_train", 0)),
        cohort=str(payload.get("cohort", "unknown")),
        extras={
            "format": fmt,
            "date_lo": payload.get("date_lo"),
            "date_hi": payload.get("date_hi"),
            "curation_columns": list(payload.get("curation_columns", [])),
        },
    )
    gen = GaussianCopulaGenerator(random_seed=random_seed)
    gen.model = model
    return gen
