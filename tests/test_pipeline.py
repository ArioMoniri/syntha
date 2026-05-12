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
    assert Path(result["model"]).exists()

    syn = pd.read_csv(result["csv"])
    assert (syn["bp_systolic"] >= syn["bp_diastolic"]).all()

    with open(result["fhir"]) as f:
        first = json.loads(f.readline())
    assert first["resourceType"] == "Bundle"
