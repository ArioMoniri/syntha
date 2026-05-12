import numpy as np
import pandas as pd

from syntha.generator.copula import GaussianCopulaGenerator


def _toy_df(n=500, seed=0):
    rng = np.random.default_rng(seed)
    age = rng.normal(45, 12, n).clip(18, 90)
    male = rng.binomial(1, 0.5, n)
    # Strong correlation: BP rises with age.
    sys_bp = 100 + 0.6 * age + rng.normal(0, 8, n)
    dia_bp = 60 + 0.3 * age + rng.normal(0, 5, n)
    htn = ((sys_bp > 140) | (dia_bp > 90)).astype(int)
    df = pd.DataFrame({
        "age": age, "gender_is_male": male,
        "bp_systolic": sys_bp, "bp_diastolic": dia_bp,
        "Hipertansiyon": htn,
    })
    return df


def test_fit_and_sample_shape():
    df = _toy_df()
    gen = GaussianCopulaGenerator(random_seed=1).fit(
        df, binary_cols=["gender_is_male", "Hipertansiyon"],
        continuous_cols=["age", "bp_systolic", "bp_diastolic"],
    )
    out = gen.sample(200)
    assert len(out) == 200
    assert set(out.columns) == set(df.columns)


def test_correlation_preserved_roughly():
    df = _toy_df(n=2000)
    gen = GaussianCopulaGenerator(random_seed=1).fit(
        df, binary_cols=["gender_is_male", "Hipertansiyon"],
        continuous_cols=["age", "bp_systolic", "bp_diastolic"],
    )
    sampled = gen.sample(2000)
    src_corr = df[["age", "bp_systolic"]].corr().iloc[0, 1]
    syn_corr = sampled[["age", "bp_systolic"]].corr().iloc[0, 1]
    # Both should show strong positive correlation by construction.
    assert src_corr > 0.5
    assert syn_corr > 0.4


def test_binary_marginals_approximate():
    df = _toy_df(n=2000)
    gen = GaussianCopulaGenerator(random_seed=2).fit(
        df, binary_cols=["gender_is_male"], continuous_cols=["age"],
    )
    sampled = gen.sample(5000)
    src_p = df["gender_is_male"].mean()
    syn_p = sampled["gender_is_male"].mean()
    assert abs(src_p - syn_p) < 0.05


def test_continuous_binary_correlation_sign_preserved():
    """Regression: an earlier implementation used X = 1{u < p}, which gave
    the right marginal but flipped the sign of every continuous↔binary
    correlation. Make sure positive source correlation stays positive."""
    rng = np.random.default_rng(11)
    n = 5000
    age = rng.normal(45, 12, n).clip(18, 90)
    # Higher age strongly increases HTN risk.
    logit = -3.0 + 0.08 * (age - 45)
    htn = (rng.random(n) < 1.0 / (1.0 + np.exp(-logit))).astype(int)
    df = pd.DataFrame({"age": age, "Hipertansiyon": htn})
    src_corr = df.corr(method="spearman").iloc[0, 1]
    assert src_corr > 0.15  # sanity: source has clear positive corr

    gen = GaussianCopulaGenerator(random_seed=1).fit(
        df, binary_cols=["Hipertansiyon"], continuous_cols=["age"],
    )
    syn = gen.sample(20_000)
    syn_corr = syn.corr(method="spearman").iloc[0, 1]
    # Sign must match — that's the regression we care about. Magnitude
    # attenuation is a known property of fitting Spearman correlations on
    # tied (binary) columns; see ROADMAP v0.6 (polyserial / tetrachoric).
    assert syn_corr > 0.05, f"expected positive corr, got {syn_corr:.3f}"
    assert (src_corr > 0) == (syn_corr > 0), "sign of correlation must match"


def test_save_load_roundtrip(tmp_path):
    df = _toy_df()
    gen = GaussianCopulaGenerator(random_seed=3).fit(
        df, binary_cols=["gender_is_male"], continuous_cols=["age"],
    )
    p = tmp_path / "m.pkl"
    gen.save(p)
    gen2 = GaussianCopulaGenerator.load(p)
    s1 = gen.sample(50)
    s2 = gen2.sample(50)
    pd.testing.assert_frame_equal(s1, s2)
