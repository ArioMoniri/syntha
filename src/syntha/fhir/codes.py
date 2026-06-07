"""LOINC, SNOMED CT, and ICD-10 code tables.

Every Condition resource is emitted with **dual coding**: SNOMED CT (the FHIR
preferred clinical terminology) plus ICD-10 (used by Turkish billing /
administrative pipelines). Code text carries both English and Turkish
preferred terms for the condition.
"""
from __future__ import annotations

from ..locale.turkish import CONDITION_DISPLAY_TR

# (LOINC code, display, UCUM unit) per modeled lab/vital column.
LAB_LOINC: dict[str, tuple[str, str, str]] = {
    "glucose_fasting_latest": ("1558-6", "Fasting glucose [Mass/volume] in Serum or Plasma", "mg/dL"),
    "ldl_direct_latest": ("18262-6", "LDL Cholesterol [Mass/volume] in Serum or Plasma by Direct assay", "mg/dL"),
    "hdl_latest": ("2085-9", "HDL Cholesterol [Mass/volume] in Serum or Plasma", "mg/dL"),
    "cholesterol_total_latest": ("2093-3", "Cholesterol [Mass/volume] in Serum or Plasma", "mg/dL"),
    "triglycerides_latest": ("2571-8", "Triglyceride [Mass/volume] in Serum or Plasma", "mg/dL"),
    "egfr_latest": ("62238-1", "Glomerular filtration rate/1.73 sq M.predicted [Volume Rate/Area] in Serum or Plasma by Creatinine-based formula (CKD-EPI)", "mL/min/{1.73_m2}"),
    "creatinine_latest": ("2160-0", "Creatinine [Mass/volume] in Serum or Plasma", "mg/dL"),
    "hemoglobin_latest": ("718-7", "Hemoglobin [Mass/volume] in Blood", "g/dL"),
    "wbc_latest": ("6690-2", "Leukocytes [#/volume] in Blood by Automated count", "10*3/uL"),
    "platelets_latest": ("777-3", "Platelets [#/volume] in Blood by Automated count", "10*3/uL"),
    "alt_latest": ("1742-6", "Alanine aminotransferase [Enzymatic activity/volume] in Serum or Plasma", "U/L"),
    "ast_latest": ("1920-8", "Aspartate aminotransferase [Enzymatic activity/volume] in Serum or Plasma", "U/L"),
    "ferritin_latest": ("2276-4", "Ferritin [Mass/volume] in Serum or Plasma", "ng/mL"),
    "vitamin_b12_latest": ("2132-9", "Cobalamin (Vitamin B12) [Mass/volume] in Serum or Plasma", "pg/mL"),
    "bp_systolic": ("8480-6", "Systolic blood pressure", "mm[Hg]"),
    "bp_diastolic": ("8462-4", "Diastolic blood pressure", "mm[Hg]"),
}

# SNOMED CT codes for the 20 source-CSV comorbidity flags.
CONDITION_SNOMED: dict[str, tuple[str, str]] = {
    "Kanser": ("363346000", "Malignant neoplastic disease (disorder)"),
    "Iskemik_Kalp": ("414545008", "Ischemic heart disease (disorder)"),
    "Serebrovaskuler": ("62914000", "Cerebrovascular disease (disorder)"),
    "Kalp_Yetmezligi": ("84114007", "Heart failure (disorder)"),
    "Pulmoner_Emboli": ("59282003", "Pulmonary embolism (disorder)"),
    "Aort_Anevrizma": ("67362008", "Aortic aneurysm (disorder)"),
    "Kronik_Bobrek": ("709044004", "Chronic kidney disease (disorder)"),
    "Karaciger_Siroz": ("19943007", "Cirrhosis of liver (disorder)"),
    "Sepsis": ("91302008", "Sepsis (disorder)"),
    "Atriyal_Fibrilasyon": ("49436004", "Atrial fibrillation (disorder)"),
    "COPD": ("13645005", "Chronic obstructive pulmonary disease (disorder)"),
    # DM_Komplikasyonlu: SCT does not have a single generic
    # "diabetes-with-complications" parent. The previously-used 75682002 was
    # the rare type-B insulin-receptor-antibody form — wrong. We now use
    # 44054006 (Type 2 diabetes mellitus) on the assumption the complicated
    # cases in this Turkish-cohort source are predominantly T2DM, and rely on
    # the paired ICD-10 (E11.8) below to convey "with unspecified
    # complications".
    "DM_Komplikasyonlu": ("44054006", "Type 2 diabetes mellitus (disorder)"),
    "DM_Tum": ("73211009", "Diabetes mellitus (disorder)"),
    "Astim": ("195967001", "Asthma (disorder)"),
    "Hipertansiyon": ("38341003", "Hypertensive disorder, systemic arterial (disorder)"),
    "Hiperlipidemi": ("55822004", "Hyperlipidemia (disorder)"),
    "Tiroid": ("14304000", "Disorder of thyroid gland (disorder)"),
    "Obezite": ("414916001", "Obesity (disorder)"),
    "Depresyon": ("35489007", "Depressive disorder (disorder)"),
    "Anksiyete": ("48694002", "Anxiety (finding)"),
}

# ICD-10 codes paired with each comorbidity flag. Codes use the unspecified
# form when source CSV does not distinguish subtype (e.g. E11.9 for DM).
CONDITION_ICD10: dict[str, tuple[str, str]] = {
    "Kanser": ("C80.1", "Malignant neoplasm, unspecified"),
    "Iskemik_Kalp": ("I25.9", "Chronic ischaemic heart disease, unspecified"),
    "Serebrovaskuler": ("I67.9", "Cerebrovascular disease, unspecified"),
    "Kalp_Yetmezligi": ("I50.9", "Heart failure, unspecified"),
    "Pulmoner_Emboli": ("I26.9", "Pulmonary embolism without acute cor pulmonale"),
    "Aort_Anevrizma": ("I71.9", "Aortic aneurysm of unspecified site, without mention of rupture"),
    "Kronik_Bobrek": ("N18.9", "Chronic kidney disease, unspecified"),
    "Karaciger_Siroz": ("K74.6", "Other and unspecified cirrhosis of liver"),
    "Sepsis": ("A41.9", "Sepsis, unspecified organism"),
    "Atriyal_Fibrilasyon": ("I48.91", "Unspecified atrial fibrillation"),
    "COPD": ("J44.9", "Chronic obstructive pulmonary disease, unspecified"),
    "DM_Komplikasyonlu": ("E11.8", "Type 2 diabetes mellitus with unspecified complications"),
    "DM_Tum": ("E11.9", "Type 2 diabetes mellitus without complications"),
    "Astim": ("J45.9", "Asthma, unspecified"),
    "Hipertansiyon": ("I10", "Essential (primary) hypertension"),
    "Hiperlipidemi": ("E78.5", "Hyperlipidaemia, unspecified"),
    "Tiroid": ("E07.9", "Disorder of thyroid, unspecified"),
    "Obezite": ("E66.9", "Obesity, unspecified"),
    "Depresyon": ("F32.9", "Depressive episode, unspecified"),
    "Anksiyete": ("F41.9", "Anxiety disorder, unspecified"),
}

# --- CKD staging (KDIGO G1–G5, eGFR-driven) -------------------------------
# Stage-specific SNOMED CT + ICD-10 used by the CKD module. eGFR thresholds
# follow KDIGO 2024 (mL/min/1.73 m²). ICD-10 N18.x maps 1:1 onto the KDIGO
# stages; SNOMED CT has dedicated stage concepts.
#
# CLINICAL CONFIRMATION NEEDED (see PR checklist): KDIGO is the international
# standard and TR primary-care follows it, but the nephrology-referral stage
# (G3b vs G4) should be confirmed against TR practice.
#
# Each entry: (eGFR low-inclusive, eGFR high-exclusive, stage label,
#              (SNOMED code, SNOMED display), (ICD-10 code, ICD-10 display)).
CKD_STAGES: list[tuple[float, float, str, tuple[str, str], tuple[str, str]]] = [
    (90.0, float("inf"), "G1",
     ("431855005", "Chronic kidney disease stage 1 (disorder)"),
     ("N18.1", "Chronic kidney disease, stage 1")),
    (60.0, 90.0, "G2",
     ("431856006", "Chronic kidney disease stage 2 (disorder)"),
     ("N18.2", "Chronic kidney disease, stage 2 (mild)")),
    (45.0, 60.0, "G3a",
     ("700378005", "Chronic kidney disease stage 3A (disorder)"),
     ("N18.3", "Chronic kidney disease, stage 3 (moderate)")),
    (30.0, 45.0, "G3b",
     ("700379002", "Chronic kidney disease stage 3B (disorder)"),
     ("N18.3", "Chronic kidney disease, stage 3 (moderate)")),
    (15.0, 30.0, "G4",
     ("431857002", "Chronic kidney disease stage 4 (disorder)"),
     ("N18.4", "Chronic kidney disease, stage 4 (severe)")),
    (0.0, 15.0, "G5",
     ("433146000", "Chronic kidney disease stage 5 (disorder)"),
     ("N18.5", "Chronic kidney disease, stage 5")),
]


def ckd_stage_for_egfr(egfr: float | None) -> tuple[str, tuple[str, str], tuple[str, str]] | None:
    """Map an eGFR (mL/min/1.73 m²) to its KDIGO stage + SNOMED/ICD-10 codes.

    Returns ``(stage_label, snomed, icd10)`` or ``None`` when eGFR is missing
    (no staging possible — caller falls back to the generic ``N18.9``).
    """
    if egfr is None:
        return None
    try:
        v = float(egfr)
    except (TypeError, ValueError):
        return None
    for lo, hi, label, snomed, icd10 in CKD_STAGES:
        if lo <= v < hi:
            return label, snomed, icd10
    return None


GENDER_MAP = {1: "male", 0: "female"}


def condition_display_dual(flag: str) -> str:
    """English/Turkish bilingual display string for a comorbidity flag."""
    en = CONDITION_SNOMED.get(flag, (None, flag))[1]
    tr = CONDITION_DISPLAY_TR.get(flag, flag)
    return f"{en} / {tr}"
