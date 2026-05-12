"""Command-line interface for syntha."""
from __future__ import annotations

import json
from pathlib import Path

import click
import pandas as pd

from .generator.copula import GaussianCopulaGenerator
from .models.registry import ModelRegistry
from .pipeline import PipelineConfig, run


@click.group()
@click.version_option()
def main() -> None:
    """syntha — synthetic patient record generator."""


@main.command()
@click.option("--input", "input_csv", required=True, type=click.Path(exists=True))
@click.option("--output", "output_dir", required=True, type=click.Path())
@click.option("--n", default=1000, show_default=True, help="Number of synthetic episodes (or total encounters in longitudinal mode)")
@click.option("--cohort", default="strict", show_default=True)
@click.option("--seed", default=42, show_default=True)
@click.option("--csv/--no-csv", default=True, show_default=True)
@click.option("--fhir/--no-fhir", default=True, show_default=True)
@click.option("--fhir-format", type=click.Choice(["ndjson", "json"]), default="ndjson", show_default=True)
@click.option("--modules/--no-modules", default=True, show_default=True, help="Run Synthea-style clinical modules during FHIR export")
@click.option("--longitudinal", is_flag=True, default=False, help="Expand each baseline into multiple encounters over time")
@click.option("--encounters-per-patient", default=4.0, show_default=True)
@click.option("--years-of-history", default=3.0, show_default=True)
@click.option("--registry-dir", default=None, help="Directory for the trained-model registry (default: <output>/models)")
def generate(input_csv, output_dir, n, cohort, seed, csv, fhir, fhir_format,
             modules, longitudinal, encounters_per_patient, years_of_history,
             registry_dir):
    """Train copula, sample, run modules, write CSV + FHIR + model card."""
    cfg = PipelineConfig(
        n=n, cohort=cohort, random_seed=seed,
        write_csv=csv, write_fhir=fhir, fhir_format=fhir_format,
        run_modules=modules, longitudinal=longitudinal,
        encounters_per_patient_mean=encounters_per_patient,
        years_of_history=years_of_history, registry_dir=registry_dir,
    )
    click.echo(json.dumps(run(input_csv, output_dir, cfg), indent=2))


@main.command()
@click.option("--input", "input_csv", required=True, type=click.Path(exists=True))
@click.option("--registry", "registry_dir", required=True, type=click.Path())
@click.option("--name", required=True)
@click.option("--cohort", default="strict", show_default=True)
@click.option("--seed", default=42, show_default=True)
def fit(input_csv, registry_dir, name, cohort, seed):
    """Fit a copula and store it (with model card) in the registry."""
    from . import data, preprocess
    src = data.load_episodes(input_csv)
    modeled = preprocess.clip_to_physiologic(
        preprocess.coerce_types(data.filter_to_modeled(src))
    )
    feat_df, bcols, ccols = preprocess.split_modeled(modeled)
    gen = GaussianCopulaGenerator(random_seed=seed).fit(feat_df, bcols, ccols, cohort=cohort)
    registry = ModelRegistry(registry_dir)
    card = registry.save(name, gen, input_csv, modeled, bcols, ccols, cohort)
    click.echo(json.dumps({
        "registry": str(registry_dir), "name": name,
        "n_train": card.n_train, "source_sha256": card.source_sha256,
    }, indent=2))


@main.command(name="list-models")
@click.option("--registry", "registry_dir", required=True, type=click.Path(exists=True))
def list_models(registry_dir):
    """List models in a registry."""
    registry = ModelRegistry(registry_dir)
    click.echo(json.dumps(registry.list_models(), indent=2))


@main.command(name="show-card")
@click.option("--registry", "registry_dir", required=True, type=click.Path(exists=True))
@click.option("--name", required=True)
def show_card(registry_dir, name):
    """Show a model card."""
    registry = ModelRegistry(registry_dir)
    _, card = registry.load(name)
    click.echo(card.to_json())


@main.command()
@click.option("--registry", "registry_dir", required=True, type=click.Path(exists=True))
@click.option("--name", required=True)
@click.option("--output", "output_csv", required=True, type=click.Path())
@click.option("--n", default=1000, show_default=True)
def sample(registry_dir, name, output_csv, n):
    """Sample n rows from a registered model (raw — no constraints, no FHIR)."""
    registry = ModelRegistry(registry_dir)
    gen, _ = registry.load(name)
    df = gen.sample(n)
    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False)
    click.echo(json.dumps({"rows": len(df), "csv": output_csv}, indent=2))


@main.command()
@click.option("--input", "input_csv", required=True, type=click.Path(exists=True))
@click.option("--output", "output_dir", required=True, type=click.Path())
@click.option("--format", "fmt", type=click.Choice(["ndjson", "json"]), default="ndjson", show_default=True)
@click.option("--modules/--no-modules", default=True, show_default=True)
def fhir(input_csv, output_dir, fmt, modules):
    """Convert an existing synthetic CSV to FHIR R4 bundles."""
    from .fhir.export import write_fhir_bundles
    df = pd.read_csv(input_csv)
    path = write_fhir_bundles(df, output_dir, fmt=fmt, run_modules=modules)
    click.echo(json.dumps({"rows": len(df), "fhir": str(path)}, indent=2))


if __name__ == "__main__":
    main()
