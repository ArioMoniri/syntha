"""Clinical reference ranges (G3 from the medical-officer review).

Distinct from ``schema.PHYSIOLOGIC_BOUNDS`` which encodes "alive vs dead"
limits (hemoglobin 4–22 g/dL — physiologically possible, but a male
patient with Hb=8 is severely anemic). These ranges are the
**reference intervals** used by clinical labs to flag a value as out
of normal range.

Values are sex- and age-specific where the underlying biology
differs (hemoglobin, creatinine, eGFR). Adult ranges apply from age 18+.

References (all major clinical chemistry references converge within ~5%):
  * NIH National Library of Medicine — MedlinePlus reference intervals
  * Tietz Textbook of Clinical Chemistry, 8th ed. (2024)
  * Mayo Clinic Laboratories reference intervals (online catalogue)
  * KDIGO 2024 CKD guideline (eGFR staging)
  * NCEP ATP-III + 2018 AHA/ACC cholesterol guidelines (lipids)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Sex = Literal["M", "F"]


@dataclass(frozen=True)
class ReferenceInterval:
    """A reference interval. ``low``/``high`` may be None for one-sided refs
    (e.g. LDL: only an upper desirable bound). ``units`` always matches the
    units of the corresponding source-CSV column.
    """
    low: float | None
    high: float | None
    units: str
    notes: str = ""

    def contains(self, value: float | None) -> bool:
        if value is None:
            return True  # missing values are not flagged
        if self.low is not None and value < self.low:
            return False
        if self.high is not None and value > self.high:
            return False
        return True


# Sex-agnostic adult intervals.
COMMON: dict[str, ReferenceInterval] = {
    "glucose_fasting_latest":   ReferenceInterval(70, 99, "mg/dL", "fasting; >125 = diabetic range"),
    "hdl_latest":               ReferenceInterval(40, None, "mg/dL", "M ≥ 40, F ≥ 50 ideally"),
    "ldl_direct_latest":        ReferenceInterval(None, 100, "mg/dL", "<100 desirable; <70 in high-risk patients"),
    "cholesterol_total_latest": ReferenceInterval(None, 200, "mg/dL", "<200 desirable"),
    "triglycerides_latest":     ReferenceInterval(None, 150, "mg/dL", "<150 desirable"),
    "alt_latest":               ReferenceInterval(7, 56, "U/L", "M ≤ 50, F ≤ 38 more commonly cited"),
    "ast_latest":               ReferenceInterval(8, 48, "U/L", ""),
    "platelets_latest":         ReferenceInterval(150, 450, "10^3/uL", ""),
    "wbc_latest":               ReferenceInterval(4.5, 11.0, "10^3/uL", ""),
    "ferritin_latest":          ReferenceInterval(20, 250, "ng/mL", "M 30–400, F 13–150 more strictly"),
    "vitamin_b12_latest":       ReferenceInterval(200, 900, "pg/mL", "<200 deficient, >900 possibly indicating excess"),
    "bp_systolic":              ReferenceInterval(None, 120, "mmHg", "<120 normal; 120–129 elevated; 130+ HTN"),
    "bp_diastolic":             ReferenceInterval(None, 80, "mmHg", "<80 normal; 80–89 HTN-1; 90+ HTN-2"),
    "egfr_latest":              ReferenceInterval(90, None, "mL/min/1.73m²", "G1 ≥ 90, G2 60–89, G3a 45–59, G3b 30–44, G4 15–29, G5 < 15"),
}

# Sex-specific adult intervals (the columns whose normal range differs by sex).
BY_SEX: dict[str, dict[Sex, ReferenceInterval]] = {
    "hemoglobin_latest": {
        "M": ReferenceInterval(13.5, 17.5, "g/dL", "adult male"),
        "F": ReferenceInterval(12.0, 15.5, "g/dL", "adult female non-pregnant"),
    },
    "creatinine_latest": {
        "M": ReferenceInterval(0.74, 1.35, "mg/dL", "adult male"),
        "F": ReferenceInterval(0.59, 1.04, "mg/dL", "adult female"),
    },
}


def get_reference(column: str, sex: Sex | None = None) -> ReferenceInterval | None:
    """Look up the reference interval for ``column``, sex-aware where needed.

    Returns ``None`` if the column has no clinical reference defined
    (e.g. ``age``, comorbidity flags) — caller should treat that as
    "no flagging applies".
    """
    if column in BY_SEX:
        if sex is None:
            # Caller didn't specify sex but column needs it — average the
            # bounds across both as a coarse fallback.
            m = BY_SEX[column]["M"]
            f = BY_SEX[column]["F"]
            return ReferenceInterval(
                low=min(x for x in (m.low, f.low) if x is not None) if (m.low or f.low) else None,
                high=max(x for x in (m.high, f.high) if x is not None) if (m.high or f.high) else None,
                units=m.units,
                notes="combined-sex coarse range",
            )
        return BY_SEX[column].get(sex)
    return COMMON.get(column)


def is_within_reference(column: str, value: float | None, sex: Sex | None = None) -> bool:
    ref = get_reference(column, sex)
    if ref is None:
        return True
    return ref.contains(value)


def row_within_reference(row, sex_column: str = "gender_is_male") -> dict[str, bool]:
    """Per-column check for one synthetic-record row.

    Returns a dict {column: is-within-reference}. Missing values are
    treated as within-range. Useful when a downstream consumer wants
    only patients whose entire lab panel falls inside the reference
    interval (a "definitely-clinically-healthy" subset).
    """
    sex: Sex | None = None
    try:
        if sex_column in row:
            v = row[sex_column]
            if v is not None:
                sex = "M" if int(v) == 1 else "F"
    except (KeyError, ValueError, TypeError):
        pass

    result: dict[str, bool] = {}
    for col in list(COMMON.keys()) + list(BY_SEX.keys()):
        if col in row:
            v = row[col]
            try:
                vf = float(v) if v is not None else None
            except (TypeError, ValueError):
                vf = None
            result[col] = is_within_reference(col, vf, sex)
    return result


def fraction_within_reference(df, sex_column: str = "gender_is_male") -> dict[str, float]:
    """Vectorized: per-column fraction of rows whose value is within reference.

    Returns {column: fraction in [0,1]}. Used by the validation report
    to spot synthetic populations that drift outside clinically normal.
    """
    import pandas as pd
    out: dict[str, float] = {}
    has_sex = sex_column in df.columns
    male_mask = pd.to_numeric(df[sex_column], errors="coerce") == 1 if has_sex else None
    for col, ref in COMMON.items():
        if col not in df.columns:
            continue
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if not len(s):
            continue
        ok = s.between(
            ref.low if ref.low is not None else float("-inf"),
            ref.high if ref.high is not None else float("inf"),
        )
        out[col] = float(ok.mean())
    for col, refs in BY_SEX.items():
        if col not in df.columns or not has_sex:
            continue
        s = pd.to_numeric(df[col], errors="coerce")
        m_ref, f_ref = refs["M"], refs["F"]
        ok = pd.Series(True, index=df.index)
        for mask, r in ((male_mask, m_ref), (~male_mask, f_ref)):
            sub = s[mask]
            sub_ok = sub.between(
                r.low if r.low is not None else float("-inf"),
                r.high if r.high is not None else float("inf"),
            )
            ok.loc[mask] = sub_ok
        ok = ok[s.notna()]
        if len(ok):
            out[col] = float(ok.mean())
    return out
