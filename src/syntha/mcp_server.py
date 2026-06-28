"""Model Context Protocol (MCP) server for syntha.

Exposes the synthetic-cohort generator as a set of tools any
MCP-compatible client (Claude Desktop, Claude Web custom connector,
mcp-cli, Cursor, Continue, etc.) can invoke. Two transports are
supported:

  * ``stdio`` (default) — for Claude Desktop and other local hosts.
  * ``http``           — for the Claude.com web "custom connector"
                          slot, which speaks Streamable HTTP.

Tools (all sample from the bundled v2 copula JSONs — no source CSV
required at runtime):

  * ``list_bundled_cohorts``       — cohorts shipped with syntha
                                      (``tolerant``, ``strict``)
  * ``get_cohort_summary``         — n_train, marginal prevalences,
                                      modeled columns, source-data
                                      provenance
  * ``generate_cohort_csv``        — N synthetic patients as a CSV
                                      string (physiologic constraints
                                      applied by default)
  * ``generate_cohort_fhir``       — N synthetic patients as a FHIR R4
                                      transaction-Bundle NDJSON string
  * ``sample_conditional``         — AST-validated rejection sampling
                                      against a pandas-style filter
                                      expression ("age > 60 & DM_Tum
                                      == 1 & bp_systolic >= 140")
  * ``list_clinical_modules``      — the nine Synthea-style modules
  * ``list_physiologic_constraints`` — the four physiologic-validity
                                       rejection rules
  * ``syntha_version``             — version + commit-hash provenance

Run as ``syntha-mcp`` (installed by the ``[mcp]`` extra) or
``python -m syntha.mcp_server``.
"""
from __future__ import annotations

import io
import json
import os
import sys
from importlib import resources
from pathlib import Path
from typing import Literal

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:  # pragma: no cover — clear error for misinstalls
    raise SystemExit(
        "The 'mcp' Python SDK is required for syntha-mcp.\n"
        "Install: pip install 'syntha-ehr[mcp]'   "
        "(or:  pip install 'mcp>=1.2')"
    ) from e

import pandas as pd

from . import __version__ as _syntha_version
from . import schema as _schema
from .export_model import load_generator_from_json
from .generator.constraints import ConstraintConfig, PhysiologicConstraints

# Bundled cohorts — name → JSON resource basename
_COHORTS: dict[str, str] = {"tolerant": "tolerant.json", "strict": "strict.json"}

_app = FastMCP(
    name="syntha",
    instructions=(
        "syntha generates locale-aware (Turkish primary-care) synthetic "
        "patient cohorts trained on de-identified retrospective EHR "
        "episodes. Use `generate_cohort_csv` for a flat CSV, "
        "`generate_cohort_fhir` for FHIR R4 transaction Bundles, "
        "`sample_conditional` for rejection-sampled subsets matching a "
        "filter expression, and `get_cohort_summary` to inspect what each "
        "bundled cohort (tolerant / strict) actually models. "
        "All outputs are synthetic: no real-patient row is ever returned."
    ),
)


# ───────────────────────── helpers ─────────────────────────


def _load_bundled(cohort: str, seed: int = 42):
    """Read a bundled cohort JSON via importlib.resources."""
    if cohort not in _COHORTS:
        raise ValueError(
            f"unknown cohort {cohort!r}; valid: {sorted(_COHORTS)}"
        )
    pkg = "syntha.bundled_models"
    text = (resources.files(pkg) / _COHORTS[cohort]).read_text(encoding="utf-8")
    return load_generator_from_json(text, random_seed=seed)


def _csv_from_df(df: pd.DataFrame) -> str:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


def _drop_curation_flags(df: pd.DataFrame) -> pd.DataFrame:
    drop = [c for c in _schema.CURATION_COLUMNS if c in df.columns]
    return df.drop(columns=drop) if drop else df


def _apply_constraints(df: pd.DataFrame) -> pd.DataFrame:
    kept, _ = PhysiologicConstraints(ConstraintConfig()).apply(df)
    return kept


# ───────────────────────── tools ─────────────────────────


@_app.tool()
def syntha_version() -> dict:
    """Return the syntha library version, repo URL, and bundled-model fingerprints."""
    info: dict = {
        "syntha_version": _syntha_version,
        "repo": "https://github.com/ArioMoniri/syntha",
        "license": "Apache-2.0",
        "bundled_cohorts": list(_COHORTS),
    }
    return info


@_app.tool()
def list_bundled_cohorts() -> dict:
    """List the cohorts whose trained copulas ship with this package.

    Each ``tolerant`` and ``strict`` JSON is a compressed empirical
    summary (≈200 quantiles per continuous column plus a correlation
    matrix). No real patient records are embedded.
    """
    out = {}
    for name in _COHORTS:
        gen = _load_bundled(name)
        m = gen.model
        assert m is not None
        out[name] = {
            "n_train": m.n_train,
            "n_modeled_columns": len(m.columns),
            "n_binary_columns": len(m.binary_cols),
            "n_continuous_columns": len(m.columns) - len(m.binary_cols),
            "format": m.extras.get("format", "unknown"),
            "date_window": [
                m.extras.get("date_lo"),
                m.extras.get("date_hi"),
            ],
        }
    return out


@_app.tool()
def get_cohort_summary(cohort: Literal["tolerant", "strict"] = "tolerant") -> dict:
    """Return n_train, comorbidity prevalences, lab/vital columns, and source-window for a bundled cohort.

    Use this before ``generate_cohort_csv`` so you can see which
    diseases (Hipertansiyon, DM_Tum, Hiperlipidemi, Tiroid, …) are
    materially present (i.e. prevalence > 1 %) in the trained model.
    """
    gen = _load_bundled(cohort)
    m = gen.model
    assert m is not None

    # Tolerant: real prevalences. Strict: most comorbidities are
    # zero-prevalence by construction of the pristine-cohort filter, so
    # we mark that explicitly.
    comorbidity_prevalence = {
        c: round(m.binary_p.get(c, 0.0) * 100, 3)
        for c in _schema.COMORBIDITY_COLUMNS
        if c in m.binary_p
    }
    return {
        "cohort": cohort,
        "n_train": m.n_train,
        "modeled_columns": list(m.columns),
        "binary_columns": sorted(m.binary_cols),
        "continuous_columns": [c for c in m.columns if c not in m.binary_cols],
        "comorbidity_prevalence_percent": comorbidity_prevalence,
        "source_date_window": [
            m.extras.get("date_lo"),
            m.extras.get("date_hi"),
        ],
        "notes": (
            "tolerant: 135,569 retrospective episodes with realistic comorbidity"
            " prevalences (Tiroid 14.5 %, Hiperlipidemi 12.0 %, Hipertansiyon"
            " 7.5 %, DM 4.8 %, …). strict: 55,141 episodes filtered to"
            " clinically pristine — most comorbidity prevalences are ~0 % by"
            " construction."
        ),
    }


@_app.tool()
def generate_cohort_csv(
    n: int = 100,
    cohort: Literal["tolerant", "strict"] = "tolerant",
    seed: int = 42,
    apply_constraints: bool = True,
    include_curation_flags: bool = False,
    max_rows: int = 10_000,
) -> dict:
    """Generate ``n`` synthetic patient records from a bundled cohort, return them as a CSV string.

    Args:
        n: number of synthetic patients (capped at ``max_rows`` so the
           MCP tool result stays under typical client size limits).
        cohort: ``tolerant`` (default — realistic comorbidity prevalences)
           or ``strict`` (clinically-pristine cohort with near-zero
           prevalence on most diseases).
        seed: RNG seed for reproducibility.
        apply_constraints: drop rows that violate pulse-pressure ≥ 20 mmHg,
           Friedewald lipid coherence, or eGFR ↔ creatinine consistency.
        include_curation_flags: keep 29 source-pipeline metadata flags
           (``pristine_*``, ``berturk_*``, ``rf_*``, …). Off by default
           because those are training-pipeline artifacts, not clinical
           observations.
        max_rows: hard upper bound on returned rows. Default 10,000.

    Returns:
        ``{"csv": "<csv text>", "n_rows": int, "n_columns": int, "columns": [...], "cohort": str, "seed": int}``
    """
    n = max(1, min(int(n), int(max_rows)))
    gen = _load_bundled(cohort, seed=seed)
    raw = gen.sample(int(n * (1.5 if apply_constraints else 1.0)) + 8)
    if apply_constraints:
        raw = _apply_constraints(raw)
    df = raw.head(n).reset_index(drop=True)
    if not include_curation_flags:
        df = _drop_curation_flags(df)
    return {
        "cohort": cohort,
        "seed": seed,
        "n_rows": len(df),
        "n_columns": len(df.columns),
        "columns": list(df.columns),
        "csv": _csv_from_df(df),
    }


@_app.tool()
def generate_cohort_fhir(
    n: int = 25,
    cohort: Literal["tolerant", "strict"] = "tolerant",
    seed: int = 42,
    apply_constraints: bool = True,
    run_modules: bool = True,
    include_lab_history: bool = False,
    max_rows: int = 500,
) -> dict:
    """Generate ``n`` synthetic patients and return them as FHIR R4 NDJSON.

    Each line is a FHIR R4 ``Bundle`` of type ``transaction`` containing
    a ``Patient``, ``Observation``s (LOINC), ``Condition``s (SNOMED CT +
    ICD-10), ``Encounter``s, ``MedicationRequest``s (RxNorm), and the
    Synthea-style clinical modules (Hypertension, Diabetes, Hyperlipidemia,
    Thyroid, Depression, Anxiety, IHD, Asthma, COPD).

    Output is capped lower than the CSV tool because FHIR Bundles are
    bulkier — default 25, max 500.
    """
    n = max(1, min(int(n), int(max_rows)))
    gen = _load_bundled(cohort, seed=seed)
    raw = gen.sample(int(n * (1.5 if apply_constraints else 1.0)) + 8)
    if apply_constraints:
        raw = _apply_constraints(raw)
    df = raw.head(n).reset_index(drop=True)

    # Synthesize the three id columns the FHIR exporter expects.
    from .pipeline import _generate_ids_and_dates

    ids = _generate_ids_and_dates(
        len(df),
        pd.Timestamp(gen.model.extras.get("date_lo") or "2015-01-01"),  # type: ignore[union-attr]
        pd.Timestamp(gen.model.extras.get("date_hi") or "2024-12-31"),  # type: ignore[union-attr]
        seed=seed + 1,
    )
    df = pd.concat([ids, df], axis=1)

    from .fhir.export import episode_to_bundle

    bundles = [
        episode_to_bundle(row, run_modules, include_lab_history=include_lab_history)
        for _, row in df.iterrows()
    ]
    ndjson = "\n".join(json.dumps(b, ensure_ascii=False) for b in bundles)
    return {
        "cohort": cohort,
        "seed": seed,
        "n_rows": len(df),
        "n_bundles": len(bundles),
        "fhir_format": "ndjson",
        "fhir_ndjson": ndjson,
    }


@_app.tool()
def sample_conditional(
    condition: str,
    n: int = 100,
    cohort: Literal["tolerant", "strict"] = "tolerant",
    seed: int = 42,
    oversample_factor: float = 5.0,
    max_rounds: int = 10,
    include_curation_flags: bool = False,
    max_rows: int = 5_000,
) -> dict:
    """Rejection-sample synthetic patients matching a pandas-style filter expression.

    Example conditions:
      * ``"age > 60 & DM_Tum == 1 & bp_systolic >= 140"``
      * ``"Hipertansiyon == 1 & age >= 50 & age <= 75"``
      * ``"Hiperlipidemi == 1 & ldl_direct_latest > 160"``

    The expression is parsed by an AST-allowlist validator (no arbitrary
    Python). Compounds use ``&`` / ``|`` and column names must exist in
    the cohort's modeled-column list (see ``get_cohort_summary``).

    Returns the matching CSV, the number of rounds run, and the empirical
    rejection rate so the caller can see how rare the requested combination
    is in the cohort.
    """
    from .conditional import sample_conditional as _sample_conditional

    n = max(1, min(int(n), int(max_rows)))
    gen = _load_bundled(cohort, seed=seed)
    result = _sample_conditional(
        gen, n=n, condition=condition,
        oversample_factor=oversample_factor, max_rounds=max_rounds,
    )
    df = result.rows
    if not include_curation_flags:
        df = _drop_curation_flags(df)
    return {
        "cohort": cohort,
        "seed": seed,
        "condition": condition,
        "n_requested": result.n_requested,
        "n_generated": result.n_generated,
        "rounds": result.rounds,
        "rejection_rate": round(result.rejection_rate, 4),
        "csv": _csv_from_df(df),
    }


@_app.tool()
def list_clinical_modules() -> dict:
    """Enumerate the nine Synthea-style clinical modules and the source flag each fires on."""
    return {
        "modules": [
            {"name": "Hypertension",   "flag": "Hipertansiyon",       "drug_class": "ACEi (perindopril) ± CCB / thiazide"},
            {"name": "Diabetes",       "flag": "DM_Tum / DM_Komplikasyonlu", "drug_class": "metformin (± insulin if severe)"},
            {"name": "Hyperlipidemia", "flag": "Hiperlipidemi",       "drug_class": "moderate-intensity statin (high-intensity if LDL ≥ 190)"},
            {"name": "Thyroid",        "flag": "Tiroid",              "drug_class": "levothyroxine"},
            {"name": "Depression",     "flag": "Depresyon",           "drug_class": "SSRI (sertraline)"},
            {"name": "Anxiety",        "flag": "Anksiyete",           "drug_class": "SSRI (escitalopram) or buspirone"},
            {"name": "Ischemic heart disease", "flag": "Iskemik_Kalp", "drug_class": "aspirin + β-blocker + statin"},
            {"name": "Asthma",         "flag": "Astim",               "drug_class": "SABA + ICS"},
            {"name": "COPD",           "flag": "COPD",                "drug_class": "LABA + SABA"},
        ],
        "notes": (
            "Each module emits FHIR Encounter + MedicationRequest "
            "(RxNorm-coded) + Procedure + CarePlan when its flag is set in "
            "the sampled record. Drug-class defaults are international; "
            "Turkish-locale calibration is a help-wanted-clinician task — "
            "see COLLABORATE.md."
        ),
    }


@_app.tool()
def list_physiologic_constraints() -> dict:
    """Enumerate the four physiologic-validity rejection rules applied after sampling."""
    return {
        "constraints": [
            {"name": "pulse_pressure_min",
             "rule": "bp_systolic - bp_diastolic >= 20 mmHg"},
            {"name": "friedewald_coherence",
             "rule": "|cholesterol_total - (HDL + LDL + triglycerides/5)| <= 40 mg/dL "
                     "(only enforced when TG <= 400)"},
            {"name": "egfr_creatinine_consistency",
             "rule": "reject if creatinine > 2.0 mg/dL while eGFR > 90 mL/min/1.73m²"},
            {"name": "diastolic_le_systolic",
             "rule": "bp_diastolic <= bp_systolic"},
        ],
        "notes": (
            "Each rule fires only when both inputs are observed (i.e., "
            "not NaN). Empirical first-round acceptance is ≈ 97 % on the "
            "tolerant cohort."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    """Entry point used by the ``syntha-mcp`` console script."""
    import argparse

    argv = list(argv if argv is not None else sys.argv[1:])
    parser = argparse.ArgumentParser(
        prog="syntha-mcp",
        description="Run the syntha MCP server (stdio or HTTP).",
    )
    parser.add_argument(
        "--transport", choices=["stdio", "http", "sse"], default="stdio",
        help=("stdio (default) — for Claude Desktop and local MCP clients. "
              "http — Streamable HTTP for Claude.com custom-connector slot. "
              "sse — legacy Server-Sent Events transport."),
    )
    parser.add_argument(
        "--host", default=os.environ.get("SYNTHA_MCP_HOST", "127.0.0.1"),
        help="Host for http/sse transport (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--port", type=int,
        default=int(os.environ.get("SYNTHA_MCP_PORT", "8765")),
        help="Port for http/sse transport (default: 8765).",
    )
    args = parser.parse_args(argv)

    if args.transport in ("http", "sse"):
        # FastMCP picks up host/port from its settings.
        _app.settings.host = args.host
        _app.settings.port = args.port
        _app.run(transport="streamable-http" if args.transport == "http" else "sse")
    else:
        _app.run()  # stdio
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
