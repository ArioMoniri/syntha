import json

import numpy as np
import pandas as pd

from syntha.validate import save_report, validate


def _twin_dfs(n=400, seed=0, shift=0.0):
    rng = np.random.default_rng(seed)
    src = pd.DataFrame({
        "age": rng.normal(45, 10, n),
        "bp_systolic": rng.normal(120, 12, n),
        "Hipertansiyon": rng.binomial(1, 0.2, n),
    })
    syn = pd.DataFrame({
        "age": rng.normal(45 + shift, 10, n),
        "bp_systolic": rng.normal(120 + shift, 12, n),
        "Hipertansiyon": rng.binomial(1, 0.2 + shift / 100, n),
    })
    return src, syn


def test_identical_distributions_have_low_ks():
    src, syn = _twin_dfs(seed=1)
    report = validate(
        src, syn,
        continuous_cols=["age", "bp_systolic"],
        binary_cols=["Hipertansiyon"],
    )
    assert all(c.ks_stat < 0.2 for c in report.continuous)
    assert all(b.abs_error < 0.1 for b in report.binary)


def test_shifted_distributions_have_high_ks():
    src, syn = _twin_dfs(seed=2, shift=30.0)
    report = validate(
        src, syn,
        continuous_cols=["age", "bp_systolic"],
        binary_cols=["Hipertansiyon"],
    )
    assert max(c.ks_stat for c in report.continuous) > 0.5


def test_save_report_roundtrip(tmp_path):
    src, syn = _twin_dfs(seed=3)
    report = validate(src, syn, ["age"], ["Hipertansiyon"])
    out = save_report(report, tmp_path / "report.json")
    data = json.loads(out.read_text())
    assert data["n_source"] == len(src)
    assert "continuous" in data and "binary" in data


def test_correlation_frobenius_nonzero_when_correlations_differ():
    rng = np.random.default_rng(4)
    n = 500
    age = rng.normal(45, 10, n)
    src = pd.DataFrame({"age": age, "bp": age * 0.6 + rng.normal(0, 5, n)})
    syn = pd.DataFrame({"age": age, "bp": age * 0.1 + rng.normal(0, 5, n)})
    report = validate(src, syn, ["age", "bp"], [])
    assert report.correlation_frobenius > 0.1
