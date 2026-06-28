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

Core generation
  * ``list_bundled_cohorts``       — cohorts shipped with syntha
  * ``get_cohort_summary``         — n_train, marginal prevalences,
                                      modeled columns, source-data
                                      provenance
  * ``generate_cohort_csv``        — N synthetic patients as CSV
  * ``generate_cohort_fhir``       — N synthetic patients as FHIR R4 NDJSON
  * ``sample_conditional``         — AST-validated rejection sampling
  * ``generate_longitudinal_cohort`` — multi-encounter trajectories (CSV)
  * ``generate_longitudinal_fhir`` — multi-encounter trajectories (FHIR)
  * ``generate_cohort_with_lab_history`` — AR(1) lab time-series + BP triplets
  * ``generate_clinical_assessments`` — Charlson / PHQ-9 / GAD-7 / family history

Validation & privacy
  * ``validate_synthetic_csv``     — KS / Wasserstein / Frobenius diff
  * ``validate_against_bundled_cohort`` — same against bundled marginals
  * ``privacy_audit``              — MIA + AIA against caller-supplied CSVs
  * ``privacy_audit_bundled``      — MIA + AIA self-audit on bundled cohort
  * ``fraction_within_reference``  — fraction inside clinical ref intervals
  * ``check_row_within_reference`` — per-record reference-interval check
  * ``apply_physiologic_constraints`` — drop rows that fail clinical rules

Reference data / introspection
  * ``list_clinical_modules``      — the nine Synthea-style modules
  * ``list_modules_detail``        — full per-module emission detail
  * ``list_physiologic_constraints`` — rejection rules
  * ``list_reference_ranges``      — Mayo/Tietz/KDIGO reference intervals
  * ``list_schema_columns``        — labs/vitals/demographics/flags/bounds
  * ``list_condition_codes``       — dual-coded SNOMED + ICD-10 + TR display
  * ``list_lab_loinc_codes``       — LOINC + UCUM per lab
  * ``list_lab_panels``            — DiagnosticReport panel groupings
  * ``list_lab_drift_profiles``    — Westgard biological variation per lab
  * ``list_rxnorm_medications``    — RxNorm prescription catalog
  * ``list_locale_data``           — Turkish names / cities / displays
  * ``list_clinical_assessment_instruments`` — PHQ-9 / GAD-7 / Charlson refs
  * ``list_pipeline_config_options`` — PipelineConfig field documentation
  * ``ckd_stage_for_egfr``         — KDIGO 2024 staging lookup
  * ``validate_condition_expression`` — AST-precheck sample_conditional input
  * ``get_correlation_pairs``      — top Spearman pairs from bundled model
  * ``get_model_card``             — full ModelCard for a bundled cohort
  * ``syntha_version``             — version + commit-hash provenance

Run as ``syntha-mcp`` (installed by the ``[mcp]`` extra) or
``python -m syntha.mcp_server``.
"""
from __future__ import annotations

import io
import json
import os
import sys
import uuid
from dataclasses import fields as _dc_fields
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

import numpy as np
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
        "episodes. All outputs are synthetic: no real-patient row is ever "
        "returned.\n\n"
        "Generation tools:\n"
        "  • `generate_cohort_csv` — N synthetic patients as a flat CSV.\n"
        "  • `generate_cohort_fhir` — N synthetic patients as FHIR R4 NDJSON.\n"
        "  • `sample_conditional` — AST-validated rejection sampling.\n"
        "  • `generate_longitudinal_cohort` — multi-encounter trajectories (CSV).\n"
        "  • `generate_longitudinal_fhir` — multi-encounter trajectories (FHIR).\n"
        "  • `generate_cohort_with_lab_history` — AR(1) lab time-series + BP triplets.\n"
        "  • `generate_clinical_assessments` — Charlson + PHQ-9 + GAD-7 + family history.\n\n"
        "Validation / privacy tools:\n"
        "  • `validate_synthetic_csv`, `validate_against_bundled_cohort`,\n"
        "    `privacy_audit`, `privacy_audit_bundled`, `fraction_within_reference`,\n"
        "    `check_row_within_reference`, `apply_physiologic_constraints`.\n\n"
        "Reference / introspection tools:\n"
        "  • `get_cohort_summary`, `get_model_card`, `get_correlation_pairs`,\n"
        "    `list_bundled_cohorts`, `list_clinical_modules`, `list_modules_detail`,\n"
        "    `list_physiologic_constraints`, `list_reference_ranges`,\n"
        "    `list_schema_columns`, `list_condition_codes`, `list_lab_loinc_codes`,\n"
        "    `list_lab_panels`, `list_lab_drift_profiles`, `list_rxnorm_medications`,\n"
        "    `list_locale_data`, `list_clinical_assessment_instruments`,\n"
        "    `list_pipeline_config_options`, `ckd_stage_for_egfr`,\n"
        "    `validate_condition_expression`, `syntha_version`."
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


# Inbound-CSV size cap for tools that accept CSV text — keeps tool invocations
# under typical MCP client limits and prevents resource exhaustion.
_MAX_CSV_BYTES = 5 * 1024 * 1024  # 5 MB


def _csv_to_df(csv_text: str, label: str = "csv") -> pd.DataFrame:
    """Parse a CSV string with bounded size, raising a clear ValueError on overflow."""
    if not isinstance(csv_text, str):
        raise ValueError(f"{label} must be a CSV string")
    nb = len(csv_text.encode("utf-8"))
    if nb > _MAX_CSV_BYTES:
        raise ValueError(
            f"{label} exceeds the 5 MB inbound cap "
            f"(got {nb / 1024 / 1024:.2f} MB)"
        )
    return pd.read_csv(io.StringIO(csv_text))


def _sample_constrained(
    cohort: str,
    n: int,
    seed: int,
    apply_constraints: bool,
    include_curation_flags: bool,
) -> pd.DataFrame:
    """Common-path sampler: load cohort, oversample, apply constraints, drop curation."""
    gen = _load_bundled(cohort, seed=seed)
    raw = gen.sample(int(n * (1.5 if apply_constraints else 1.0)) + 8)
    if apply_constraints:
        raw = _apply_constraints(raw)
    df = raw.head(n).reset_index(drop=True)
    if not include_curation_flags:
        df = _drop_curation_flags(df)
    return df


def _model_card_dict(cohort: str) -> dict:
    """Synthesize a ModelCard-style summary for a bundled cohort.

    Bundled cohort JSONs ship the empirical marginals/correlations but not
    the per-cohort training metadata, so we reconstruct what we can from
    the v2 JSON and annotate the rest as not-available.
    """
    gen = _load_bundled(cohort)
    m = gen.model
    assert m is not None
    binary_marginals = {c: float(m.binary_p.get(c, 0.0)) for c in sorted(m.binary_cols)}
    continuous_summary: dict[str, dict] = {}
    for col, qs in m.continuous_quantiles.items():
        arr = np.asarray(qs, dtype=float)
        if not arr.size:
            continue
        continuous_summary[col] = {
            "mean": float(arr.mean()),
            "std": float(arr.std()),
            "q05": float(np.quantile(arr, 0.05)),
            "q50": float(np.quantile(arr, 0.50)),
            "q95": float(np.quantile(arr, 0.95)),
        }
    pairs = _top_correlation_pairs(m, top_k=15, min_abs_corr=0.0)
    return {
        "name": f"copula_{cohort}",
        "cohort": cohort,
        "n_train": int(m.n_train),
        "source_csv": "bundled-v2-json",
        "source_sha256": None,
        "trained_at": None,
        "syntha_version": _syntha_version,
        "binary_marginals": binary_marginals,
        "continuous_summary": continuous_summary,
        "top_correlations": pairs,
        "source_date_window": [
            m.extras.get("date_lo"),
            m.extras.get("date_hi"),
        ],
        "notes": (
            "Bundled JSON model. source_sha256 and trained_at are not "
            "embedded in the bundled artifact; see the trained ModelCard "
            "in the registry directory for full provenance."
        ),
    }


def _top_correlation_pairs(
    m, top_k: int = 30, min_abs_corr: float = 0.1
) -> list[dict]:
    """Top-K |Spearman| pairs from a CopulaModel."""
    cols = list(m.columns)
    corr = np.asarray(m.correlation, dtype=float)
    pairs: list[dict] = []
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            v = corr[i, j]
            if not np.isfinite(v):
                continue
            if abs(v) < min_abs_corr:
                continue
            pairs.append({"a": cols[i], "b": cols[j], "spearman": float(v)})
    pairs.sort(key=lambda d: abs(d["spearman"]), reverse=True)
    return pairs[:top_k]


def _coerce_to_float64(df: pd.DataFrame) -> pd.DataFrame:
    """Cast every numeric column to plain float64 (NaN-safe).

    Some upstream samplers emit pandas nullable Int64 columns; downstream
    privacy/validation attacks try to median-fill with floats, which Int64
    rejects. Casting to float64 here is the simplest robust fix.
    """
    out = df.copy()
    for col in out.columns:
        try:
            out[col] = pd.to_numeric(out[col], errors="coerce").astype("float64")
        except (TypeError, ValueError):
            # Non-numeric column (e.g. an ID/date string) — leave it alone.
            continue
    return out


def _generate_episode_ids(
    df: pd.DataFrame, cohort_model, seed: int
) -> pd.DataFrame:
    """Prepend the three FHIR-required id columns to a sampled DataFrame."""
    from .pipeline import _generate_ids_and_dates

    ids = _generate_ids_and_dates(
        len(df),
        pd.Timestamp(cohort_model.extras.get("date_lo") or "2015-01-01"),
        pd.Timestamp(cohort_model.extras.get("date_hi") or "2024-12-31"),
        seed=seed,
    )
    return pd.concat([ids.reset_index(drop=True), df.reset_index(drop=True)], axis=1)


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


# ───────────────────────── longitudinal & FHIR variants ─────────────────────────


@_app.tool()
def generate_longitudinal_cohort(
    n_patients: int = 50,
    cohort: Literal["tolerant", "strict"] = "tolerant",
    encounters_per_patient_mean: float = 4.0,
    years_of_history: float = 3.0,
    lab_drift_scale: float = 0.05,
    age_advance: bool = True,
    seed: int = 42,
    apply_constraints: bool = True,
    include_curation_flags: bool = False,
    max_rows: int = 5_000,
) -> dict:
    """Generate a longitudinal multi-encounter cohort as a CSV.

    Each baseline patient is expanded into a Poisson-mean number of
    encounters over ``years_of_history`` years. Comorbidity flags are
    sticky (once present, present in all subsequent encounters). Continuous
    labs drift around the baseline via a Gaussian walk scaled by
    ``lab_drift_scale`` (5% of baseline by default). Age advances with
    the encounter date when ``age_advance`` is set.

    Output rows ≈ ``n_patients × encounters_per_patient_mean``; the result
    is capped at ``max_rows`` total encounters and the response reports
    whether truncation occurred.
    """
    from .longitudinal import TrajectoryConfig, expand_to_trajectories

    n_patients = max(1, int(n_patients))
    gen = _load_bundled(cohort, seed=seed)
    m = gen.model
    assert m is not None

    # Oversample baselines so post-constraint we have ~n_patients.
    raw = gen.sample(int(n_patients * (1.5 if apply_constraints else 1.0)) + 8)
    if apply_constraints:
        raw = _apply_constraints(raw)
    baselines = raw.head(n_patients).reset_index(drop=True)
    baselines = _generate_episode_ids(baselines, m, seed=seed + 1)

    date_lo = pd.Timestamp(m.extras.get("date_lo") or "2015-01-01")
    date_hi = pd.Timestamp(m.extras.get("date_hi") or "2024-12-31")
    traj_cfg = TrajectoryConfig(
        encounters_per_patient_mean=float(encounters_per_patient_mean),
        years_of_history=float(years_of_history),
        lab_drift_scale=float(lab_drift_scale),
        age_advance=bool(age_advance),
        random_seed=seed + 2,
    )
    expanded = expand_to_trajectories(baselines, date_lo, date_hi, traj_cfg)
    if apply_constraints:
        expanded = _apply_constraints(expanded)

    truncated = False
    if len(expanded) > max_rows:
        expanded = expanded.head(int(max_rows)).reset_index(drop=True)
        truncated = True

    if not include_curation_flags:
        expanded = _drop_curation_flags(expanded)

    return {
        "cohort": cohort,
        "seed": seed,
        "n_patients": int(n_patients),
        "n_encounters": int(len(expanded)),
        "truncated": truncated,
        "columns": list(expanded.columns),
        "csv": _csv_from_df(expanded),
    }


@_app.tool()
def generate_longitudinal_fhir(
    n_patients: int = 25,
    cohort: Literal["tolerant", "strict"] = "tolerant",
    encounters_per_patient_mean: float = 4.0,
    years_of_history: float = 3.0,
    include_lab_history: bool = False,
    run_modules: bool = True,
    seed: int = 42,
    max_bundles: int = 200,
) -> dict:
    """Generate longitudinal multi-encounter records as FHIR R4 NDJSON.

    Same trajectory expansion as ``generate_longitudinal_cohort`` but
    emits one ``Bundle`` per encounter (so a single patient can yield 4+
    bundles linked by the synthetic HASTA_ID).

    Output is capped at ``max_bundles`` (default 200; hard ceiling 500).
    """
    from .fhir.export import episode_to_bundle
    from .longitudinal import TrajectoryConfig, expand_to_trajectories

    n_patients = max(1, int(n_patients))
    max_bundles = max(1, min(int(max_bundles), 500))

    gen = _load_bundled(cohort, seed=seed)
    m = gen.model
    assert m is not None

    raw = gen.sample(int(n_patients * 1.5) + 8)
    raw = _apply_constraints(raw)
    baselines = raw.head(n_patients).reset_index(drop=True)
    baselines = _generate_episode_ids(baselines, m, seed=seed + 1)

    date_lo = pd.Timestamp(m.extras.get("date_lo") or "2015-01-01")
    date_hi = pd.Timestamp(m.extras.get("date_hi") or "2024-12-31")
    traj_cfg = TrajectoryConfig(
        encounters_per_patient_mean=float(encounters_per_patient_mean),
        years_of_history=float(years_of_history),
        random_seed=seed + 2,
    )
    expanded = expand_to_trajectories(baselines, date_lo, date_hi, traj_cfg)
    expanded = _apply_constraints(expanded)

    if len(expanded) > max_bundles:
        expanded = expanded.head(max_bundles).reset_index(drop=True)

    bundles = [
        episode_to_bundle(
            row, run_modules, include_lab_history=include_lab_history,
        )
        for _, row in expanded.iterrows()
    ]
    ndjson = "\n".join(json.dumps(b, ensure_ascii=False) for b in bundles)
    return {
        "cohort": cohort,
        "seed": seed,
        "n_bundles": len(bundles),
        "fhir_format": "ndjson",
        "fhir_ndjson": ndjson,
    }


@_app.tool()
def generate_cohort_with_lab_history(
    n: int = 25,
    cohort: Literal["tolerant", "strict"] = "tolerant",
    seed: int = 42,
    n_historical_min: int = 2,
    n_historical_max: int = 4,
    history_window_days_min: int = 180,
    history_window_days_max: int = 730,
    intra_encounter_bp_count: int = 3,
    max_rows: int = 100,
) -> dict:
    """Generate FHIR bundles with AR(1) lab time-series and intra-encounter BP triplets.

    For each lab in the time-series catalog (glucose, lipids, hemogram,
    creatinine/eGFR, ferritin, B12, liver enzymes), syntha synthesizes
    2-4 prior measurements over 6-24 months with Westgard-derived
    biological variation (e.g. eGFR has 6% CV plus ~1%/yr secular decline).
    Each encounter also emits 2-3 BP readings 4-6 min apart showing the
    standard white-coat drop on repeat readings.

    Default n=25; hard cap at 100 (each patient adds ~15 history Observations).
    """
    from .fhir.export import episode_to_bundle
    from .longitudinal_labs import TrajectoryConfig as LabHistoryCfg

    n = max(1, min(int(n), int(max_rows)))
    gen = _load_bundled(cohort, seed=seed)
    m = gen.model
    assert m is not None

    raw = gen.sample(int(n * 1.5) + 8)
    raw = _apply_constraints(raw)
    df = raw.head(n).reset_index(drop=True)
    df = _generate_episode_ids(df, m, seed=seed + 1)

    # Override the lab-history defaults via a module-level patch so the
    # FHIR exporter picks them up. We do this scoped to this tool call by
    # passing the config object directly into expand_observations_with_history
    # through a per-row monkeypatch on the exporter.
    from . import longitudinal_labs as _ll
    from .fhir import export as _fhir_export

    user_cfg = LabHistoryCfg(
        n_historical_min=int(n_historical_min),
        n_historical_max=int(n_historical_max),
        history_window_days_min=int(history_window_days_min),
        history_window_days_max=int(history_window_days_max),
        intra_encounter_bp_count=int(intra_encounter_bp_count),
    )

    bundles: list[dict] = []
    rng = np.random.default_rng(seed + 5)
    for _, row in df.iterrows():
        bundle = episode_to_bundle(row, run_modules=True, include_lab_history=False)
        # Splice in lab history + intra-encounter BP using the row's UUID Patient.
        patient_id = None
        for entry in bundle.get("entry", []):
            res = entry.get("resource", {})
            if res.get("resourceType") == "Patient":
                patient_id = res.get("id")
                break
        if patient_id is None:
            bundles.append(bundle)
            continue
        episode_dt = pd.to_datetime(row.get("episode_date"), errors="coerce")
        if pd.isna(episode_dt):
            episode_dt = pd.Timestamp.utcnow()
        extras = _ll.expand_observations_with_history(
            row, patient_id, episode_dt, cfg=user_cfg, rng=rng,
        )
        for r in extras:
            bundle["entry"].append({
                "fullUrl": f"urn:uuid:{r['id']}",
                "resource": r,
                "request": {"method": "POST", "url": r["resourceType"]},
            })
        bundles.append(bundle)

    ndjson = "\n".join(json.dumps(b, ensure_ascii=False) for b in bundles)
    return {
        "cohort": cohort,
        "seed": seed,
        "n_bundles": len(bundles),
        "fhir_format": "ndjson",
        "fhir_ndjson": ndjson,
    }


@_app.tool()
def generate_clinical_assessments(
    n: int = 10,
    cohort: Literal["tolerant", "strict"] = "tolerant",
    seed: int = 42,
    include: list[str] | None = None,
) -> dict:
    """Emit standalone Charlson / PHQ-9 / GAD-7 / family-history resources.

    Each entry is keyed off a freshly-sampled synthetic patient. Useful
    for showing the LLM exactly what PHQ-9 / GAD-7 / Charlson resources
    syntha emits without scanning a full FHIR bundle.

    ``include`` defaults to all four assessments.
    """
    from .fhir.clinical_extras import (
        charlson_risk_assessment,
        family_history_resources,
        gad7_observation,
        phq9_observation,
    )

    n = max(1, min(int(n), 50))
    include_set = {s.lower() for s in (include or ["charlson", "phq9", "gad7", "family_history"])}

    gen = _load_bundled(cohort, seed=seed)
    m = gen.model
    assert m is not None

    raw = gen.sample(int(n * 1.5) + 8)
    raw = _apply_constraints(raw)
    df = raw.head(n).reset_index(drop=True)
    df = _generate_episode_ids(df, m, seed=seed + 1)

    rng = np.random.default_rng(seed + 7)
    assessments: list[dict] = []
    for _, row in df.iterrows():
        patient_id = str(uuid.uuid4())
        episode_dt = pd.to_datetime(row.get("episode_date"), errors="coerce")
        if pd.isna(episode_dt):
            episode_dt = pd.Timestamp.utcnow()
        effective_iso = episode_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        item: dict = {"patient_id": patient_id}
        if "charlson" in include_set and pd.notna(row.get("charlson_cci")):
            item["charlson"] = charlson_risk_assessment(
                patient_id, float(row.get("charlson_cci")), effective_iso,
            )
        if "phq9" in include_set and pd.notna(row.get("Depresyon")):
            item["phq9"] = phq9_observation(
                patient_id, int(row.get("Depresyon")), effective_iso, rng,
            )
        if "gad7" in include_set and pd.notna(row.get("Anksiyete")):
            item["gad7"] = gad7_observation(
                patient_id, int(row.get("Anksiyete")), effective_iso, rng,
            )
        if "family_history" in include_set:
            item["family_history"] = family_history_resources(
                patient_id, row, effective_iso,
            )
        assessments.append(item)

    return {
        "cohort": cohort,
        "seed": seed,
        "n": len(assessments),
        "include": sorted(include_set),
        "assessments": assessments,
    }


# ───────────────────────── validation / privacy ─────────────────────────


@_app.tool()
def validate_synthetic_csv(
    source_csv: str,
    synthetic_csv: str,
    continuous_cols: list[str] | None = None,
    binary_cols: list[str] | None = None,
    min_observations: int = 30,
) -> dict:
    """Compare two CSVs with KS / Wasserstein / Frobenius correlation diff.

    The headline statistical-fidelity reporter. ``source_csv`` is the
    real reference data; ``synthetic_csv`` is the candidate. Column
    classification defaults to syntha's schema (continuous = labs +
    vitals + counts + age; binary = gender + comorbidity + flag columns)
    when not provided.

    Each CSV is capped at 5 MB inbound.
    """
    from .validate import validate

    src = _csv_to_df(source_csv, "source_csv")
    syn = _csv_to_df(synthetic_csv, "synthetic_csv")

    if continuous_cols is None:
        continuous_cols = [c for c in _schema.continuous_columns() if c in src.columns]
    if binary_cols is None:
        binary_cols = [c for c in _schema.binary_columns() if c in src.columns]

    report = validate(src, syn, continuous_cols, binary_cols, min_observations=int(min_observations))
    return {
        "summary": report.summary(),
        "per_column": report.to_dict(),
    }


@_app.tool()
def validate_against_bundled_cohort(
    synthetic_csv: str,
    cohort: Literal["tolerant", "strict"] = "tolerant",
    n_reference: int = 2_000,
    seed: int = 42,
    min_observations: int = 30,
) -> dict:
    """Compare a user-supplied synthetic CSV against the bundled cohort's marginals.

    Useful when you don't have access to the real source CSV: syntha
    samples ``n_reference`` rows from the bundled model and uses that as
    the reference distribution for the KS / Wasserstein / Frobenius
    comparison. The reference sample is reproducible via ``seed``.
    """
    from .validate import validate

    syn = _csv_to_df(synthetic_csv, "synthetic_csv")
    n_ref = max(100, min(int(n_reference), 20_000))
    gen = _load_bundled(cohort, seed=seed)
    ref = gen.sample(n_ref)
    ref = _apply_constraints(ref)

    continuous_cols = [c for c in _schema.continuous_columns() if c in ref.columns]
    binary_cols = [c for c in _schema.binary_columns() if c in ref.columns]

    report = validate(ref, syn, continuous_cols, binary_cols, min_observations=int(min_observations))
    return {
        "cohort": cohort,
        "n_reference": int(len(ref)),
        "summary": report.summary(),
        "per_column": report.to_dict(),
    }


@_app.tool()
def privacy_audit(
    real_train_csv: str,
    real_holdout_csv: str,
    synthetic_csv: str,
    feature_cols: list[str] | None = None,
    sensitive_targets: list[str] | None = None,
    mia_threshold: float = 0.60,
    aia_threshold: float = 0.70,
) -> dict:
    """Run MIA + AIA privacy attacks, return a pass/fail PrivacyReport.

    Membership-inference (Stadler nearest-neighbor) AUC > ``mia_threshold``
    or any attribute-inference AUC > ``aia_threshold`` → verdict 'fail'.

    Each CSV is capped at 5 MB inbound.
    """
    from .privacy import run_privacy_audit

    train = _csv_to_df(real_train_csv, "real_train_csv")
    holdout = _csv_to_df(real_holdout_csv, "real_holdout_csv")
    syn = _csv_to_df(synthetic_csv, "synthetic_csv")

    if feature_cols is None:
        feature_cols = [c for c in _schema.all_modeled_columns() if c in train.columns]
    if sensitive_targets is None:
        sensitive_targets = [
            c for c in ("Hipertansiyon", "DM_Tum", "Hiperlipidemi", "Depresyon")
            if c in train.columns
        ]

    report = run_privacy_audit(
        train, holdout, syn, feature_cols, sensitive_targets,
        mia_threshold=float(mia_threshold), aia_threshold=float(aia_threshold),
    )
    return {
        "verdict": report.verdict,
        "membership_inference_auc": report.membership_inference_auc,
        "attribute_inference_aucs": report.attribute_inference_aucs,
        "n_synthetic": report.n_synthetic,
        "n_real_members": report.n_real_members,
        "n_real_holdout": report.n_real_holdout,
        "columns_attacked": report.columns_attacked,
    }


@_app.tool()
def privacy_audit_bundled(
    cohort: Literal["tolerant", "strict"] = "tolerant",
    n: int = 2_000,
    split: float = 0.8,
    seed: int = 42,
) -> dict:
    """Self-audit: run MIA + AIA using the bundled model's own samples.

    Samples ``n`` rows from the bundled cohort, splits them into
    ``split``-train / (1-split)-holdout as synthetic surrogates for real
    training data, then samples a fresh ``n`` synthetic rows and runs the
    standard attacks. Demonstrates that bundled models pass the audit.
    """
    from .privacy import run_privacy_audit

    n = max(200, min(int(n), 5_000))
    split = float(min(0.95, max(0.05, split)))

    gen_a = _load_bundled(cohort, seed=seed)
    population = gen_a.sample(int(n))
    population = _apply_constraints(population).reset_index(drop=True)
    # Privacy attacks downcast to float for distance/logistic calculations;
    # coerce any pandas Int64 nullable columns the copula emits down to plain
    # float64 here so the median-fill in privacy._prepare doesn't TypeError.
    population = _coerce_to_float64(population)

    cut = int(len(population) * split)
    train = population.iloc[:cut].reset_index(drop=True)
    holdout = population.iloc[cut:].reset_index(drop=True)

    gen_b = _load_bundled(cohort, seed=seed + 9_999)
    syn = gen_b.sample(int(n))
    syn = _apply_constraints(syn).reset_index(drop=True)
    syn = _coerce_to_float64(syn)

    feature_cols = [c for c in _schema.all_modeled_columns() if c in train.columns]
    sensitive_targets = [
        c for c in ("Hipertansiyon", "DM_Tum", "Hiperlipidemi", "Depresyon", "Tiroid")
        if c in train.columns
    ]

    report = run_privacy_audit(train, holdout, syn, feature_cols, sensitive_targets)
    return {
        "cohort": cohort,
        "verdict": report.verdict,
        "membership_inference_auc": report.membership_inference_auc,
        "attribute_inference_aucs": report.attribute_inference_aucs,
        "sensitive_targets": sensitive_targets,
        "n_synthetic": report.n_synthetic,
        "n_real_members": report.n_real_members,
        "n_real_holdout": report.n_real_holdout,
    }


@_app.tool()
def fraction_within_reference(
    n: int = 500,
    cohort: Literal["tolerant", "strict"] = "tolerant",
    seed: int = 42,
    apply_constraints: bool = True,
) -> dict:
    """Per-column fraction of generated patients inside the clinical reference interval.

    Sex-aware for hemoglobin and creatinine (different M/F bounds).
    Uses the Mayo / Tietz / KDIGO reference intervals shipped in
    ``syntha.reference_ranges``.
    """
    from . import reference_ranges as _rr

    n = max(10, min(int(n), 5_000))
    df = _sample_constrained(
        cohort=cohort, n=n, seed=seed,
        apply_constraints=apply_constraints, include_curation_flags=False,
    )
    fractions = _rr.fraction_within_reference(df)
    return {
        "cohort": cohort,
        "seed": seed,
        "n_sampled": int(len(df)),
        "fractions": {k: float(v) for k, v in fractions.items()},
        "sex_aware_columns": list(_rr.BY_SEX),
    }


@_app.tool()
def check_row_within_reference(row: dict) -> dict:
    """Per-record reference-interval check for one synthetic patient row.

    Pass a dict like ``{"gender_is_male": 1, "hemoglobin_latest": 14.2,
    "ldl_direct_latest": 110, ...}``. The ``gender_is_male`` field is
    required for sex-aware columns (hemoglobin, creatinine).
    """
    from . import reference_ranges as _rr

    if not isinstance(row, dict):
        raise ValueError("`row` must be a dict of column→value")
    s = pd.Series(row)
    result = _rr.row_within_reference(s)
    n_in = sum(1 for v in result.values() if v is True)
    n_out = sum(1 for v in result.values() if v is False)
    return {
        "per_column": result,
        "summary": {
            "n_in_range": n_in,
            "n_out_of_range": n_out,
            "n_missing": len(_rr.COMMON) + len(_rr.BY_SEX) - len(result),
        },
    }


@_app.tool()
def apply_physiologic_constraints(
    csv: str,
    rules: list[str] | None = None,
    max_kept_rows: int = 5_000,
) -> dict:
    """Filter an arbitrary CSV against syntha's physiologic-coherence rules.

    Drops rows that violate pulse-pressure ≥ 20 mmHg, Friedewald lipid
    coherence, or eGFR ↔ creatinine consistency. ``rules`` defaults to
    all four; pass a subset to enable only some.

    Returns rejection counts plus a (possibly-truncated) CSV of kept rows.
    """
    df = _csv_to_df(csv, "csv")

    cfg = ConstraintConfig()
    rule_set = {r.lower() for r in (rules or [
        "diastolic_le_systolic", "pulse_pressure_min",
        "friedewald_coherence", "egfr_creatinine_consistency",
    ])}
    cfg.enforce_systolic_gt_diastolic = (
        "diastolic_le_systolic" in rule_set or "pulse_pressure_min" in rule_set
    )
    cfg.enforce_cholesterol_friedewald = "friedewald_coherence" in rule_set
    cfg.enforce_egfr_creatinine = "egfr_creatinine_consistency" in rule_set

    kept, stats = PhysiologicConstraints(cfg).apply(df)
    truncated = False
    if len(kept) > int(max_kept_rows):
        kept = kept.head(int(max_kept_rows)).reset_index(drop=True)
        truncated = True

    return {
        "n_in": int(stats["rows_in"]),
        "n_kept": int(stats["rows_kept"]),
        "n_dropped": int(stats["rows_dropped"]),
        "drop_rate": float(stats["drop_rate"]),
        "rules_applied": sorted(rule_set),
        "kept_truncated": truncated,
        "kept_csv": _csv_from_df(kept),
    }


# ───────────────────────── reference data ─────────────────────────


@_app.tool()
def list_reference_ranges(sex: Literal["M", "F"] | None = None) -> dict:
    """Return the clinical reference intervals (Mayo / Tietz / KDIGO).

    ``sex`` selects the sex-specific row for hemoglobin / creatinine; omit
    it to receive both M and F rows for those columns.
    """
    from . import reference_ranges as _rr

    out: list[dict] = []
    for col, ref in _rr.COMMON.items():
        out.append({
            "column": col,
            "low": ref.low, "high": ref.high,
            "units": ref.units, "notes": ref.notes,
            "sex_specific": False,
        })
    for col, refs in _rr.BY_SEX.items():
        for s, ref in refs.items():
            if sex is not None and s != sex:
                continue
            out.append({
                "column": col, "sex": s,
                "low": ref.low, "high": ref.high,
                "units": ref.units, "notes": ref.notes,
                "sex_specific": True,
            })
    return {"ranges": out}


@_app.tool()
def list_schema_columns(
    group: Literal[
        "labs", "vitals", "demographics", "counts", "comorbidities",
        "flags", "curation", "panels", "bounds", "all",
    ] = "all",
) -> dict:
    """Return syntha's column groupings + LAB_PANELS + PHYSIOLOGIC_BOUNDS.

    Use this to know which columns are labs vs vitals vs comorbidities,
    or to look up the (low, high) physiologic bounds — essential for
    writing valid ``sample_conditional`` expressions.
    """
    g = group.lower()
    out: dict = {}
    if g in ("labs", "all"):
        out["labs"] = list(_schema.LAB_COLUMNS)
    if g in ("vitals", "all"):
        out["vitals"] = list(_schema.VITAL_COLUMNS)
    if g in ("demographics", "all"):
        out["demographics"] = list(_schema.DEMOGRAPHIC_COLUMNS)
    if g in ("counts", "all"):
        out["counts"] = list(_schema.COUNT_COLUMNS)
    if g in ("comorbidities", "all"):
        out["comorbidities"] = list(_schema.COMORBIDITY_COLUMNS)
    if g in ("flags", "all"):
        out["flags"] = list(_schema.FLAG_COLUMNS)
    if g in ("curation", "all"):
        out["curation"] = list(_schema.CURATION_COLUMNS)
    if g in ("panels", "all"):
        out["panels"] = [
            {"id": pid, "loinc": loinc, "display": disp, "members": list(members)}
            for pid, loinc, disp, members in _schema.LAB_PANELS
        ]
    if g in ("bounds", "all"):
        out["physiologic_bounds"] = {
            k: [float(lo), float(hi)] for k, (lo, hi) in _schema.PHYSIOLOGIC_BOUNDS.items()
        }
    return out


@_app.tool()
def list_condition_codes() -> dict:
    """Dual-coded SNOMED + ICD-10 + Turkish display per comorbidity flag."""
    from .fhir.codes import CONDITION_ICD10, CONDITION_SNOMED
    from .locale.turkish import CONDITION_DISPLAY_TR

    rows: list[dict] = []
    for flag in _schema.COMORBIDITY_COLUMNS:
        sct = CONDITION_SNOMED.get(flag, ("", ""))
        icd = CONDITION_ICD10.get(flag, ("", ""))
        rows.append({
            "flag": flag,
            "snomed": [sct[0], sct[1]],
            "icd10": [icd[0], icd[1]],
            "turkish_display": CONDITION_DISPLAY_TR.get(flag, ""),
        })
    return {"conditions": rows}


@_app.tool()
def list_lab_loinc_codes() -> dict:
    """Per-lab LOINC code, display, and UCUM unit."""
    from .fhir.codes import LAB_LOINC

    return {
        "labs": [
            {"column": col, "loinc": code, "display": disp, "unit": unit}
            for col, (code, disp, unit) in LAB_LOINC.items()
        ],
    }


@_app.tool()
def list_lab_panels() -> dict:
    """LOINC-coded DiagnosticReport panel definitions (lipid, CBC, CMP, iron, BP)."""
    return {
        "panels": [
            {"id": pid, "loinc": loinc, "display": disp, "columns": list(members)}
            for pid, loinc, disp, members in _schema.LAB_PANELS
        ],
    }


@_app.tool()
def list_lab_drift_profiles() -> dict:
    """Westgard biological variation + secular trend per modeled lab.

    Used by ``generate_cohort_with_lab_history`` to synthesize AR(1)
    historical measurements per analyte. σ is expressed as a fraction
    of the latest value; secular trend is per-year fractional drift
    (e.g. eGFR ≈ -1%/year in healthy adults).
    """
    from .fhir.codes import LAB_LOINC
    from .longitudinal_labs import COLUMN_DRIFT

    rows: list[dict] = []
    for col, (sigma, trend) in COLUMN_DRIFT.items():
        code, _disp, _unit = LAB_LOINC.get(col, ("", "", ""))
        rows.append({
            "name": col,
            "sigma_fraction": float(sigma),
            "secular_trend_per_year": float(trend),
            "loinc": code,
        })
    return {
        "columns": rows,
        "notes": (
            "σ_fraction is the per-measurement biological CV (Westgard). "
            "secular_trend_per_year is signed fractional drift (e.g. "
            "-0.01 = 1%/year decline). Used to build AR(1) historical "
            "trajectories ending at the published _latest value."
        ),
    }


@_app.tool()
def list_rxnorm_medications(drug_class: str | None = None) -> dict:
    """Return the RxNorm catalog used by the Synthea-style modules.

    Pass ``drug_class`` to filter (e.g. 'statins', 'antihypertensives',
    'antidiabetics_first_line', 'ssris').
    """
    from .fhir import rxnorm

    classes = {
        "antihypertensives": rxnorm.ANTIHYPERTENSIVES,
        "antidiabetics_first_line": rxnorm.ANTIDIABETICS_FIRST_LINE,
        "antidiabetics_insulin": rxnorm.ANTIDIABETICS_INSULIN,
        "statins": rxnorm.STATINS,
        "levothyroxine": rxnorm.LEVOTHYROXINE,
        "ssris": rxnorm.SSRIS,
        "anxiolytics": rxnorm.ANXIOLYTICS,
        "bronchodilators_saba": rxnorm.BRONCHODILATORS_SABA,
        "bronchodilators_laba": rxnorm.BRONCHODILATORS_LABA,
        "inhaled_corticosteroids": rxnorm.INHALED_CORTICOSTEROIDS,
        "antiplatelets": rxnorm.ANTIPLATELETS,
        "beta_blockers": rxnorm.BETA_BLOCKERS,
    }
    if drug_class is not None:
        key = drug_class.lower()
        if key not in classes:
            raise ValueError(
                f"unknown drug_class {drug_class!r}; valid: {sorted(classes)}"
            )
        classes = {key: classes[key]}

    return {
        "classes": {
            name: [
                {"rxnorm_code": code, "display": disp, "dose": dose}
                for (code, disp, dose) in items
            ]
            for name, items in classes.items()
        },
    }


@_app.tool()
def list_locale_data(
    section: Literal["names", "cities", "conditions", "all"] = "all",
) -> dict:
    """Return the Turkish locale vocabulary (names, cities, condition displays).

    None of these strings are linked to real Turkish citizens — sources
    are TÜİK frequency reports plus the ISO 3166-2:TR province list.
    """
    from .locale import turkish as _tk

    out: dict = {
        "notes": (
            "Locale *vocabulary* only. No name+city combination here "
            "corresponds to a real person."
        ),
    }
    s = section.lower()
    if s in ("names", "all"):
        out["given_names_male"] = list(_tk.GIVEN_NAMES_MALE)
        out["given_names_female"] = list(_tk.GIVEN_NAMES_FEMALE)
        out["family_names"] = list(_tk.FAMILY_NAMES)
    if s in ("cities", "all"):
        out["cities"] = [
            {"name": name, "code": code, "weight": float(w)}
            for (name, code, w) in _tk.CITIES_TR
        ]
    if s in ("conditions", "all"):
        out["condition_display_tr"] = dict(_tk.CONDITION_DISPLAY_TR)
    return out


@_app.tool()
def list_clinical_assessment_instruments() -> dict:
    """LOINC/SNOMED codes + scoring ranges for PHQ-9 / GAD-7 / Charlson / family history."""
    return {
        "instruments": [
            {
                "name": "PHQ-9",
                "loinc": "44261-6",
                "system": "http://loinc.org",
                "scale": [0, 27],
                "abnormal_threshold": 10,
                "triggered_by_flag": "Depresyon",
                "category": "survey",
            },
            {
                "name": "GAD-7",
                "loinc": "70274-6",
                "system": "http://loinc.org",
                "scale": [0, 21],
                "abnormal_threshold": 10,
                "triggered_by_flag": "Anksiyete",
                "category": "survey",
            },
            {
                "name": "Charlson Comorbidity Index",
                "loinc": "75618-7",
                "system": "http://loinc.org",
                "scale": [0, 37],
                "abnormal_threshold": 5,
                "triggered_by_flag": "charlson_cci > 0",
                "category": "risk-assessment",
            },
            {
                "name": "FamilyMemberHistory",
                "loinc": None,
                "system": "http://snomed.info/sct",
                "triggered_by_flag": "rf_kanser / rf_kronik_hastalik",
                "category": "family-history",
                "snomed_codes": {
                    "rf_kanser": ("363346000", "Malignant neoplastic disease (disorder)"),
                    "rf_kronik_hastalik": ("237603008", "Disorder of long duration (disorder)"),
                },
            },
        ],
    }


@_app.tool()
def list_modules_detail(module: str | None = None) -> dict:
    """Per-module emission detail (encounters, procedures, medications, CarePlan)."""
    detail: list[dict] = [
        {
            "name": "hypertension",
            "triggers_on": ["Hipertansiyon"],
            "emits": {
                "encounters": ["Encounter (AMB / Follow-up SCT 390906007)"],
                "medications": ["lisinopril 314076", "amlodipine 197361",
                                "losartan 308135", "hydrochlorothiazide 310798"],
                "careplans": ["Hypertension care plan (dietary + CV-prevention counseling)"],
            },
            "trigger_logic_summary": (
                "Emits a follow-up encounter and 1-2 antihypertensives "
                "(dual therapy when bp_systolic ≥ 160 mmHg)."
            ),
        },
        {
            "name": "diabetes",
            "triggers_on": ["DM_Tum", "DM_Komplikasyonlu"],
            "emits": {
                "encounters": ["Encounter (AMB / diabetes follow-up)"],
                "medications": ["metformin 860975", "insulin glargine 575145 if complicated"],
                "procedures": ["HbA1c monitoring procedure"],
                "careplans": ["Diabetes care plan (glycemic targets + lifestyle)"],
            },
            "trigger_logic_summary": (
                "Metformin as first-line; insulin added when DM_Komplikasyonlu=1."
            ),
        },
        {
            "name": "hyperlipidemia",
            "triggers_on": ["Hiperlipidemi"],
            "emits": {
                "encounters": ["Encounter (AMB)"],
                "medications": ["atorvastatin 617312 (moderate-intensity)",
                                "rosuvastatin 859749 (high-intensity if LDL ≥ 190)"],
                "careplans": ["Lipid management care plan"],
            },
            "trigger_logic_summary": "Statin selection driven by ldl_direct_latest threshold.",
        },
        {
            "name": "thyroid",
            "triggers_on": ["Tiroid"],
            "emits": {
                "encounters": ["Encounter (AMB / endocrinology follow-up)"],
                "medications": ["levothyroxine 966247"],
            },
            "trigger_logic_summary": "Single-drug levothyroxine pathway.",
        },
        {
            "name": "depression",
            "triggers_on": ["Depresyon"],
            "emits": {
                "encounters": ["Encounter (AMB)"],
                "medications": ["sertraline 312940"],
                "observations": ["PHQ-9 (LOINC 44261-6) via clinical_extras"],
            },
            "trigger_logic_summary": "SSRI prescription + PHQ-9 emitted when flag = 1.",
        },
        {
            "name": "anxiety",
            "triggers_on": ["Anksiyete"],
            "emits": {
                "encounters": ["Encounter (AMB)"],
                "medications": ["escitalopram 321988", "buspirone 857005"],
                "observations": ["GAD-7 (LOINC 70274-6) via clinical_extras"],
            },
            "trigger_logic_summary": "SSRI or buspirone + GAD-7 emitted when flag = 1.",
        },
        {
            "name": "ihd",
            "triggers_on": ["Iskemik_Kalp"],
            "emits": {
                "encounters": ["Encounter (AMB cardiology)"],
                "medications": ["aspirin 243670", "metoprolol 866412", "atorvastatin 617312"],
                "careplans": ["Secondary prevention CV care plan"],
            },
            "trigger_logic_summary": "Aspirin + β-blocker + statin combination.",
        },
        {
            "name": "asthma",
            "triggers_on": ["Astim"],
            "emits": {
                "encounters": ["Encounter (AMB pulmonology)"],
                "medications": ["albuterol SABA 329498", "fluticasone ICS 896001"],
            },
            "trigger_logic_summary": "SABA + ICS step-up.",
        },
        {
            "name": "copd",
            "triggers_on": ["COPD"],
            "emits": {
                "encounters": ["Encounter (AMB pulmonology)"],
                "medications": ["tiotropium LABA 637202", "albuterol SABA 329498"],
            },
            "trigger_logic_summary": "LABA + SABA combination.",
        },
        {
            "name": "ckd",
            "triggers_on": ["Kronik_Bobrek"],
            "emits": {
                "encounters": ["Encounter (AMB nephrology)"],
                "conditions": ["Stage-specific N18.x + SNOMED via ckd_stage_for_egfr"],
                "careplans": ["CKD monitoring (eGFR / albuminuria)"],
            },
            "trigger_logic_summary": "KDIGO G1-G5 staging from eGFR; stage-aware condition emitted.",
        },
    ]
    if module is not None:
        m = module.lower()
        detail = [d for d in detail if d["name"] == m]
        if not detail:
            raise ValueError(f"unknown module {module!r}")
    return {"modules": detail}


@_app.tool()
def list_pipeline_config_options() -> dict:
    """Documents every PipelineConfig field with default + type + description."""
    from .pipeline import PipelineConfig

    descriptions = {
        "n": "target number of synthetic episodes",
        "cohort": "'tolerant' or 'strict' bundled cohort",
        "random_seed": "RNG seed for full pipeline reproducibility",
        "oversample_factor": "multiplier when rejection-sampling against constraints",
        "write_csv": "emit synthetic_<cohort>_episodes.csv",
        "write_fhir": "emit FHIR R4 bundles",
        "fhir_format": "'ndjson' or 'bundle'",
        "run_modules": "execute the 9 Synthea-style clinical modules",
        "longitudinal": "expand baselines into multi-encounter trajectories",
        "encounters_per_patient_mean": "Poisson mean of encounters per patient",
        "years_of_history": "trajectory window length in years",
        "constraint": "ConstraintConfig — physiologic-coherence rules",
        "registry_dir": "where to store the model card (optional)",
        "write_validation": "emit validation_report.json",
        "apply_conditional_missingness": (
            "v0.5.2 joint comorbidity-conditional missingness model"
        ),
        "include_clinical_normal_report": (
            "G3 fraction-within-reference appended to validation_report"
        ),
        "include_lab_history": "5.5 AR(1) lab time-series in FHIR Observations",
        "include_curation_flags": (
            "keep source-pipeline metadata flags (pristine_*, berturk_*, rf_*)"
        ),
    }
    out: list[dict] = []
    inst = PipelineConfig()
    for f in _dc_fields(PipelineConfig):
        try:
            default = getattr(inst, f.name)
            if hasattr(default, "__dict__"):
                default = str(default)
        except Exception:
            default = None
        out.append({
            "name": f.name,
            "type": str(f.type),
            "default": default,
            "description": descriptions.get(f.name, ""),
        })
    return {"config_fields": out}


@_app.tool()
def ckd_stage_for_egfr(egfr: float) -> dict:
    """KDIGO 2024 CKD staging (G1-G5) for an eGFR value + SNOMED/ICD-10."""
    from .fhir.codes import ckd_stage_for_egfr as _stage

    result = _stage(egfr)
    if result is None:
        return {"stage": None, "snomed": None, "icd10": None, "egfr": egfr}
    label, snomed, icd10 = result
    return {
        "egfr": float(egfr),
        "stage": label,
        "snomed": [snomed[0], snomed[1]],
        "icd10": [icd10[0], icd10[1]],
    }


@_app.tool()
def validate_condition_expression(
    condition: str,
    cohort: Literal["tolerant", "strict"] = "tolerant",
) -> dict:
    """Pre-validate a ``sample_conditional`` expression without sampling.

    Walks the AST with syntha's allowlist validator and lists the
    columns the expression references. Returns ``valid=False`` and a
    human-readable error on failure.
    """
    import ast

    from .conditional import _ALLOWED_AST_NODES

    gen = _load_bundled(cohort)
    m = gen.model
    assert m is not None
    valid_cols = set(m.columns)

    try:
        tree = ast.parse(condition, mode="eval")
    except SyntaxError as e:
        return {"valid": False, "columns_referenced": [], "error": f"syntax error: {e}"}

    referenced: set[str] = set()
    for node in ast.walk(tree):
        if type(node) not in _ALLOWED_AST_NODES:
            return {
                "valid": False, "columns_referenced": sorted(referenced),
                "error": f"disallowed construct {type(node).__name__!r}",
            }
        if isinstance(node, ast.Name):
            referenced.add(node.id)
            if node.id not in valid_cols:
                return {
                    "valid": False, "columns_referenced": sorted(referenced),
                    "error": (
                        f"unknown column {node.id!r}; not modeled by the "
                        f"{cohort} cohort"
                    ),
                }
    return {
        "valid": True,
        "columns_referenced": sorted(referenced),
        "error": None,
    }


@_app.tool()
def get_correlation_pairs(
    cohort: Literal["tolerant", "strict"] = "tolerant",
    top_k: int = 30,
    min_abs_corr: float = 0.1,
) -> dict:
    """Top-K Spearman correlation pairs from a bundled cohort.

    Each pair has ``a``, ``b``, ``spearman``. Pairs are sorted by
    ``|spearman|`` descending and filtered by ``min_abs_corr``.
    """
    gen = _load_bundled(cohort)
    m = gen.model
    assert m is not None
    top_k = max(1, min(int(top_k), 500))
    pairs = _top_correlation_pairs(m, top_k=top_k, min_abs_corr=float(min_abs_corr))
    return {
        "cohort": cohort,
        "top_k": top_k,
        "min_abs_corr": float(min_abs_corr),
        "pairs": pairs,
        "full_matrix_available": True,
    }


@_app.tool()
def get_model_card(cohort: Literal["tolerant", "strict"] = "tolerant") -> dict:
    """Return the model card (n_train, marginals, continuous quantile summary, top correlations)."""
    return _model_card_dict(cohort)


# ─────────────────────────────────────────────────────────────────────
# Tool annotations — per MCP spec, every tool advertises read-only /
# destructive / open-world / idempotent hints. Every syntha tool loads
# bundled JSON, computes, returns; none mutate state, write to disk, or
# call external services. So one global annotation applies to all tools.
# Anthropic Connector reviewers introspect tools/list and look for these
# hints to size the trust / consent surface.
# ─────────────────────────────────────────────────────────────────────

_TOOL_TITLES: dict[str, str] = {
    "syntha_version":                       "Library version",
    "list_bundled_cohorts":                 "List bundled cohorts",
    "get_cohort_summary":                   "Cohort summary",
    "get_model_card":                       "Model card",
    "generate_cohort_csv":                  "Generate cohort (CSV)",
    "generate_cohort_fhir":                 "Generate cohort (FHIR R4)",
    "generate_longitudinal_cohort":         "Generate longitudinal cohort (CSV)",
    "generate_longitudinal_fhir":           "Generate longitudinal cohort (FHIR R4)",
    "generate_cohort_with_lab_history":     "Generate cohort with lab time-series",
    "generate_clinical_assessments":        "Generate clinical-assessment resources",
    "sample_conditional":                   "Conditional rejection sampling",
    "validate_synthetic_csv":               "Validate two CSVs",
    "validate_against_bundled_cohort":      "Validate synthetic CSV vs bundled cohort",
    "privacy_audit":                        "Privacy audit (MIA + AIA)",
    "privacy_audit_bundled":                "Privacy self-audit (demo)",
    "fraction_within_reference":            "Fraction within reference ranges",
    "check_row_within_reference":           "Check one row against reference ranges",
    "apply_physiologic_constraints":        "Apply physiologic-coherence filter",
    "list_clinical_modules":                "List clinical modules",
    "list_modules_detail":                  "List clinical-module detail",
    "list_physiologic_constraints":         "List physiologic constraints",
    "list_reference_ranges":                "List reference ranges",
    "list_schema_columns":                  "List schema columns",
    "list_condition_codes":                 "List condition codes",
    "list_lab_loinc_codes":                 "List lab LOINC codes",
    "list_lab_panels":                      "List lab panels",
    "list_lab_drift_profiles":              "List lab drift profiles",
    "list_rxnorm_medications":              "List RxNorm medications",
    "list_locale_data":                     "List Turkish-locale data",
    "list_clinical_assessment_instruments": "List clinical-assessment instruments",
    "list_pipeline_config_options":         "List PipelineConfig options",
    "ckd_stage_for_egfr":                   "CKD staging from eGFR",
    "validate_condition_expression":        "Validate condition expression",
    "get_correlation_pairs":                "Get correlation pairs",
}


def _annotate_registered_tools() -> None:
    """Apply MCP ToolAnnotations to every @_app.tool()-registered tool.

    Called once at import time, after all @tool decorators have run. We
    don't add annotations to each decorator individually because (a) the
    answer is the same for every syntha tool — read-only, deterministic,
    no side effects — and (b) running this once keeps the 34 decorators
    visually clean.
    """
    try:
        from mcp.types import ToolAnnotations
    except ImportError:  # pragma: no cover — older mcp-sdk
        return

    # The tool registry lives at _app._tool_manager._tools in the public
    # FastMCP layout (mcp-sdk ≥ 1.2). Be defensive: silently no-op if the
    # internal layout has moved.
    tm = getattr(_app, "_tool_manager", None)
    tools = getattr(tm, "_tools", None)
    if not isinstance(tools, dict):
        return

    for name, tool in tools.items():
        # If a tool already has an annotation block, leave it alone — the
        # author's explicit choice wins.
        if getattr(tool, "annotations", None) is not None:
            continue
        try:
            tool.annotations = ToolAnnotations(
                title=_TOOL_TITLES.get(name, name.replace("_", " ").title()),
                readOnlyHint=True,
                destructiveHint=False,
                openWorldHint=False,
                idempotentHint=True,
            )
        except Exception:
            # If ToolAnnotations doesn't accept these keys on the installed
            # SDK version, fall back to setting just title via dict-attr.
            try:
                tool.annotations = ToolAnnotations(title=_TOOL_TITLES.get(name, name))
            except Exception:
                pass


_annotate_registered_tools()


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
