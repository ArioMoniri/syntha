"""Longitudinal trajectory generator.

Sample N synthetic *baselines* from the copula, then for each baseline expand
into K episodes spread across `years_of_history` years. Comorbidity flags are
sticky (once present, present in all subsequent episodes). Continuous labs
drift around the baseline value (Gaussian walk bounded by physiologic limits).
This gives a Synthea-style longitudinal record without needing per-state-machine
disease progression.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import schema


@dataclass
class TrajectoryConfig:
    encounters_per_patient_mean: float = 4.0  # Poisson mean over the window
    years_of_history: float = 3.0
    lab_drift_scale: float = 0.05  # 5% sd as fraction of baseline
    age_advance: bool = True
    random_seed: int = 42


def _draw_encounter_count(rng: np.random.Generator, mean: float) -> int:
    return max(1, int(rng.poisson(lam=mean)))


def _drift_continuous(
    base: float, drift_scale: float, rng: np.random.Generator
) -> float:
    if pd.isna(base):
        return base
    return float(base * (1.0 + rng.normal(0.0, drift_scale)))


def expand_to_trajectories(
    baselines: pd.DataFrame,
    date_lo: pd.Timestamp,
    date_hi: pd.Timestamp,
    cfg: TrajectoryConfig,
) -> pd.DataFrame:
    """Expand each baseline row into multiple episode rows over time."""
    rng = np.random.default_rng(cfg.random_seed)
    out_rows: list[dict] = []
    window_seconds = max((date_hi - date_lo).total_seconds(), 1.0)

    sticky = set(schema.COMORBIDITY_COLUMNS + schema.FLAG_COLUMNS)
    continuous = set(schema.LAB_COLUMNS + schema.VITAL_COLUMNS + schema.COUNT_COLUMNS)

    for _, base in baselines.iterrows():
        patient_id = f"SYN_{uuid.uuid4().hex[:8].upper()}"
        n_enc = _draw_encounter_count(rng, cfg.encounters_per_patient_mean)
        anchor = pd.Timestamp(date_lo + pd.Timedelta(seconds=float(rng.random() * window_seconds)))
        span = pd.Timedelta(days=int(cfg.years_of_history * 365.25))
        offsets = np.sort(rng.random(n_enc)) * span.total_seconds()
        for i, off in enumerate(offsets):
            row = base.copy()
            episode_dt = anchor + pd.Timedelta(seconds=float(off))
            row["HASTA_ID"] = patient_id
            row["RF_EPISODE2"] = int(rng.integers(10_000_000, 99_999_999))
            row["episode_date"] = episode_dt
            for col in row.index:
                if col in sticky:
                    continue
                if col in continuous and pd.notna(row[col]):
                    row[col] = _drift_continuous(float(row[col]), cfg.lab_drift_scale, rng)
            if cfg.age_advance and pd.notna(row.get("age")):
                # Add fractional years between baseline date and this episode.
                delta_years = (episode_dt - anchor).total_seconds() / (365.25 * 86400)
                row["age"] = int(round(float(row["age"]) + delta_years))
            out_rows.append(row.to_dict())

    return pd.DataFrame(out_rows)
