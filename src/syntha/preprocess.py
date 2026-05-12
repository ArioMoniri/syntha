"""Light preprocessing: coerce types, record missingness, optionally clip outliers."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import schema


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in schema.binary_columns():
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    for col in schema.continuous_columns():
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def clip_to_physiologic(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col, (lo, hi) in schema.PHYSIOLOGIC_BOUNDS.items():
        if col in out.columns:
            out[col] = out[col].clip(lower=lo, upper=hi)
    return out


def missingness(df: pd.DataFrame) -> dict[str, float]:
    return {c: float(df[c].isna().mean()) for c in df.columns}


def split_modeled(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Return (modeled_df, binary_cols, continuous_cols) restricted to present columns."""
    bcols = [c for c in schema.binary_columns() if c in df.columns]
    ccols = [c for c in schema.continuous_columns() if c in df.columns]
    return df[bcols + ccols].copy(), bcols, ccols
