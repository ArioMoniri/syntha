"""Command-line interface for syntha."""
from __future__ import annotations

import json
from pathlib import Path

import click
import numpy as np
import pandas as pd

from .generator.copula import GaussianCopulaGenerator
from .models.registry import ModelRegistry
from .pipeline import PipelineConfig, run


from . import __version__ as _syntha_version


@click.group()
@click.version_option(_syntha_version, prog_name="syntha", package_name="syntha-ehr")
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
@click.option("--lab-history/--no-lab-history", default=False, show_default=True,
              help="Emit 2-4 prior measurements per lab (v0.5.5 longitudinal labs)")
@click.option("--conditional-missingness/--no-conditional-missingness", default=True,
              show_default=True, help="Apply comorbidity-conditional missingness (v0.5.2)")
@click.option("--validation/--no-validation", default=True, show_default=True,
              help="Compute KS/Wasserstein/correlation report alongside output")
def generate(input_csv, output_dir, n, cohort, seed, csv, fhir, fhir_format,
             modules, longitudinal, encounters_per_patient, years_of_history,
             registry_dir, lab_history, conditional_missingness, validation):
    """Train copula, sample, run modules, write CSV + FHIR + model card."""
    cfg = PipelineConfig(
        n=n, cohort=cohort, random_seed=seed,
        write_csv=csv, write_fhir=fhir, fhir_format=fhir_format,
        run_modules=modules, longitudinal=longitudinal,
        encounters_per_patient_mean=encounters_per_patient,
        years_of_history=years_of_history, registry_dir=registry_dir,
        write_validation=validation,
        apply_conditional_missingness=conditional_missingness,
        include_lab_history=lab_history,
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


@main.command(name="sample-conditional")
@click.option("--registry", "registry_dir", required=True, type=click.Path(exists=True))
@click.option("--name", required=True)
@click.option("--output", "output_csv", required=True, type=click.Path())
@click.option("--n", default=1000, show_default=True, help="Target number of accepted rows")
@click.option(
    "--condition",
    required=True,
    help=(
        "pandas-style filter expression in the model's column names. "
        'Example: --condition "age > 60 & DM_Tum == 1 & bp_systolic >= 140"'
    ),
)
@click.option("--oversample", default=5.0, show_default=True,
              help="Initial oversample factor for rejection sampling")
@click.option("--max-rounds", default=10, show_default=True)
def sample_conditional_cmd(registry_dir, name, output_csv, n, condition,
                            oversample, max_rounds):
    """Conditional sampling via rejection — return only rows matching --condition."""
    from .conditional import sample_conditional
    registry = ModelRegistry(registry_dir)
    gen, _ = registry.load(name)
    result = sample_conditional(
        gen, n=n, condition=condition,
        oversample_factor=oversample, max_rounds=max_rounds,
    )
    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    result.rows.to_csv(output_csv, index=False)
    click.echo(json.dumps({
        "n_requested": result.n_requested,
        "n_generated": result.n_generated,
        "rounds": result.rounds,
        "rejection_rate": round(result.rejection_rate, 3),
        "csv": output_csv,
    }, indent=2))


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


@main.command(name="validate")
@click.option("--source", "source_csv", required=True, type=click.Path(exists=True))
@click.option("--synthetic", "synthetic_csv", required=True, type=click.Path(exists=True))
@click.option("--output", "report_path", required=True, type=click.Path())
def validate_cmd(source_csv, synthetic_csv, report_path):
    """Compute KS / Wasserstein / correlation-diff between source and synthetic.

    (CLI command name is `validate`; the Python function is `validate_cmd`
    to avoid shadowing the `validate.validate` module function — per the
    v0.5 architecture review.)
    """
    from . import data, preprocess
    from .validate import save_report
    from .validate import validate as _v

    src = preprocess.coerce_types(data.filter_to_modeled(data.load_episodes(source_csv)))
    syn = pd.read_csv(synthetic_csv)
    _, bcols, ccols = preprocess.split_modeled(src)
    report = _v(src, syn, ccols, bcols)
    save_report(report, report_path)
    click.echo(json.dumps(report.summary(), indent=2))


@main.command()
@click.option("--source", "source_csv", required=True, type=click.Path(exists=True))
@click.option("--synthetic", "synthetic_csv", required=True, type=click.Path(exists=True))
@click.option("--output", "report_path", required=True, type=click.Path())
@click.option("--split", default=0.8, show_default=True,
              help="Fraction of source used as train (rest is held out for the attack)")
def audit(source_csv, synthetic_csv, report_path, split):
    """Run a privacy audit (membership + attribute inference attacks) against
    a synthetic CSV and write a JSON report. CI fails on MIA AUC > 0.60."""
    from . import data, preprocess
    from .privacy import DEFAULT_MIA_THRESHOLD, run_privacy_audit

    src = preprocess.coerce_types(data.filter_to_modeled(data.load_episodes(source_csv)))
    syn = pd.read_csv(synthetic_csv)
    rng = np.random.default_rng(42)
    idx = rng.permutation(len(src))
    n_train = int(split * len(src))
    real_train = src.iloc[idx[:n_train]].copy()
    real_holdout = src.iloc[idx[n_train:]].copy()

    feature_cols = [c for c in src.columns if c in syn.columns
                    and c not in ("RF_EPISODE2", "HASTA_ID", "episode_date", "gender")]
    sensitive_targets = [c for c in ["Hipertansiyon", "DM_Tum", "Hiperlipidemi"]
                         if c in feature_cols]

    report = run_privacy_audit(
        real_train, real_holdout, syn,
        feature_cols=feature_cols,
        sensitive_targets=sensitive_targets,
    )
    summary = report.summary()
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    Path(report_path).write_text(json.dumps(summary, indent=2))
    click.echo(json.dumps(summary, indent=2))
    if summary["membership_inference_auc"] > DEFAULT_MIA_THRESHOLD:
        raise click.ClickException(
            f"membership inference AUC {summary['membership_inference_auc']:.3f} > "
            f"{DEFAULT_MIA_THRESHOLD} — possible memorization"
        )


if __name__ == "__main__":
    main()
