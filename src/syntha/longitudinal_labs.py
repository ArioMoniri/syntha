"""Lab time-series + intra-encounter vital trajectories.

Per docs/MEDICAL_OFFICER_REVIEW_v0.5.md §5.5, single ``_latest`` values
are clinically unrealistic. This module synthesizes:

  * **Lab time-series** — 2-4 prior measurements over the preceding
    6-24 months, drifting around the ``_latest`` value with
    column-specific biological variation pulled from Westgard QC.
    eGFR has slow secular decline (~0.8 mL/min/year in healthy
    adults), HbA1c has 0.3% σ over 3 months, hemoglobin is stable
    (σ 0.3 g/dL).
  * **Intra-encounter BP trajectory** — 2-3 BP measurements 5 min apart,
    with the standard clinical pattern of a slight decline on the
    second/third reading (white-coat effect).

The output is a list of FHIR ``Observation`` resources keyed off the
existing single Observation; the caller (fhir.export) appends them to
the bundle's resources list.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .fhir.codes import LAB_LOINC

# ── Column-specific biological variation (Westgard QC database, May 2026)
# Each entry: (sigma_per_measurement_as_fraction_of_value,
#              secular_trend_per_year_fraction).
#
# E.g. eGFR has 5% measurement variability + 1%/year decline trend.
COLUMN_DRIFT: dict[str, tuple[float, float]] = {
    "glucose_fasting_latest":    (0.045, 0.00),    # 4.5% CV, no trend in healthy
    "ldl_direct_latest":         (0.080, 0.00),    # 8% CV, lipid panel CVs are big
    "hdl_latest":                (0.060, 0.00),    # 6% CV
    "cholesterol_total_latest":  (0.050, 0.00),    # 5% CV
    "triglycerides_latest":      (0.150, 0.00),    # TGs are HIGHLY variable (15%)
    "egfr_latest":               (0.060, -0.010),  # 6% CV, ~1%/yr decline in healthy adults
    "creatinine_latest":         (0.040, 0.005),   # 4% CV, slight uptick with age
    "hemoglobin_latest":         (0.020, 0.00),    # very stable, 2% CV
    "wbc_latest":                (0.080, 0.00),    # 8% CV
    "platelets_latest":          (0.060, 0.00),    # 6% CV
    "alt_latest":                (0.150, 0.00),    # liver enzymes vary 15% normally
    "ast_latest":                (0.150, 0.00),
    "ferritin_latest":           (0.140, 0.00),
    "vitamin_b12_latest":        (0.100, 0.00),
}

# Labs that appear in real EHRs as multi-time-point series; others typically
# only get measured once per visit (skip those for time-series synthesis).
TIME_SERIES_COLUMNS = list(COLUMN_DRIFT.keys())


@dataclass
class TrajectoryConfig:
    n_historical_min: int = 2
    n_historical_max: int = 4
    history_window_days_min: int = 180   # 6 months
    history_window_days_max: int = 730   # 24 months
    intra_encounter_bp_count: int = 3    # 3 BP measurements per visit
    intra_encounter_bp_gap_min_s: int = 240   # 4 min between
    intra_encounter_bp_gap_max_s: int = 360   # 6 min between
    bp_white_coat_drop_mmHg: float = 4.0  # systolic drop per repeat measurement


def _ar1_path(
    latest_value: float,
    days_ago: list[int],
    sigma_frac: float,
    secular_trend_per_year: float,
    rng: np.random.Generator,
) -> list[float]:
    """AR(1)-style trajectory ending at ``latest_value``.

    Generates values for each past time-point. Walks backward from the
    latest value, adding Gaussian noise at each step with σ proportional
    to the latest value AND a secular trend (e.g. eGFR decline). Returns
    list of historical values, oldest-first.
    """
    sigma = max(0.001, sigma_frac * abs(latest_value))
    # Sort days_ago ascending (most recent first) for the walk-back.
    days_ago = sorted(days_ago)
    trajectory = []
    # Walk backward: latest_value → days_ago[0] → days_ago[1] → ...
    current = latest_value
    prev_days = 0
    for d in days_ago:
        delta_days = d - prev_days
        # Per-measurement noise
        noise = rng.normal(0.0, sigma)
        # Secular trend (reverse direction since we're going back in time)
        trend = -secular_trend_per_year * latest_value * (delta_days / 365.25)
        current = current + noise + trend
        trajectory.append(current)
        prev_days = d
    # Return oldest-first
    return trajectory[::-1]


def _intra_encounter_bp(
    sys_latest: float | None,
    dia_latest: float | None,
    cfg: TrajectoryConfig,
    rng: np.random.Generator,
) -> list[tuple[float, float, int]]:
    """Generate ``cfg.intra_encounter_bp_count`` BP measurements within
    one encounter. Returns list of (sys, dia, seconds_after_encounter_start).

    The first measurement is the published ``_latest`` value. Subsequent
    measurements show a slight decline (white-coat-effect mitigation —
    well-documented in ambulatory monitoring literature). Random small
    Gaussian noise (~3 mmHg) on each beyond the deterministic drop.
    """
    if sys_latest is None or dia_latest is None:
        return []
    measurements = []
    cumulative_drop_sys = 0.0
    cumulative_drop_dia = 0.0
    t = 0
    for i in range(cfg.intra_encounter_bp_count):
        sys_val = sys_latest - cumulative_drop_sys + rng.normal(0.0, 3.0)
        dia_val = dia_latest - cumulative_drop_dia + rng.normal(0.0, 2.0)
        measurements.append((float(sys_val), float(dia_val), t))
        # Set up the next measurement: ~4-6 min later, slightly lower.
        cumulative_drop_sys += cfg.bp_white_coat_drop_mmHg
        cumulative_drop_dia += cfg.bp_white_coat_drop_mmHg * 0.5
        t += int(rng.integers(cfg.intra_encounter_bp_gap_min_s,
                              cfg.intra_encounter_bp_gap_max_s))
    return measurements


def _observation_with_effective_time(
    patient_id: str, column: str, value: float, effective_iso: str,
) -> dict:
    """Build a single Observation resource — same shape as the main exporter,
    just with a parametric effective time."""
    code, display, unit = LAB_LOINC[column]
    is_vital = column in {"bp_systolic", "bp_diastolic"}
    category = "vital-signs" if is_vital else "laboratory"
    return {
        "resourceType": "Observation",
        "id": str(uuid.uuid4()),
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": category,
                "display": category.replace("-", " ").title(),
            }],
        }],
        "code": {
            "coding": [{"system": "http://loinc.org", "code": code, "display": display}],
            "text": display,
        },
        "subject": {"reference": f"urn:uuid:{patient_id}"},
        "effectiveDateTime": effective_iso,
        "valueQuantity": {
            "value": float(value),
            "unit": unit,
            "system": "http://unitsofmeasure.org",
            "code": unit,
        },
    }


def expand_observations_with_history(
    row: pd.Series,
    patient_id: str,
    episode_dt: pd.Timestamp,
    cfg: TrajectoryConfig | None = None,
    rng: np.random.Generator | None = None,
) -> list[dict]:
    """For each lab column in TIME_SERIES_COLUMNS that has a value, emit
    ``cfg.n_historical`` extra Observation resources at past timepoints.
    Plus emit intra-encounter BP measurements.

    Caller is responsible for splicing these into the bundle alongside the
    existing single-point Observation. (The single-point one stays — it's
    the ``_latest`` entry; the history entries are *prior* measurements.)
    """
    cfg = cfg or TrajectoryConfig()
    rng = rng or np.random.default_rng()
    extras: list[dict] = []

    # ── Lab history (2-4 prior measurements per lab) ──
    for col in TIME_SERIES_COLUMNS:
        if col not in row.index:
            continue
        value = row.get(col)
        if value is None or pd.isna(value):
            continue
        n_hist = int(rng.integers(cfg.n_historical_min, cfg.n_historical_max + 1))
        days_ago = rng.integers(
            cfg.history_window_days_min, cfg.history_window_days_max, n_hist,
        ).tolist()
        sigma_frac, trend = COLUMN_DRIFT[col]
        values = _ar1_path(float(value), days_ago, sigma_frac, trend, rng)
        for v, d in zip(values, sorted(days_ago, reverse=True)):
            past_dt = episode_dt - pd.Timedelta(days=int(d))
            extras.append(_observation_with_effective_time(
                patient_id, col, v, past_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            ))

    # ── Intra-encounter BP (3 readings ~5 min apart) ──
    sys_v = row.get("bp_systolic")
    dia_v = row.get("bp_diastolic")
    if not (pd.isna(sys_v) if isinstance(sys_v, float) else sys_v is None):
        bp_measurements = _intra_encounter_bp(
            None if pd.isna(sys_v) else float(sys_v),
            None if pd.isna(dia_v) else float(dia_v),
            cfg, rng,
        )
        # Skip the first one (it's the same as the existing main Observation).
        for sys_val, dia_val, t_offset in bp_measurements[1:]:
            sub_dt = episode_dt + pd.Timedelta(seconds=t_offset)
            extras.append(_observation_with_effective_time(
                patient_id, "bp_systolic", sys_val,
                sub_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            ))
            extras.append(_observation_with_effective_time(
                patient_id, "bp_diastolic", dia_val,
                sub_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            ))

    return extras
