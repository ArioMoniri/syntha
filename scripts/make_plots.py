"""Generate README figures from the bundled tolerant copula model JSON.

The script intentionally does **not** depend on the source CSV (which is
PHI-adjacent and gitignored). Instead it reads the v2 model JSON that
already ships in ``app/src/model_tolerant.json``:

  * **Source** marginals come straight from the model:
      - continuous columns → ``continuous_quantiles[col]`` (the empirical
        order-statistics grid stored when the model was fitted)
      - binary columns → ``binary_p[col]`` (the empirical prevalence)
  * **Synthetic** is drawn by running the actual sampler against the model
    via ``syntha.cli sample`` so the figures track whatever the released
    desktop app would produce.

Outputs (PNG, ~150 DPI) into docs/figures/:
  * distributions.png  — 2×3 grid of source vs synthetic histograms for
                          key continuous columns (age, BP, glucose, HDL,
                          hemoglobin, eGFR).
  * correlations.png   — side-by-side Spearman correlation heatmaps for a
                          subset of clinical variables.
  * prevalence.png     — disease-prevalence bar chart for the most common
                          comorbidities in the tolerant cohort.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Make the package importable without `pip install -e .`.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from syntha.models.registry import ModelRegistry  # noqa: E402

MODEL_JSON = ROOT / "app/src/model_tolerant.json"
REGISTRY_DIR = ROOT / "output/tolerant/models"
REGISTRY_NAME = "copula_tolerant"
OUT_DIR = ROOT / "docs/figures"

# Number of synthetic samples — large enough for smooth histograms even on
# discretized source columns like BP (multiples of 5/10 mmHg dominate).
N_SYNTHETIC = 5000
SEED = 42

CONT_PLOT_COLS = [
    ("age", "Age (years)"),
    ("bp_systolic", "Systolic BP (mmHg)"),
    ("glucose_fasting_latest", "Fasting glucose (mg/dL)"),
    ("hdl_latest", "HDL (mg/dL)"),
    ("hemoglobin_latest", "Hemoglobin (g/dL)"),
    ("egfr_latest", "eGFR (mL/min/1.73 m²)"),
]
CORR_COLS = [
    "age", "bp_systolic", "bp_diastolic", "glucose_fasting_latest",
    "hdl_latest", "ldl_direct_latest", "hemoglobin_latest", "egfr_latest",
    "creatinine_latest",
]
# Only show comorbidities with non-trivial prevalence in the tolerant
# cohort — otherwise the bar chart collapses to an empty axis (as it did
# on strict, where every comorbidity is 0% by construction).
PREVALENCE_COLS = [
    ("Tiroid", "Thyroid disorder"),
    ("Hiperlipidemi", "Hyperlipidemia"),
    ("Hipertansiyon", "Hypertension"),
    ("DM_Tum", "Diabetes"),
    ("Iskemik_Kalp", "Ischemic heart dis."),
    ("Astim", "Asthma"),
    ("COPD", "COPD"),
    ("Kanser", "Cancer"),
    ("Anksiyete", "Anxiety"),
    ("Atriyal_Fibrilasyon", "Atrial fib."),
]


def _load_model_payload() -> dict:
    if not MODEL_JSON.exists():
        raise SystemExit(f"missing bundled model: {MODEL_JSON} — run scripts/refresh_app_model.sh")
    return json.loads(MODEL_JSON.read_text())


def _sample_synthetic(n: int) -> pd.DataFrame:
    if not (REGISTRY_DIR / REGISTRY_NAME).exists():
        raise SystemExit(
            f"missing registered model: {REGISTRY_DIR}/{REGISTRY_NAME}\n"
            "Run `bash scripts/refresh_app_model.sh` first."
        )
    gen, _card = ModelRegistry(str(REGISTRY_DIR)).load(REGISTRY_NAME)
    return gen.sample(n)


def _plot_distributions(payload: dict, syn: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(2, 3, figsize=(13, 7))
    fig.suptitle(
        f"Source vs synthetic — marginal distributions (tolerant cohort, "
        f"n_train = {payload['n_train']:,}, n_synth = {len(syn):,})",
        fontsize=12, fontweight="bold",
    )
    for ax, (col, label) in zip(axes.flat, CONT_PLOT_COLS):
        source_q = np.asarray(payload["continuous_quantiles"].get(col, []), dtype=float)
        source_q = source_q[~np.isnan(source_q)]
        t = pd.to_numeric(syn[col], errors="coerce").dropna().to_numpy() if col in syn.columns else np.array([])
        if source_q.size == 0 or t.size == 0:
            ax.set_title(f"{label} (no data)")
            continue
        lo = float(min(source_q.min(), t.min()))
        hi = float(max(source_q.max(), t.max()))
        bins = np.linspace(lo, hi, 45)
        ax.hist(source_q, bins=bins, alpha=0.55, color="#1f77b4",
                label="source", density=True)
        ax.hist(t, bins=bins, alpha=0.55, color="#ff7f0e",
                label="synthetic", density=True)
        ax.set_title(label, fontsize=10)
        ax.tick_params(labelsize=8)
        ax.legend(fontsize=8)
    fig.tight_layout()
    target = OUT_DIR / "distributions.png"
    fig.savefig(target, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return target


def _empirical_correlation_from_payload(payload: dict, cols: list[str]) -> pd.DataFrame:
    """Read source Spearman correlation from the stored correlation matrix.

    The model JSON ships the *latent-Gaussian* correlation matrix; converting
    it back to Spearman would be ``ρ_s = (6/π) arcsin(ρ/2)``. We only need
    relative magnitudes for the heatmap so we plot the latent ρ directly.
    """
    full_cols = payload["columns"]
    mat = np.asarray(payload["correlation"], dtype=float)
    idx = [full_cols.index(c) for c in cols if c in full_cols]
    sub = mat[np.ix_(idx, idx)]
    return pd.DataFrame(sub, columns=[full_cols[i] for i in idx], index=[full_cols[i] for i in idx])


def _plot_correlations(payload: dict, syn: pd.DataFrame) -> Path:
    cols = [c for c in CORR_COLS if c in payload["columns"] and c in syn.columns]
    a = _empirical_correlation_from_payload(payload, cols)
    b = syn[cols].corr(method="spearman").fillna(0.0).reindex(columns=cols, index=cols)
    diff = a - b
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.5), constrained_layout=True)
    for ax, mat, title in (
        (axes[0], a, "Source ρ (latent Gaussian)"),
        (axes[1], b, "Synthetic Spearman ρ"),
        (axes[2], diff, "Source − Synthetic"),
    ):
        im = ax.imshow(mat.to_numpy(), cmap="RdBu_r", vmin=-1, vmax=1)
        ax.set_xticks(range(len(cols)))
        ax.set_yticks(range(len(cols)))
        ax.set_xticklabels(cols, rotation=45, ha="right", fontsize=8)
        ax.set_yticklabels(cols, fontsize=8)
        ax.set_title(title, fontsize=11, fontweight="bold")
        plt.colorbar(im, ax=ax, fraction=0.04, pad=0.04)
    target = OUT_DIR / "correlations.png"
    fig.savefig(target, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return target


def _plot_prevalence(payload: dict, syn: pd.DataFrame) -> Path:
    pairs = [(c, lab) for c, lab in PREVALENCE_COLS
             if c in payload["binary_p"] and c in syn.columns]
    labels = [lab for _, lab in pairs]
    src_p = [float(payload["binary_p"][c]) * 100 for c, _ in pairs]
    syn_p = [float(pd.to_numeric(syn[c], errors="coerce").dropna().mean()) * 100
             for c, _ in pairs]
    x = np.arange(len(labels))
    width = 0.4
    fig, ax = plt.subplots(figsize=(12, 5.5))
    rects_src = ax.bar(x - width / 2, src_p, width, label="source",
                        color="#1f77b4")
    rects_syn = ax.bar(x + width / 2, syn_p, width, label="synthetic",
                        color="#ff7f0e")
    # Numeric labels above each bar — the most informative way to read a
    # small-prevalence comparison.
    for rect, val in zip(rects_src, src_p):
        ax.annotate(f"{val:.1f}%", xy=(rect.get_x() + rect.get_width() / 2, val),
                    xytext=(0, 3), textcoords="offset points",
                    ha="center", va="bottom", fontsize=8, color="#1f77b4")
    for rect, val in zip(rects_syn, syn_p):
        ax.annotate(f"{val:.1f}%", xy=(rect.get_x() + rect.get_width() / 2, val),
                    xytext=(0, 3), textcoords="offset points",
                    ha="center", va="bottom", fontsize=8, color="#d97706")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel("Prevalence (%)")
    ax.set_ylim(0, max(max(src_p), max(syn_p)) * 1.18 + 1)
    ax.set_title(
        f"Comorbidity prevalence — source ({payload['n_train']:,} episodes) "
        f"vs synthetic ({len(syn):,})",
        fontsize=12, fontweight="bold",
    )
    ax.legend(loc="upper right")
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    fig.tight_layout()
    target = OUT_DIR / "prevalence.png"
    fig.savefig(target, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return target


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = _load_model_payload()
    print(f"loaded model {MODEL_JSON.name} — format {payload['format']}, "
          f"n_train={payload['n_train']:,}, cohort={payload['cohort']}")
    syn = _sample_synthetic(N_SYNTHETIC)
    print(f"sampled {len(syn):,} synthetic rows from registry {REGISTRY_DIR}")
    for p in (
        _plot_distributions(payload, syn),
        _plot_correlations(payload, syn),
        _plot_prevalence(payload, syn),
    ):
        print(f"✓ wrote {p}  ({p.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
