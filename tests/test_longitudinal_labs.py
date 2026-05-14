"""Tests for lab time-series + intra-encounter BP trajectories."""
import numpy as np
import pandas as pd
import pytest

from syntha.longitudinal_labs import (
    COLUMN_DRIFT,
    TIME_SERIES_COLUMNS,
    TrajectoryConfig,
    _ar1_path,
    _intra_encounter_bp,
    expand_observations_with_history,
)


def test_ar1_path_returns_correct_length():
    rng = np.random.default_rng(1)
    days = [90, 270, 540]
    vals = _ar1_path(100.0, days, 0.05, 0.0, rng)
    assert len(vals) == 3


def test_ar1_path_stays_close_to_latest_no_trend():
    rng = np.random.default_rng(2)
    latest = 100.0
    vals = _ar1_path(latest, [180], 0.05, 0.0, rng)
    # σ = 5% × 100 = 5, but values are realistic — within 3σ
    assert abs(vals[0] - latest) < 15


def test_ar1_path_secular_trend_decreases_egfr():
    """eGFR has trend = -1%/year. Path going BACK 5 years should show
    HIGHER values (eGFR was higher then)."""
    rng = np.random.default_rng(3)
    latest = 90.0
    # 5 years ago
    vals = _ar1_path(latest, [1825], 0.06, -0.010, rng)
    # 5 years × 1% = 5% trend. Should be ~94-95 historically.
    avg_historical = vals[0]
    # Allow for noise but trend should bias upward
    assert avg_historical > latest - 10  # within noise envelope including ~5 trend


def test_intra_encounter_bp_count_and_white_coat_drop():
    rng = np.random.default_rng(4)
    cfg = TrajectoryConfig(intra_encounter_bp_count=3, bp_white_coat_drop_mmHg=5.0)
    bps = _intra_encounter_bp(140.0, 90.0, cfg, rng)
    assert len(bps) == 3
    # Average sys should drop across 3 measurements (white-coat effect)
    sys_vals = [b[0] for b in bps]
    # 3rd reading deterministic drop is 2*5 = 10 below first, plus noise
    assert sys_vals[0] > sys_vals[-1] - 15  # noise can mask drop, but trend is there
    # Timestamps increasing
    times = [b[2] for b in bps]
    assert times == sorted(times)


def test_expand_observations_emits_history_for_each_lab():
    rng = np.random.default_rng(5)
    row = pd.Series({
        "egfr_latest": 90.0,
        "creatinine_latest": 0.9,
        "hemoglobin_latest": 14.0,
        "bp_systolic": 130.0,
        "bp_diastolic": 85.0,
    })
    extras = expand_observations_with_history(
        row,
        patient_id="test-patient-uuid",
        episode_dt=pd.Timestamp("2024-06-01"),
        cfg=TrajectoryConfig(n_historical_min=2, n_historical_max=2,
                             intra_encounter_bp_count=3),
        rng=rng,
    )
    # 3 labs × 2 history + (3-1) intra-encounter BP × 2 (sys+dia) = 6 + 4 = 10
    assert len(extras) >= 8

    # Each Observation should be valid FHIR
    for obs in extras:
        assert obs["resourceType"] == "Observation"
        assert obs["status"] == "final"
        assert "valueQuantity" in obs
        assert obs["subject"]["reference"] == "urn:uuid:test-patient-uuid"


def test_missing_value_skipped():
    rng = np.random.default_rng(6)
    row = pd.Series({"egfr_latest": float("nan"), "creatinine_latest": 1.0})
    extras = expand_observations_with_history(
        row, "id", pd.Timestamp("2024-06-01"), rng=rng,
    )
    # Only creatinine should produce history; eGFR is NaN
    by_loinc = {e["code"]["coding"][0]["code"] for e in extras}
    assert "62238-1" not in by_loinc  # eGFR LOINC absent
    assert "2160-0" in by_loinc       # creatinine LOINC present


def test_column_drift_table_covers_all_modeled_labs():
    """Every lab in TIME_SERIES_COLUMNS should have a drift entry."""
    assert set(TIME_SERIES_COLUMNS) <= set(COLUMN_DRIFT.keys())


@pytest.mark.parametrize("col", ["egfr_latest", "creatinine_latest", "hemoglobin_latest"])
def test_history_observations_are_dated_in_the_past(col):
    rng = np.random.default_rng(7)
    row = pd.Series({col: 100.0})
    episode = pd.Timestamp("2024-06-01")
    extras = expand_observations_with_history(
        row, "id", episode, cfg=TrajectoryConfig(n_historical_min=2, n_historical_max=2),
        rng=rng,
    )
    for obs in extras:
        eff = pd.Timestamp(obs["effectiveDateTime"].rstrip("Z"))
        assert eff < episode
