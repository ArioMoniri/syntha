"""CLI smoke tests for `syntha generate` and friends.

Covers the v0.5 architecture review gap (no tests/test_cli.py before this).
Each test invokes the click command directly via CliRunner so we exercise
option parsing, default values, and the pipeline end-to-end without
shelling out.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from click.testing import CliRunner

from syntha.cli import main


def _write_tiny_csv(path: Path, n: int = 300, seed: int = 0) -> None:
    rng = np.random.default_rng(seed)
    age = rng.normal(50, 10, n).clip(20, 80).round().astype(int)
    male = rng.binomial(1, 0.5, n)
    sys_bp = (105 + 0.55 * age + rng.normal(0, 7, n)).round(1)
    dia_bp = (62 + 0.28 * age + rng.normal(0, 5, n)).round(1)
    pd.DataFrame({
        "RF_EPISODE2": np.arange(n),
        "HASTA_ID": [f"ANON_{i:05d}" for i in range(n)],
        "episode_date": pd.date_range("2019-01-01", periods=n, freq="h").astype(str),
        "age": age, "gender_is_male": male,
        "gender": np.where(male == 1, "M", "F"),
        "bp_systolic": sys_bp, "bp_diastolic": dia_bp,
        "hemoglobin_latest": rng.normal(14, 1.3, n).clip(9, 18).round(1),
        "glucose_fasting_latest": rng.normal(95, 12, n).clip(60, 160).round(1),
        "creatinine_latest": rng.normal(0.9, 0.15, n).clip(0.4, 2.0).round(2),
        "egfr_latest": rng.normal(95, 12, n).clip(40, 130).round(1),
        "Hipertansiyon": (sys_bp > 140).astype(int),
        "DM_Tum": rng.binomial(1, 0.08, n),
        "pristine_strict": 1, "pristine_tolerant": 1, "tier_healthy_episode": 1,
        "berturk_similarity": rng.uniform(0.6, 0.95, n).round(3),
        "drug_safe": 1, "has_rx_data": rng.binomial(1, 0.7, n),
    }).to_csv(path, index=False)


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "syntha" in result.output.lower()


def test_cli_generate_writes_csv_and_drops_curation(tmp_path):
    src = tmp_path / "src.csv"
    _write_tiny_csv(src)
    out = tmp_path / "out"
    runner = CliRunner()
    result = runner.invoke(main, [
        "generate",
        "--input", str(src), "--output", str(out),
        "--n", "40", "--cohort", "strict", "--seed", "7",
        "--no-fhir", "--no-validation",
    ])
    assert result.exit_code == 0, result.output
    summary = json.loads(result.output)
    csv_path = Path(summary["csv"])
    assert csv_path.exists()
    df = pd.read_csv(csv_path)
    # Default is --no-curation-flags ⇒ pristine_* / berturk_similarity dropped.
    for col in ("pristine_strict", "berturk_similarity", "drug_safe"):
        assert col not in df.columns, (
            f"curation flag {col!r} leaked into default CSV"
        )
    # Identifiers should be present.
    for col in ("RF_EPISODE2", "HASTA_ID", "episode_date"):
        assert col in df.columns


def test_cli_generate_curation_flags_optin(tmp_path):
    src = tmp_path / "src.csv"
    _write_tiny_csv(src)
    out = tmp_path / "out"
    runner = CliRunner()
    result = runner.invoke(main, [
        "generate",
        "--input", str(src), "--output", str(out),
        "--n", "20", "--cohort", "strict", "--seed", "3",
        "--no-fhir", "--no-validation", "--curation-flags",
    ])
    assert result.exit_code == 0, result.output
    df = pd.read_csv(json.loads(result.output)["csv"])
    assert "pristine_strict" in df.columns
