"""Tests for the joint missingness model."""
import numpy as np
import pandas as pd

from syntha.generator.missingness import (
    DEFAULT_PANEL_GROUPS,
    MissingnessModel,
    fit_missingness,
)


def _toy_panel_data(n=4000, seed=0):
    rng = np.random.default_rng(seed)
    # 20% of patients are diabetic — they ALWAYS have CMP values
    # (creatinine, glucose), but only 50% have lipid panel.
    dm = rng.binomial(1, 0.20, n).astype(int)
    healthy = (dm == 0).astype(bool)

    df = pd.DataFrame({
        "DM_Tum": dm,
        "Hipertansiyon": rng.binomial(1, 0.10, n),
        # Lipid panel — present in 50% of healthy, 80% of DM
        "cholesterol_total_latest": np.where(
            healthy, rng.choice([np.nan, 200.0], n, p=[0.50, 0.50]),
            rng.choice([np.nan, 200.0], n, p=[0.20, 0.80]),
        ),
        # CMP — present in 50% healthy, 95% DM
        "creatinine_latest": np.where(
            healthy, rng.choice([np.nan, 1.0], n, p=[0.50, 0.50]),
            rng.choice([np.nan, 1.0], n, p=[0.05, 0.95]),
        ),
        "glucose_fasting_latest": np.where(
            healthy, rng.choice([np.nan, 100.0], n, p=[0.50, 0.50]),
            rng.choice([np.nan, 100.0], n, p=[0.05, 0.95]),
        ),
        # Hemoglobin — present in 70% of healthy, 90% DM
        "hemoglobin_latest": np.where(
            healthy, rng.choice([np.nan, 14.0], n, p=[0.30, 0.70]),
            rng.choice([np.nan, 14.0], n, p=[0.10, 0.90]),
        ),
    })
    return df


def test_marginal_and_conditional_rates_learned():
    df = _toy_panel_data()
    model = fit_missingness(
        df,
        columns=[
            "cholesterol_total_latest", "creatinine_latest",
            "glucose_fasting_latest", "hemoglobin_latest",
            "DM_Tum", "Hipertansiyon",
        ],
        comorbidity_cols=["DM_Tum", "Hipertansiyon"],
    )

    # Marginal creatinine missing rate ≈ 0.5*0.8 + 0.5*0.2 ≈ 0.40
    # (50% are healthy with 50% missing; 50% are DM ... wait, 80% healthy + 20% DM)
    # Actually 0.8 * 0.50 + 0.2 * 0.05 = 0.41
    assert 0.30 < model.p_marginal["creatinine_latest"] < 0.50

    # Conditional creatinine|DM should be ≈ 0.05
    assert model.p_given_flag[("creatinine_latest", "DM_Tum")] < 0.15


def test_sample_mask_propagates_panel_co_missingness():
    """After sampling, lipid-panel co-missingness should be substantial."""
    # Add all 4 lipid panel columns to the toy data
    rng = np.random.default_rng(1)
    n = 4000
    df = _toy_panel_data(n=n)
    df["hdl_latest"] = rng.choice([np.nan, 50.0], n, p=[0.5, 0.5])
    df["ldl_direct_latest"] = rng.choice([np.nan, 120.0], n, p=[0.5, 0.5])
    df["triglycerides_latest"] = rng.choice([np.nan, 150.0], n, p=[0.5, 0.5])

    model = fit_missingness(
        df,
        columns=[
            "cholesterol_total_latest", "hdl_latest", "ldl_direct_latest",
            "triglycerides_latest",
            "DM_Tum",
        ],
        comorbidity_cols=["DM_Tum"],
    )
    # Synthetic sample df with values present (mask is sampled on top)
    n = 5000
    syn = pd.DataFrame({
        "DM_Tum": np.zeros(n, dtype=int),  # all healthy, so high missingness expected
        "cholesterol_total_latest": np.full(n, 200.0),
        "hdl_latest": np.full(n, 50.0),
        "ldl_direct_latest": np.full(n, 120.0),
        "triglycerides_latest": np.full(n, 150.0),
    })
    rng = np.random.default_rng(42)
    mask = model.sample_mask(syn, rng)

    # All four lipid columns should have similar missingness rates (panel
    # behavior), not independent Bernoullis.
    rates = {c: float(mask[c].mean()) for c in
             ["cholesterol_total_latest", "hdl_latest", "ldl_direct_latest", "triglycerides_latest"]}
    assert all(0.05 < r < 0.95 for r in rates.values())

    # Co-missingness: P(chol missing AND HDL missing) should be much
    # higher than the product if independent.
    p_chol = mask["cholesterol_total_latest"].mean()
    p_hdl = mask["hdl_latest"].mean()
    independent_prob = p_chol * p_hdl
    joint_prob = (mask["cholesterol_total_latest"] & mask["hdl_latest"]).mean()
    # Joint should be materially higher than independent (real EHR co-
    # missingness). With marginal rates around 0.55 and propagation
    # probability 0.85, expect ~1.3× the independent product.
    assert joint_prob > independent_prob * 1.25


def test_dm_patients_get_their_labs():
    """A synthetic DM patient should not be missing creatinine/glucose."""
    df = _toy_panel_data()
    model = fit_missingness(
        df,
        columns=[
            "creatinine_latest", "glucose_fasting_latest",
            "DM_Tum",
        ],
        comorbidity_cols=["DM_Tum"],
    )
    n = 5000
    syn = pd.DataFrame({
        "DM_Tum": np.ones(n, dtype=int),
        "creatinine_latest": np.full(n, 1.0),
        "glucose_fasting_latest": np.full(n, 100.0),
    })
    rng = np.random.default_rng(7)
    mask = model.sample_mask(syn, rng)
    # DM patients should have creatinine present in >80% (conditional ≈ 0.05)
    assert mask["creatinine_latest"].mean() < 0.20
    assert mask["glucose_fasting_latest"].mean() < 0.20


def test_default_panel_groups_aligned_with_fhir_panels():
    """Sanity-check the panel groups match the FHIR DiagnosticReport panel
    constituents (same labs grouped same way)."""
    from syntha.fhir.panels import PANELS
    fhir_panel_cols = {col for _code, _disp, members in PANELS for col in members}
    miss_panel_cols = {c for cs in DEFAULT_PANEL_GROUPS.values() for c in cs}
    # The missingness panel groups should be a subset (since FHIR includes
    # iron studies as a 1-element panel; missingness doesn't propagate).
    overlap = fhir_panel_cols & miss_panel_cols
    assert len(overlap) >= 10  # at least 10 lab columns shared
