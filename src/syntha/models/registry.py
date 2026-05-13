"""Lightweight registry around copula model artifacts.

Each trained model is paired with a JSON ``ModelCard`` capturing:
  * source-CSV path and sha256;
  * cohort label and training row count;
  * trained-at timestamp and syntha version;
  * marginal summary (mean/std/quantiles) per modeled column;
  * top-K Spearman correlation pairs from the source data.

This is the same idea as a HuggingFace model card or Google's "Model Cards for
Model Reporting" — it makes a trained-model artifact reproducible, auditable,
and shippable.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .. import __version__
from ..generator.copula import GaussianCopulaGenerator


def _sha256(path: str | Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


@dataclass
class ModelCard:
    name: str
    cohort: str
    source_csv: str
    source_sha256: str
    n_train: int
    trained_at: str
    syntha_version: str
    binary_columns: list[str]
    continuous_columns: list[str]
    binary_marginals: dict[str, float] = field(default_factory=dict)
    continuous_summary: dict[str, dict] = field(default_factory=dict)
    top_correlations: list[dict] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str) -> ModelCard:
        return cls(**json.loads(text))


def _summarize(df: pd.DataFrame, bcols: list[str], ccols: list[str], top_k: int = 15):
    bmarginals = {c: float(df[c].mean(skipna=True)) for c in bcols}
    csummary = {}
    for c in ccols:
        s = df[c].dropna()
        if not len(s):
            continue
        csummary[c] = {
            "mean": float(s.mean()),
            "std": float(s.std()),
            "q05": float(s.quantile(0.05)),
            "q50": float(s.quantile(0.50)),
            "q95": float(s.quantile(0.95)),
            "n_observed": int(s.size),
        }
    corr = df[bcols + ccols].corr(method="spearman").stack()
    corr = corr[corr.index.get_level_values(0) < corr.index.get_level_values(1)]
    corr = corr.dropna().reindex(corr.abs().sort_values(ascending=False).index)
    top = [
        {"a": a, "b": b, "spearman": float(v)}
        for (a, b), v in corr.head(top_k).items()
    ]
    return bmarginals, csummary, top


class ModelRegistry:
    """Directory-backed registry: <root>/<name>/{model.pkl, card.json}."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def model_dir(self, name: str) -> Path:
        d = self.root / name
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save(
        self, name: str, generator: GaussianCopulaGenerator,
        source_csv: str | Path, training_df: pd.DataFrame,
        bcols: list[str], ccols: list[str], cohort: str,
    ) -> ModelCard:
        d = self.model_dir(name)
        generator.save(d / "model.pkl")
        bm, cs, top = _summarize(training_df, bcols, ccols)
        card = ModelCard(
            name=name, cohort=cohort,
            source_csv=str(source_csv),
            source_sha256=_sha256(source_csv),
            n_train=len(training_df),
            trained_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            syntha_version=__version__,
            binary_columns=bcols, continuous_columns=ccols,
            binary_marginals=bm, continuous_summary=cs, top_correlations=top,
        )
        (d / "card.json").write_text(card.to_json(), encoding="utf-8")
        return card

    def load(self, name: str) -> tuple[GaussianCopulaGenerator, ModelCard]:
        d = self.model_dir(name)
        gen = GaussianCopulaGenerator.load(d / "model.pkl")
        card = ModelCard.from_json((d / "card.json").read_text(encoding="utf-8"))
        return gen, card

    def list_models(self) -> list[str]:
        return sorted(p.name for p in self.root.iterdir() if (p / "model.pkl").exists())


def save_model(path: str | Path, generator: GaussianCopulaGenerator) -> None:
    generator.save(path)


def load_model(path: str | Path) -> GaussianCopulaGenerator:
    return GaussianCopulaGenerator.load(path)
