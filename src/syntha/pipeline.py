"""End-to-end orchestration: load → fit → sample → constrain → write CSV+FHIR."""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from . import data, preprocess
from .fhir.export import write_fhir_bundles
from .generator.constraints import ConstraintConfig, PhysiologicConstraints
from .generator.copula import GaussianCopulaGenerator


@dataclass
class PipelineConfig:
    n: int = 1000
    cohort: str = "strict"
    random_seed: int = 42
    oversample_factor: float = 1.5
    write_csv: bool = True
    write_fhir: bool = True
    fhir_format: str = "ndjson"
    constraint: ConstraintConfig = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.constraint is None:
            self.constraint = ConstraintConfig()


def _generate_ids_and_dates(
    n: int, date_lo: pd.Timestamp, date_hi: pd.Timestamp, seed: int
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    span = max((date_hi - date_lo).total_seconds(), 1.0)
    offsets = rng.random(n) * span
    dates = pd.to_datetime([date_lo + pd.Timedelta(seconds=float(o)) for o in offsets])
    return pd.DataFrame(
        {
            "RF_EPISODE2": [int(rng.integers(10_000_000, 99_999_999)) for _ in range(n)],
            "HASTA_ID": [f"SYN_{uuid.uuid4().hex[:8].upper()}" for _ in range(n)],
            "episode_date": dates,
        }
    )


def run(
    input_csv: str | Path,
    output_dir: str | Path,
    cfg: PipelineConfig,
) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    src = data.load_episodes(input_csv)
    date_lo, date_hi = data.date_range(src)
    modeled = data.filter_to_modeled(src)
    modeled = preprocess.coerce_types(modeled)
    modeled = preprocess.clip_to_physiologic(modeled)
    feat_df, bcols, ccols = preprocess.split_modeled(modeled)

    gen = GaussianCopulaGenerator(random_seed=cfg.random_seed).fit(
        feat_df, bcols, ccols, cohort=cfg.cohort
    )

    constraint = PhysiologicConstraints(cfg.constraint)

    collected: list[pd.DataFrame] = []
    rounds = 0
    target = cfg.n
    while sum(len(d) for d in collected) < target and rounds < 5:
        batch_n = max(1, math.ceil((target - sum(len(d) for d in collected)) * cfg.oversample_factor))
        raw = gen.sample(batch_n)
        kept, _ = constraint.apply(raw)
        collected.append(kept)
        rounds += 1
    final = pd.concat(collected, ignore_index=True).head(target).reset_index(drop=True)
    ids = _generate_ids_and_dates(len(final), date_lo, date_hi, cfg.random_seed + 1)
    synthetic = pd.concat([ids, final], axis=1)

    written: dict[str, str] = {}
    if cfg.write_csv:
        csv_path = out / f"synthetic_{cfg.cohort}_episodes.csv"
        synthetic.to_csv(csv_path, index=False)
        written["csv"] = str(csv_path)
    if cfg.write_fhir:
        fhir_path = write_fhir_bundles(synthetic, out / "fhir", fmt=cfg.fhir_format)
        written["fhir"] = str(fhir_path)

    model_path = out / f"copula_{cfg.cohort}.pkl"
    gen.save(model_path)
    written["model"] = str(model_path)

    return {
        "n_requested": cfg.n,
        "n_generated": len(synthetic),
        "rounds": rounds,
        "cohort": cfg.cohort,
        "training_rows": len(modeled),
        **written,
    }
