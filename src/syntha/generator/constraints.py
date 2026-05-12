"""Physiologic constraints applied after copula sampling.

We use rejection sampling for hard impossibilities (systolic <= diastolic) and
soft repair (clipping to physiologic bounds) for outliers that the copula tail
occasionally produces. Friedewald (LDL ≈ total − HDL − TG/5) is checked with a
generous tolerance because direct-LDL was assayed in this cohort.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .. import schema


@dataclass
class ConstraintConfig:
    enforce_systolic_gt_diastolic: bool = True
    min_pulse_pressure: float = 20.0
    enforce_cholesterol_friedewald: bool = True
    friedewald_tolerance: float = 40.0
    enforce_egfr_creatinine: bool = True
    drop_invalid: bool = True


class PhysiologicConstraints:
    def __init__(self, config: ConstraintConfig | None = None) -> None:
        self.cfg = config or ConstraintConfig()

    def repair(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clip to physiologic bounds; non-destructive."""
        out = df.copy()
        for col, (lo, hi) in schema.PHYSIOLOGIC_BOUNDS.items():
            if col in out.columns:
                out[col] = out[col].clip(lower=lo, upper=hi)
        return out

    def validity_mask(self, df: pd.DataFrame) -> pd.Series:
        """Boolean mask of rows that satisfy all enabled hard constraints.

        Rows with missing inputs for a given rule are passed through (a rule can
        only fire when all its inputs are observed).
        """
        mask = pd.Series(True, index=df.index)

        if self.cfg.enforce_systolic_gt_diastolic and {"bp_systolic", "bp_diastolic"} <= set(df.columns):
            present = df["bp_systolic"].notna() & df["bp_diastolic"].notna()
            ok = (df["bp_systolic"] - df["bp_diastolic"]) >= self.cfg.min_pulse_pressure
            mask &= (~present) | ok

        if self.cfg.enforce_cholesterol_friedewald and {
            "cholesterol_total_latest", "hdl_latest", "ldl_direct_latest", "triglycerides_latest",
        } <= set(df.columns):
            cols = ["cholesterol_total_latest", "hdl_latest", "ldl_direct_latest", "triglycerides_latest"]
            present = df[cols].notna().all(axis=1)
            expected = df["hdl_latest"] + df["ldl_direct_latest"] + df["triglycerides_latest"] / 5.0
            diff = (df["cholesterol_total_latest"] - expected).abs()
            ok = diff <= self.cfg.friedewald_tolerance
            mask &= (~present) | ok

        if self.cfg.enforce_egfr_creatinine and {"egfr_latest", "creatinine_latest"} <= set(df.columns):
            present = df["egfr_latest"].notna() & df["creatinine_latest"].notna()
            bad = (df["creatinine_latest"] > 2.0) & (df["egfr_latest"] > 90)
            mask &= (~present) | (~bad)

        return mask

    def apply(self, df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
        repaired = self.repair(df)
        mask = self.validity_mask(repaired)
        kept = repaired[mask].reset_index(drop=True)
        stats = {
            "rows_in": len(df),
            "rows_kept": int(mask.sum()),
            "rows_dropped": int((~mask).sum()),
            "drop_rate": float((~mask).mean()),
        }
        return kept, stats
