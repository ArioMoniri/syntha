"""Generate README figures comparing source vs synthetic distributions.

Outputs (PNG, ~150 DPI) into docs/figures/:
  * distributions.png  — 2×3 grid of source vs synthetic histograms for
                          key continuous columns (age, BP, glucose, HDL,
                          hemoglobin, eGFR).
  * correlations.png   — side-by-side Spearman correlation heatmaps for a
                          subset of clinical variables.
  * prevalence.png     — disease-prevalence bar chart for the 8 most common
                          comorbidities in the tolerant cohort.
"""
from __future__ import annotations

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

from syntha import data, preprocess  # noqa: E402

SOURCE_CSV = ROOT / "data/raw/pristine_tolerant_episodes.csv"
SYNTH_CSV = ROOT / "output/sample/synthetic_tolerant_episodes.csv"
OUT_DIR = ROOT / "docs/figures"

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
PREVALENCE_COLS = [
    ("Hiperlipidemi", "Hyperlipidemia"),
    ("Hipertansiyon", "Hypertension"),
    ("DM_Tum", "Diabetes"),
    ("Tiroid", "Thyroid disorder"),
    ("Anksiyete", "Anxiety"),
    ("Depresyon", "Depression"),
    ("Astim", "Asthma"),
    ("Obezite", "Obesity"),
]


def _load() -> tuple[pd.DataFrame, pd.DataFrame]:
    src = preprocess.coerce_types(data.filter_to_modeled(data.load_episodes(SOURCE_CSV)))
    src = preprocess.clip_to_physiologic(src)
    syn = pd.read_csv(SYNTH_CSV, low_memory=False)
    return src, syn


def _plot_distributions(src: pd.DataFrame, syn: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(2, 3, figsize=(13, 7))
    fig.suptitle(
        "Source vs synthetic — marginal distributions (tolerant cohort)",
        fontsize=13, fontweight="bold",
    )
    for ax, (col, label) in zip(axes.flat, CONT_PLOT_COLS):
        s = pd.to_numeric(src[col], errors="coerce").dropna()
        t = pd.to_numeric(syn[col], errors="coerce").dropna()
        if s.empty or t.empty:
            ax.set_title(f"{label} (no data)")
            continue
        bins = np.linspace(
            float(min(s.min(), t.min())),
            float(max(s.max(), t.max())),
            45,
        )
        ax.hist(s, bins=bins, alpha=0.55, color="#1f77b4", label="source", density=True)
        ax.hist(t, bins=bins, alpha=0.55, color="#ff7f0e", label="synthetic", density=True)
        ax.set_title(label, fontsize=10)
        ax.tick_params(labelsize=8)
        ax.legend(fontsize=8)
    fig.tight_layout()
    target = OUT_DIR / "distributions.png"
    fig.savefig(target, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return target


def _plot_correlations(src: pd.DataFrame, syn: pd.DataFrame) -> Path:
    cols = [c for c in CORR_COLS if c in src.columns and c in syn.columns]
    a = src[cols].corr(method="spearman").fillna(0.0)
    b = syn[cols].corr(method="spearman").fillna(0.0)
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.5), constrained_layout=True)
    for ax, mat, title in (
        (axes[0], a, "Source Spearman ρ"),
        (axes[1], b, "Synthetic Spearman ρ"),
        (axes[2], a - b, "Source − Synthetic"),
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


def _plot_prevalence(src: pd.DataFrame, syn: pd.DataFrame) -> Path:
    labels = [lab for _, lab in PREVALENCE_COLS]
    src_p = [float(pd.to_numeric(src[c], errors="coerce").dropna().mean()) * 100 for c, _ in PREVALENCE_COLS]
    syn_p = [float(pd.to_numeric(syn[c], errors="coerce").dropna().mean()) * 100 for c, _ in PREVALENCE_COLS]
    x = np.arange(len(labels))
    width = 0.4
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar(x - width / 2, src_p, width, label="source", color="#1f77b4")
    ax.bar(x + width / 2, syn_p, width, label="synthetic", color="#ff7f0e")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel("Prevalence (%)")
    ax.set_title(
        "Comorbidity prevalence in source vs synthetic (tolerant cohort)",
        fontsize=12, fontweight="bold",
    )
    ax.legend()
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    fig.tight_layout()
    target = OUT_DIR / "prevalence.png"
    fig.savefig(target, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return target


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    src, syn = _load()
    paths = [
        _plot_distributions(src, syn),
        _plot_correlations(src, syn),
        _plot_prevalence(src, syn),
    ]
    for p in paths:
        print(f"✓ wrote {p}  ({p.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
