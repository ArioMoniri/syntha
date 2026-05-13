"""Tests for conditional sampling via rejection."""
import numpy as np
import pandas as pd
import pytest

from syntha.conditional import sample_conditional
from syntha.generator.copula import GaussianCopulaGenerator


def _fit_toy(n=2000, seed=0):
    rng = np.random.default_rng(seed)
    age = rng.normal(45, 12, n).clip(18, 90)
    male = rng.binomial(1, 0.5, n)
    bp_sys = 110 + 0.4 * age + rng.normal(0, 8, n)
    htn = (bp_sys > 140).astype(int)
    df = pd.DataFrame({
        "age": age, "gender_is_male": male,
        "bp_systolic": bp_sys, "Hipertansiyon": htn,
    })
    gen = GaussianCopulaGenerator(random_seed=1).fit(
        df, binary_cols=["gender_is_male", "Hipertansiyon"],
        continuous_cols=["age", "bp_systolic"],
    )
    return gen


def test_simple_continuous_condition():
    gen = _fit_toy()
    result = sample_conditional(gen, n=200, condition="age > 60")
    assert len(result.rows) == 200
    assert (result.rows["age"] > 60).all()


def test_compound_condition():
    gen = _fit_toy()
    # This condition has ~5% prevalence in the toy data — bump oversample.
    result = sample_conditional(
        gen, n=50,
        condition="age > 50 & Hipertansiyon == 1 & gender_is_male == 1",
        oversample_factor=20, max_rounds=15,
    )
    assert len(result.rows) == 50
    assert (result.rows["age"] > 50).all()
    assert (result.rows["Hipertansiyon"] == 1).all()
    assert (result.rows["gender_is_male"] == 1).all()


def test_disallowed_constructs_rejected():
    gen = _fit_toy()
    # Attribute access
    with pytest.raises(ValueError, match="(disallowed|Attribute|unknown name)"):
        sample_conditional(gen, n=10, condition="age.__class__")
    # Function call
    with pytest.raises(ValueError, match="(disallowed|Call|unknown name)"):
        sample_conditional(gen, n=10, condition="__import__('os')")
    # Subscript
    with pytest.raises(ValueError, match="(disallowed|Subscript|unknown name)"):
        sample_conditional(gen, n=10, condition="age[0] > 60")


def test_unknown_column_rejected():
    gen = _fit_toy()
    with pytest.raises(ValueError, match="unknown name"):
        sample_conditional(gen, n=10, condition="not_a_real_column > 0")


def test_rejection_rate_reported():
    gen = _fit_toy()
    # Very selective condition.
    result = sample_conditional(
        gen, n=20, condition="age > 70 & Hipertansiyon == 1",
        oversample_factor=20, max_rounds=10,
    )
    assert result.n_generated >= 1
    assert 0.0 <= result.rejection_rate <= 1.0


def test_unsatisfiable_condition_returns_partial_with_rounds_capped():
    gen = _fit_toy()
    # Condition that can never be true at the same time.
    result = sample_conditional(
        gen, n=10, condition="age > 200", max_rounds=2,
    )
    assert result.n_generated == 0
    assert result.rounds == 2
