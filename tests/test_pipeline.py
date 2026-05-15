import json
from pathlib import Path

import numpy as np
import pandas as pd

from syntha.pipeline import PipelineConfig, run


def _write_tiny_csv(path: Path, n: int = 400, seed: int = 0):
    rng = np.random.default_rng(seed)
    age = rng.normal(45, 12, n).clip(18, 85).round().astype(int)
    male = rng.binomial(1, 0.5, n)
    sys_bp = (100 + 0.6 * age + rng.normal(0, 8, n)).round(1)
    dia_bp = (60 + 0.3 * age + rng.normal(0, 5, n)).round(1)
    df = pd.DataFrame({
        "RF_EPISODE2": np.arange(n),
        "HASTA_ID": [f"ANON_{i:06d}" for i in range(n)],
        "episode_date": pd.date_range("2018-01-01", periods=n, freq="h").astype(str),
        "age": age, "gender_is_male": male, "gender": np.where(male == 1, "M", "F"),
        "bp_systolic": sys_bp, "bp_diastolic": dia_bp,
        "hemoglobin_latest": rng.normal(14, 1.5, n).clip(8, 18).round(1),
        "glucose_fasting_latest": rng.normal(95, 12, n).clip(60, 160).round(1),
        "creatinine_latest": rng.normal(0.9, 0.15, n).clip(0.4, 2.0).round(2),
        "egfr_latest": rng.normal(95, 12, n).clip(40, 130).round(1),
        "Hipertansiyon": (sys_bp > 140).astype(int),
        "DM_Tum": rng.binomial(1, 0.08, n),
        "pristine_strict": 1, "pristine_tolerant": 1, "tier_healthy_episode": 1,
    })
    df.to_csv(path, index=False)


def test_pipeline_end_to_end(tmp_path):
    src = tmp_path / "src.csv"
    _write_tiny_csv(src)
    out = tmp_path / "out"
    result = run(
        src, out,
        PipelineConfig(n=50, cohort="strict", random_seed=7),
    )
    assert result["n_generated"] == 50
    assert Path(result["csv"]).exists()
    assert Path(result["fhir"]).exists()
    assert Path(result["model_dir"]).exists()
    assert (Path(result["model_dir"]) / "card.json").exists()

    syn = pd.read_csv(result["csv"])
    assert (syn["bp_systolic"] >= syn["bp_diastolic"]).all()

    with open(result["fhir"]) as f:
        first = json.loads(f.readline())
    assert first["resourceType"] == "Bundle"


def test_curation_flags_dropped_by_default(tmp_path):
    """v0.5.6: curation flags (pristine_*, berturk_*, drug-safety, rf_*)
    are training metadata, not clinical observations. The default CSV
    output should not include them."""
    src = tmp_path / "src.csv"
    _write_tiny_csv(src)
    out = tmp_path / "out_clean"
    result = run(src, out, PipelineConfig(n=30, cohort="strict", random_seed=11))
    syn = pd.read_csv(result["csv"])

    from syntha import schema
    for col in schema.CURATION_COLUMNS:
        assert col not in syn.columns, (
            f"curation flag {col!r} leaked into default CSV output"
        )
    # Clinical columns should survive the filter.
    for col in ["age", "bp_systolic", "Hipertansiyon", "DM_Tum"]:
        if col in syn.columns:
            break
    else:
        raise AssertionError("no clinical columns survived — filter is too aggressive")
    # Identifiers must be present (we synthesize them post-sample).
    for col in ("RF_EPISODE2", "HASTA_ID", "episode_date"):
        assert col in syn.columns, f"identifier {col!r} missing from CSV"


def test_curation_flags_opt_in(tmp_path):
    """include_curation_flags=True preserves backwards-compat shape."""
    src = tmp_path / "src.csv"
    _write_tiny_csv(src)
    out = tmp_path / "out_full"
    result = run(
        src, out,
        PipelineConfig(
            n=30, cohort="strict", random_seed=13,
            include_curation_flags=True,
        ),
    )
    syn = pd.read_csv(result["csv"])
    # The CSV should now contain at least one curation flag that the
    # source had (pristine_strict is set on every row in the fixture).
    assert "pristine_strict" in syn.columns


def test_model_export_v2_metadata(tmp_path):
    """Exported JSON should declare format v2 and carry the curation list
    + a date window (falls back to the registered source CSV's range)."""
    from syntha.export_model import export_model_to_json
    from syntha.models.registry import ModelRegistry

    src = tmp_path / "src.csv"
    _write_tiny_csv(src)
    out = tmp_path / "out"
    run(src, out, PipelineConfig(
        n=30, cohort="strict", random_seed=5,
        write_fhir=False, write_validation=False,
    ))
    gen, _card = ModelRegistry(str(out / "models")).load("copula_strict")
    payload_path = tmp_path / "model.json"
    export_model_to_json(
        gen, payload_path, n_quantiles=64,
        date_lo="2020-01-01", date_hi="2021-12-31",
    )
    payload = json.loads(payload_path.read_text())
    assert payload["format"] == "syntha-copula-v2"
    assert payload["date_lo"] == "2020-01-01"
    assert payload["date_hi"] == "2021-12-31"
    assert len(payload["curation_columns"]) >= 25
