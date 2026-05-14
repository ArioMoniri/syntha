"""Tests for privacy attack module (G2)."""
import numpy as np
import pandas as pd

from syntha.privacy import (
    PrivacyReport,
    attribute_inference_attack,
    membership_inference_attack,
    run_privacy_audit,
)


def _toy_data(n_train=500, n_holdout=500, seed=0):
    """Make a real train + real holdout + 'good' synthetic (drawn from the
    SAME population but no copies). MIA should fail to distinguish."""
    rng = np.random.default_rng(seed)
    cols = ["age", "bp_systolic", "hdl_latest", "gender_is_male", "Hipertansiyon"]

    def draw(n):
        age = rng.normal(45, 12, n).clip(18, 90)
        male = rng.binomial(1, 0.5, n)
        bp = 110 + 0.4 * age + rng.normal(0, 8, n)
        hdl = 55 - 0.1 * age + rng.normal(0, 10, n) + male * (-5)
        htn = (bp > 140).astype(int)
        return pd.DataFrame({
            "age": age, "bp_systolic": bp, "hdl_latest": hdl,
            "gender_is_male": male, "Hipertansiyon": htn,
        })

    return draw(n_train), draw(n_holdout), draw(n_train), cols


def test_well_behaved_synthetic_passes_mia():
    """Synthetic drawn from same population (no memorization) should
    yield MIA AUC near 0.50."""
    real_train, real_holdout, synthetic, cols = _toy_data()
    auc = membership_inference_attack(real_train, real_holdout, synthetic, cols)
    # Should be close to 0.50 (no membership signal)
    assert 0.35 < auc < 0.65


def test_memorizing_synthetic_fails_mia():
    """If synthetic is just a copy of training data, MIA should detect it."""
    real_train, real_holdout, _, cols = _toy_data()
    synthetic = real_train.copy()  # full memorization
    auc = membership_inference_attack(real_train, real_holdout, synthetic, cols)
    # Memorization → AUC strongly above 0.5
    assert auc > 0.65, f"expected high MIA AUC, got {auc:.3f}"


def test_aia_finds_population_signal_but_not_individual():
    """Synthetic from same-population should let AIA recover the
    age→HTN signal that exists in the population, but no more than that."""
    _, real_holdout, synthetic, cols = _toy_data(n_train=2000, n_holdout=1000)
    auc = attribute_inference_attack(
        real_holdout, synthetic,
        public_cols=["age", "bp_systolic", "gender_is_male"],
        target_col="Hipertansiyon",
    )
    # HTN is deterministically (bp_systolic > 140) → AIA should recover it
    # well from synthetic since the (BP→HTN) signal is preserved. So this
    # is high but expected — sanity that the function works.
    assert auc > 0.85


def test_run_privacy_audit_overall_pass():
    real_train, real_holdout, synthetic, cols = _toy_data()
    report = run_privacy_audit(
        real_train, real_holdout, synthetic,
        feature_cols=cols,
        sensitive_targets=[],  # no sensitive AIA target → only MIA gates
    )
    assert isinstance(report, PrivacyReport)
    assert report.verdict == "pass"
    assert 0.40 < report.membership_inference_auc < 0.65


def test_run_privacy_audit_fails_on_memorization():
    real_train, real_holdout, _, cols = _toy_data()
    synthetic = real_train.copy()
    report = run_privacy_audit(
        real_train, real_holdout, synthetic,
        feature_cols=cols, sensitive_targets=[],
    )
    assert report.verdict == "fail"
    assert report.membership_inference_auc > 0.6
