"""CSV loader for pristine-episode source files."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import schema


def load_episodes(path: str | Path) -> pd.DataFrame:
    """Read a pristine-episodes CSV. Handles BOM-prefixed first column."""
    df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    df.columns = [c.lstrip("﻿").strip() for c in df.columns]
    return df


def filter_to_modeled(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only the columns we know how to model. Unknown columns are dropped."""
    keep = [c for c in schema.all_modeled_columns() if c in df.columns]
    return df[keep].copy()


def date_range(df: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp]:
    if "episode_date" not in df.columns:
        return pd.Timestamp("2015-01-01"), pd.Timestamp("2024-12-31")
    s = pd.to_datetime(df["episode_date"], errors="coerce").dropna()
    if s.empty:
        return pd.Timestamp("2015-01-01"), pd.Timestamp("2024-12-31")
    return s.min(), s.max()
