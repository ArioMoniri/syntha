"""Column groupings and physiologic reference ranges for the pristine-episode CSVs."""
from __future__ import annotations

# Pass-through columns generated/replaced at sample time (not modeled).
ID_COLUMNS = ["RF_EPISODE2", "HASTA_ID", "episode_date"]

# Continuous lab/vital measurements.
LAB_COLUMNS = [
    "glucose_fasting_latest",
    "ldl_direct_latest",
    "hdl_latest",
    "cholesterol_total_latest",
    "triglycerides_latest",
    "egfr_latest",
    "creatinine_latest",
    "hemoglobin_latest",
    "wbc_latest",
    "platelets_latest",
    "alt_latest",
    "ast_latest",
    "ferritin_latest",
    "vitamin_b12_latest",
]

VITAL_COLUMNS = ["bp_systolic", "bp_diastolic"]

DEMOGRAPHIC_COLUMNS = ["age", "gender_is_male"]

# Count / ordinal columns kept continuous in the copula then rounded.
COUNT_COLUMNS = [
    "n_drugs",
    "n_medications",
    "drug_class_count",
    "charlson_cci",
    "comorbidity_count",
    "n_ep_labs_available_x",
    "keyword_total_flags",
    "lab_abnormal_pct",
    "max_ilac_onem",
    "mean_ilac_onem",
    "berturk_similarity",
    "tier_healthy_patient",
]

# 20 comorbidity flags (Turkish source labels) → grouped by clinical area.
COMORBIDITY_COLUMNS = [
    "Kanser", "Iskemik_Kalp", "Serebrovaskuler", "Kalp_Yetmezligi",
    "Pulmoner_Emboli", "Aort_Anevrizma", "Kronik_Bobrek", "Karaciger_Siroz",
    "Sepsis", "Atriyal_Fibrilasyon", "COPD", "DM_Komplikasyonlu", "DM_Tum",
    "Astim", "Hipertansiyon", "Hiperlipidemi", "Tiroid", "Obezite",
    "Depresyon", "Anksiyete",
]

# Risk-factor and quality flags (binary).
FLAG_COLUMNS = [
    "pristine_strict", "pristine_tolerant", "tier_healthy_episode",
    "is_cancer", "is_ex", "is_cancer_or_ex", "drug_safe",
    "has_rx_data", "has_blacklist_drug", "rule_clean", "keyword_clean",
    "berturk_clean", "text_available", "nlp_filter_pass",
    "all_ep_labs_normal_x", "polypharmacy_flag", "high_risk_drug_flag",
    "has_nontolerable_icd_30d", "any_worsening",
    "rf_kanser", "rf_kronik_hastalik", "rf_akut_ciddi",
    "rf_psikiyatri_ciddi", "rf_ilac_risk_metin", "rf_fonksiyon_kaybi",
]


# Lab panel groupings — single source of truth used by both
# fhir.panels.PANELS (for DiagnosticReport grouping) and
# generator.missingness.DEFAULT_PANEL_GROUPS (for panel-co-missingness
# propagation). Each entry: (panel_id, LOINC_code, panel_display,
# constituent-column-list).
LAB_PANELS: list[tuple[str, str, str, list[str]]] = [
    ("lipid", "57698-3", "Lipid panel with direct LDL — Serum or Plasma",
     ["cholesterol_total_latest", "hdl_latest", "ldl_direct_latest",
      "triglycerides_latest"]),
    ("cbc", "58410-2", "Complete blood count (hemogram) panel — Blood by Automated count",
     ["hemoglobin_latest", "wbc_latest", "platelets_latest"]),
    ("cmp", "24323-8", "Comprehensive metabolic panel — Serum or Plasma",
     ["glucose_fasting_latest", "creatinine_latest", "egfr_latest",
      "alt_latest", "ast_latest"]),
    ("iron", "24350-1", "Iron and binding capacity — Serum or Plasma",
     ["ferritin_latest"]),
    ("bp", "85354-9", "Blood pressure panel with all children optional",
     ["bp_systolic", "bp_diastolic"]),
]


def all_modeled_columns() -> list[str]:
    return (
        DEMOGRAPHIC_COLUMNS
        + LAB_COLUMNS
        + VITAL_COLUMNS
        + COUNT_COLUMNS
        + COMORBIDITY_COLUMNS
        + FLAG_COLUMNS
    )


def binary_columns() -> list[str]:
    return ["gender_is_male"] + COMORBIDITY_COLUMNS + FLAG_COLUMNS


def continuous_columns() -> list[str]:
    return ["age"] + LAB_COLUMNS + VITAL_COLUMNS + COUNT_COLUMNS


# Physiologically plausible bounds — used to clip post-sample outliers.
# Values outside these are biologically implausible for living adults.
PHYSIOLOGIC_BOUNDS: dict[str, tuple[float, float]] = {
    "age": (18, 100),
    "glucose_fasting_latest": (40, 500),
    "ldl_direct_latest": (10, 400),
    "hdl_latest": (10, 150),
    "cholesterol_total_latest": (60, 600),
    "triglycerides_latest": (20, 2000),
    "egfr_latest": (5, 200),
    "creatinine_latest": (0.2, 15.0),
    "hemoglobin_latest": (4.0, 22.0),
    "wbc_latest": (0.5, 50.0),
    "platelets_latest": (10, 1000),
    "alt_latest": (1, 2000),
    "ast_latest": (1, 2000),
    "ferritin_latest": (1, 5000),
    "vitamin_b12_latest": (50, 5000),
    "bp_systolic": (70, 250),
    "bp_diastolic": (40, 150),
}
