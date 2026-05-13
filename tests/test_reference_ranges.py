"""Tests for clinical reference ranges (G3)."""
import pandas as pd

from syntha.reference_ranges import (
    BY_SEX,
    COMMON,
    fraction_within_reference,
    get_reference,
    is_within_reference,
    row_within_reference,
)


def test_sex_specific_hemoglobin_differs():
    male_ref = get_reference("hemoglobin_latest", "M")
    female_ref = get_reference("hemoglobin_latest", "F")
    assert male_ref is not None and female_ref is not None
    # Both bounds higher for males per textbook adult ranges.
    assert male_ref.low > female_ref.low
    assert male_ref.high > female_ref.high


def test_male_anemic_value_flagged():
    # Hb 11.0 is anemic for adult male (ref 13.5–17.5) but normal-low for
    # female (ref 12.0–15.5; 11.0 still flagged but only by 1.0 g/dL).
    assert is_within_reference("hemoglobin_latest", 11.0, "M") is False
    assert is_within_reference("hemoglobin_latest", 11.0, "F") is False


def test_normal_hemoglobin_passes_both_sexes():
    assert is_within_reference("hemoglobin_latest", 14.0, "M") is True
    assert is_within_reference("hemoglobin_latest", 13.0, "F") is True


def test_one_sided_ldl_interval():
    """LDL has only an upper desirable bound."""
    ldl = get_reference("ldl_direct_latest")
    assert ldl is not None
    assert ldl.low is None  # no lower bound
    assert ldl.high == 100
    assert is_within_reference("ldl_direct_latest", 80) is True
    assert is_within_reference("ldl_direct_latest", 150) is False


def test_missing_value_is_treated_as_within_range():
    assert is_within_reference("hemoglobin_latest", None, "M") is True


def test_unknown_column_returns_none():
    assert get_reference("not_a_real_column") is None
    assert is_within_reference("not_a_real_column", 42.0) is True  # no flag


def test_row_within_reference_dispatches_by_sex():
    row = pd.Series({
        "gender_is_male": 1,
        "hemoglobin_latest": 14.5,    # normal for M
        "creatinine_latest": 0.9,     # normal for M
        "ldl_direct_latest": 200,     # flagged
        "bp_systolic": 110,           # normal
    })
    result = row_within_reference(row)
    assert result["hemoglobin_latest"] is True
    assert result["creatinine_latest"] is True
    assert result["ldl_direct_latest"] is False
    assert result["bp_systolic"] is True


def test_fraction_within_reference_vectorized():
    df = pd.DataFrame({
        "gender_is_male": [1, 1, 0, 0],
        "hemoglobin_latest": [14.0, 18.0, 13.0, 11.0],   # M: 14 OK, 18 high; F: 13 OK, 11 low
        "ldl_direct_latest": [90, 110, 80, 150],         # 2/4 OK
    })
    fr = fraction_within_reference(df)
    assert abs(fr["hemoglobin_latest"] - 0.50) < 1e-9
    assert abs(fr["ldl_direct_latest"] - 0.50) < 1e-9


def test_reference_table_completeness():
    """Every continuous lab column we model should have a reference range
    (per the medical-officer review G3 requirement)."""
    expected = {
        "glucose_fasting_latest", "hdl_latest", "ldl_direct_latest",
        "cholesterol_total_latest", "triglycerides_latest", "alt_latest",
        "ast_latest", "platelets_latest", "wbc_latest", "ferritin_latest",
        "vitamin_b12_latest", "bp_systolic", "bp_diastolic", "egfr_latest",
        "hemoglobin_latest", "creatinine_latest",
    }
    have = set(COMMON.keys()) | set(BY_SEX.keys())
    assert expected <= have, f"missing reference for: {expected - have}"
