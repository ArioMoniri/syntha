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


@main.command(name="export-model")
@click.option("--registry", "registry_dir", required=True, type=click.Path(exists=True))
@click.option("--name", required=True)
@click.option("--output", "output_path", required=True, type=click.Path())
@click.option("--quantiles", default=200, show_default=True, help="Order statistics per continuous marginal")
def export_model(registry_dir, name, output_path, quantiles):
    """Export a registered copula to JSON for use by the Tauri desktop app."""
    from .export_model import export_model_to_json
    gen, card = ModelRegistry(registry_dir).load(name)
    path = export_model_to_json(gen, output_path, n_quantiles=quantiles)
    click.echo(json.dumps({
        "path": str(path), "cohort": card.cohort,
        "n_train": card.n_train, "size_kb": path.stat().st_size // 1024,
    }, indent=2))


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


@main.command()
@click.option("--bundles", "bundles_ndjson", required=True, type=click.Path(exists=True), help="Path to bundles.ndjson")
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8080, show_default=True)
def serve(bundles_ndjson, host, port):
    """Boot a minimal read-only FHIR R4 server backed by a bundles NDJSON file."""
    from .server import serve_forever
    serve_forever(bundles_ndjson, host=host, port=port)


@main.command()
@click.option("--source", "source_csv", required=True, type=click.Path(exists=True))
@click.option("--synthetic", "synthetic_csv", required=True, type=click.Path(exists=True))
@click.option("--output", "report_path", required=True, type=click.Path())
def validate(source_csv, synthetic_csv, report_path):
    """Compute KS / Wasserstein / correlation-diff between source and synthetic."""
    from . import data, preprocess
    from .validate import save_report
    from .validate import validate as _v

    src = preprocess.coerce_types(data.filter_to_modeled(data.load_episodes(source_csv)))
    syn = pd.read_csv(synthetic_csv)
    _, bcols, ccols = preprocess.split_modeled(src)
    report = _v(src, syn, ccols, bcols)
    save_report(report, report_path)
    click.echo(json.dumps(report.summary(), indent=2))


if __name__ == "__main__":
    main()
