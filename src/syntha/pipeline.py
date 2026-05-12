"""End-to-end orchestration: load → fit → sample → constrain → expand → write."""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from . import data, preprocess
from .fhir.export import write_fhir_bundles
from .generator.constraints import ConstraintConfig, PhysiologicConstraints
from .generator.copula import GaussianCopulaGenerator
from .longitudinal import TrajectoryConfig, expand_to_trajectories
from .models.registry import ModelRegistry
from .validate import save_report, validate


@dataclass
class PipelineConfig:
    n: int = 1000
    cohort: str = "strict"
    random_seed: int = 42
    oversample_factor: float = 1.5
    write_csv: bool = True
    write_fhir: bool = True
    fhir_format: str = "ndjson"
    run_modules: bool = True
    longitudinal: bool = False
    encounters_per_patient_mean: float = 4.0
    years_of_history: float = 3.0
    constraint: ConstraintConfig = field(default_factory=ConstraintConfig)
    registry_dir: str | None = None
    write_validation: bool = True


def _generate_ids_and_dates(
    n: int, date_lo: pd.Timestamp, date_hi: pd.Timestamp, seed: int
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    span = max((date_hi - date_lo).total_seconds(), 1.0)
    offsets = rng.random(n) * span
    dates = pd.to_datetime([date_lo + pd.Timedelta(seconds=float(o)) for o in offsets])
    return pd.DataFrame({
        "RF_EPISODE2": [int(rng.integers(10_000_000, 99_999_999)) for _ in range(n)],
        "HASTA_ID": [f"SYN_{uuid.uuid4().hex[:8].upper()}" for _ in range(n)],
        "episode_date": dates,
    })


def _sample_until(
    gen: GaussianCopulaGenerator,
    constraint: PhysiologicConstraints,
    target: int,
    oversample_factor: float,
    max_rounds: int = 5,
) -> pd.DataFrame:
    collected: list[pd.DataFrame] = []
    rounds = 0
    while sum(len(d) for d in collected) < target and rounds < max_rounds:
        deficit = target - sum(len(d) for d in collected)
        batch = max(1, math.ceil(deficit * oversample_factor))
        raw = gen.sample(batch)
        kept, _ = constraint.apply(raw)
        collected.append(kept)
        rounds += 1
    return pd.concat(collected, ignore_index=True).head(target).reset_index(drop=True)


def run(input_csv, output_dir, cfg: PipelineConfig) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    src = data.load_episodes(input_csv)
    date_lo, date_hi = data.date_range(src)
    modeled = preprocess.clip_to_physiologic(
        preprocess.coerce_types(data.filter_to_modeled(src))
    )
    feat_df, bcols, ccols = preprocess.split_modeled(modeled)

    gen = GaussianCopulaGenerator(random_seed=cfg.random_seed).fit(
        feat_df, bcols, ccols, cohort=cfg.cohort,
    )

    constraint = PhysiologicConstraints(cfg.constraint)
    target_baselines = cfg.n if not cfg.longitudinal else max(1, cfg.n // max(1, int(cfg.encounters_per_patient_mean)))
    baselines = _sample_until(gen, constraint, target_baselines, cfg.oversample_factor)
    ids = _generate_ids_and_dates(len(baselines), date_lo, date_hi, cfg.random_seed + 1)
    baselines = pd.concat([ids, baselines], axis=1)

    if cfg.longitudinal:
        traj_cfg = TrajectoryConfig(
            encounters_per_patient_mean=cfg.encounters_per_patient_mean,
            years_of_history=cfg.years_of_history,
            random_seed=cfg.random_seed + 2,
        )
        synthetic = expand_to_trajectories(baselines, date_lo, date_hi, traj_cfg)
        synthetic, _ = constraint.apply(synthetic)
    else:
        synthetic = baselines

    written: dict[str, str] = {}
    if cfg.write_csv:
        csv_path = out / f"synthetic_{cfg.cohort}_episodes.csv"
        synthetic.to_csv(csv_path, index=False)
        written["csv"] = str(csv_path)
    if cfg.write_fhir:
        fhir_path = write_fhir_bundles(
            synthetic, out / "fhir", fmt=cfg.fhir_format, run_modules=cfg.run_modules,
        )
        written["fhir"] = str(fhir_path)

    registry_root = cfg.registry_dir or str(out / "models")
    registry = ModelRegistry(registry_root)
    card = registry.save(
        name=f"copula_{cfg.cohort}", generator=gen,
        source_csv=input_csv, training_df=modeled,
        bcols=bcols, ccols=ccols, cohort=cfg.cohort,
    )
    written["model_dir"] = str(registry.model_dir(card.name))

    validation_summary: dict | None = None
    if cfg.write_validation:
        report = validate(modeled, synthetic, ccols, bcols)
        report_path = out / "validation_report.json"
        save_report(report, report_path)
        written["validation_report"] = str(report_path)
        validation_summary = report.summary()

    return {
        "n_requested": cfg.n,
        "n_generated": len(synthetic),
        "n_baselines": len(baselines),
        "longitudinal": cfg.longitudinal,
        "cohort": cfg.cohort,
        "training_rows": len(modeled),
        "source_sha256": card.source_sha256,
        "validation": validation_summary,
        **written,
    }
