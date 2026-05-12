import json
from pathlib import Path

import numpy as np
import pandas as pd

from syntha.generator.copula import GaussianCopulaGenerator
from syntha.models.registry import ModelCard, ModelRegistry


def _toy_df(n=300, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "age": rng.normal(45, 10, n).round().astype(int),
        "gender_is_male": rng.binomial(1, 0.5, n),
        "bp_systolic": rng.normal(120, 10, n),
        "Hipertansiyon": rng.binomial(1, 0.2, n),
    })


def test_save_load_roundtrip(tmp_path):
    df = _toy_df()
    src_csv = tmp_path / "src.csv"
    df.to_csv(src_csv, index=False)
    gen = GaussianCopulaGenerator(random_seed=1).fit(
        df, binary_cols=["gender_is_male", "Hipertansiyon"],
        continuous_cols=["age", "bp_systolic"],
    )
    registry = ModelRegistry(tmp_path / "registry")
    card = registry.save(
        "copula_test", gen, src_csv, df,
        ["gender_is_male", "Hipertansiyon"], ["age", "bp_systolic"], cohort="test",
    )
    assert "copula_test" in registry.list_models()

    gen2, card2 = registry.load("copula_test")
    assert card2.source_sha256 == card.source_sha256
    s1 = gen.sample(20)
    s2 = gen2.sample(20)
    pd.testing.assert_frame_equal(s1, s2)


def test_model_card_summary_keys(tmp_path):
    df = _toy_df()
    src_csv = tmp_path / "src.csv"
    df.to_csv(src_csv, index=False)
    gen = GaussianCopulaGenerator(random_seed=2).fit(
        df, ["gender_is_male"], ["age", "bp_systolic"],
    )
    registry = ModelRegistry(tmp_path / "r")
    card = registry.save(
        "m", gen, src_csv, df,
        ["gender_is_male"], ["age", "bp_systolic"], cohort="test",
    )
    assert "age" in card.continuous_summary
    assert {"mean", "std", "q05", "q50", "q95"} <= set(card.continuous_summary["age"])
    assert isinstance(card.top_correlations, list)


def test_model_card_json_roundtrip():
    card = ModelCard(
        name="x", cohort="strict", source_csv="/tmp/a.csv",
        source_sha256="abc", n_train=100,
        trained_at="2026-05-12T00:00:00+00:00", syntha_version="0.1.0",
        binary_columns=["m"], continuous_columns=["age"],
    )
    text = card.to_json()
    json.loads(text)  # must be valid JSON
    card2 = ModelCard.from_json(text)
    assert card2.source_sha256 == "abc"
