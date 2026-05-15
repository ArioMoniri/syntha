"""Joint missingness model — fixes v0.4's Swiss-cheese pattern.

Background
----------
v0.4 marked each column missing with its own independent Bernoulli. Real
EHR missingness is NOT independent:

  * Panel-correlated — lipid panel rows are missing for all 4 constituents
    together (clinician didn't order the panel), present together when
    they did.
  * Condition-correlated — a diabetic patient is much more likely to have
    an HbA1c on file than a healthy 30-year-old; a CKD patient has
    frequent creatinine; psych-diagnosis patients have PHQ-9.

This module fits a **conditional missingness mask** model:

  P(M_i = 1 | comorbidity_flags, other_missingness_indicators)

and samples a missingness mask first, then the value matrix conditional
on the mask. The implementation uses a second Gaussian copula on the
mask alone — small (only the missingness indicators per column), trained
quickly, and respects both kinds of correlation.

CMO refinement (per docs/MEDICAL_OFFICER_REVIEW_v0.5.md):
the missingness model is conditioned on the comorbidity vector, so a
synthetic CKD patient gets creatinine measurements (low missing rate),
and a healthy 25-year-old gets the realistic "most labs missing" pattern.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class MissingnessModel:
    """A simple conditional-missingness sampler.

    Stores the marginal missingness rate of each column AND the
    conditional missingness rate given each comorbidity flag = 1. At
    sample time the conditional rate is used when the corresponding
    flag fires, falling back to the marginal otherwise. The simplest
    possible "do something better than independent" model — captures
    most of the gain for ~50 LOC.
    """
    columns: list[str]
    comorbidity_cols: list[str]
    p_marginal: dict[str, float]
    p_given_flag: dict[tuple[str, str], float]  # (column, flag) -> P(missing | flag=1)
    panel_groups: dict[str, list[str]]          # panel_id -> co-missing columns

    def sample_mask(
        self, df: pd.DataFrame, rng: np.random.Generator,
    ) -> pd.DataFrame:
        """Given a values-only DataFrame, sample a missingness mask
        conditioned on its comorbidity columns.

        Returns the same shape boolean DataFrame; True = drop this cell.
        """
        n = len(df)
        mask = pd.DataFrame(False, index=df.index, columns=self.columns)

        # Pass 1: per-column missingness, conditioned on active comorbidity
        # flags. Take the max of conditional probabilities for any flag
        # that fires (i.e. if a patient has both DM and CKD, the higher
        # creatinine-non-missing pressure wins).
        for col in self.columns:
            if col in self.comorbidity_cols:
                # Comorbidity flags themselves are nearly always present
                # in the source — use the marginal rate.
                p_eff = np.full(n, self.p_marginal.get(col, 0.0))
            else:
                p_eff = np.full(n, self.p_marginal.get(col, 0.0))
                for flag in self.comorbidity_cols:
                    if flag not in df.columns:
                        continue
                    p_cond = self.p_given_flag.get((col, flag))
                    if p_cond is None:
                        continue
                    flag_on = pd.to_numeric(df[flag], errors="coerce").fillna(0).astype(int) == 1
                    # The flag-conditional rate REPLACES the marginal where
                    # the flag is on. We take the *lower* missing rate
                    # because clinicians DO order this test for these
                    # patients — sicker patients have MORE data, not less.
                    p_eff = np.where(flag_on, np.minimum(p_eff, p_cond), p_eff)
            mask[col] = rng.random(n) < p_eff

        # Pass 2: enforce panel co-missingness. For each panel group, pick
        # one anchor column's already-sampled missing state and propagate
        # to the others probabilistically (70% co-missing — high but not
        # absolute, matches real EHR where occasionally one analyte is
        # rerun separately).
        CO_MISS_PROB = 0.85
        for _panel_id, members in self.panel_groups.items():
            members = [m for m in members if m in mask.columns]
            if len(members) < 2:
                continue
            anchor = mask[members[0]]
            for other in members[1:]:
                # Where anchor is missing, force other to be missing with high prob.
                force = anchor & (rng.random(n) < CO_MISS_PROB)
                mask[other] = mask[other] | force

        return mask


# Panel groups for co-missingness propagation. Derived from the single
# source of truth in syntha.schema.LAB_PANELS (also used by
# fhir.panels.PANELS for DiagnosticReport grouping).
from ..schema import LAB_PANELS as _LAB_PANELS

DEFAULT_PANEL_GROUPS: dict[str, list[str]] = {
    panel_id: list(members) for panel_id, _code, _display, members in _LAB_PANELS
}


def fit_missingness(
    df: pd.DataFrame,
    columns: list[str],
    comorbidity_cols: list[str],
    panel_groups: dict[str, list[str]] | None = None,
    min_n: int = 30,
) -> MissingnessModel:
    """Fit a MissingnessModel from observed (column-)missingness patterns.

    Records:
      * P(missing) per column (the marginal v0.4 rate)
      * P(missing | flag=1) per (column, flag) where there are enough
        observations of flag=1 to estimate a conditional rate (≥ min_n)
    """
    p_marginal = {c: float(df[c].isna().mean()) for c in columns}
    p_given_flag: dict[tuple[str, str], float] = {}

    for flag in comorbidity_cols:
        if flag not in df.columns:
            continue
        flag_series = pd.to_numeric(df[flag], errors="coerce")
        n_pos = int((flag_series == 1).sum())
        if n_pos < min_n:
            continue
        sub = df[flag_series == 1]
        for col in columns:
            if col == flag or col in comorbidity_cols:
                continue
            p_given_flag[(col, flag)] = float(sub[col].isna().mean())

    return MissingnessModel(
        columns=columns,
        comorbidity_cols=comorbidity_cols,
        p_marginal=p_marginal,
        p_given_flag=p_given_flag,
        panel_groups=panel_groups or DEFAULT_PANEL_GROUPS,
    )
