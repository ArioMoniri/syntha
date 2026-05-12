"""Command-line interface for syntha."""
from __future__ import annotations

import json
from pathlib import Path

import click
import pandas as pd

from .generator.constraints import ConstraintConfig
from .generator.copula import GaussianCopulaGenerator
from .pipeline import PipelineConfig, run


@click.group()
@click.version_option()
def main() -> None:
    """syntha — synthetic patient record generator."""


@main.command()
@click.option("--input", "input_csv", required=True, type=click.Path(exists=True), help="Source pristine_*_episodes.csv")
@click.option("--output", "output_dir", required=True, type=click.Path(), help="Output directory")
@click.option("--n", default=1000, show_default=True, help="Number of synthetic episodes")
@click.option("--cohort", default="strict", show_default=True, help="Label for this cohort (strict/tolerant)")
@click.option("--seed", default=42, show_default=True)
@click.option("--csv/--no-csv", default=True, show_default=True)
@click.option("--fhir/--no-fhir", default=True, show_default=True)
@click.option("--fhir-format", type=click.Choice(["ndjson", "json"]), default="ndjson", show_default=True)
def generate(input_csv, output_dir, n, cohort, seed, csv, fhir, fhir_format):
    """Train copula, sample n synthetic episodes, write CSV + FHIR."""
    cfg = PipelineConfig(
        n=n, cohort=cohort, random_seed=seed,
        write_csv=csv, write_fhir=fhir, fhir_format=fhir_format,
    )
    result = run(input_csv, output_dir, cfg)
    click.echo(json.dumps(result, indent=2))


@main.command()
@click.option("--input", "input_csv", required=True, type=click.Path(exists=True))
@click.option("--output", "model_path", required=True, type=click.Path())
@click.option("--cohort", default="strict", show_default=True)
@click.option("--seed", default=42, show_default=True)
def fit(input_csv, model_path, cohort, seed):
    """Fit and save a copula model without sampling."""
    from . import data, preprocess

    src = data.load_episodes(input_csv)
    modeled = preprocess.coerce_types(data.filter_to_modeled(src))
    modeled = preprocess.clip_to_physiologic(modeled)
    feat_df, bcols, ccols = preprocess.split_modeled(modeled)
    gen = GaussianCopulaGenerator(random_seed=seed).fit(feat_df, bcols, ccols, cohort=cohort)
    gen.save(model_path)
    click.echo(json.dumps({"saved": str(model_path), "n_train": len(modeled)}, indent=2))


@main.command()
@click.option("--model", "model_path", required=True, type=click.Path(exists=True))
@click.option("--output", "output_csv", required=True, type=click.Path())
@click.option("--n", default=1000, show_default=True)
def sample(model_path, output_csv, n):
    """Sample n rows from a saved model (no FHIR, no constraints)."""
    gen = GaussianCopulaGenerator.load(model_path)
    df = gen.sample(n)
    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False)
    click.echo(json.dumps({"rows": len(df), "csv": output_csv}, indent=2))


@main.command()
@click.option("--input", "input_csv", required=True, type=click.Path(exists=True))
@click.option("--output", "output_dir", required=True, type=click.Path())
@click.option("--format", "fmt", type=click.Choice(["ndjson", "json"]), default="ndjson", show_default=True)
def fhir(input_csv, output_dir, fmt):
    """Convert an existing synthetic CSV to FHIR R4 bundles."""
    from .fhir.export import write_fhir_bundles
    df = pd.read_csv(input_csv)
    path = write_fhir_bundles(df, output_dir, fmt=fmt)
    click.echo(json.dumps({"rows": len(df), "fhir": str(path)}, indent=2))


if __name__ == "__main__":
    main()
