"""LOINC and SNOMED CT code tables for the columns this generator emits."""
from __future__ import annotations

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

# SNOMED CT codes for the 20 Turkish-labeled comorbidity flags.
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
    "DM_Komplikasyonlu": ("75682002", "Diabetes mellitus due to insulin receptor antibodies (disorder)"),
    "DM_Tum": ("73211009", "Diabetes mellitus (disorder)"),
    "Astim": ("195967001", "Asthma (disorder)"),
    "Hipertansiyon": ("38341003", "Hypertensive disorder, systemic arterial (disorder)"),
    "Hiperlipidemi": ("55822004", "Hyperlipidemia (disorder)"),
    "Tiroid": ("14304000", "Disorder of thyroid gland (disorder)"),
    "Obezite": ("414916001", "Obesity (disorder)"),
    "Depresyon": ("35489007", "Depressive disorder (disorder)"),
    "Anksiyete": ("48694002", "Anxiety (finding)"),
}

GENDER_MAP = {1: "male", 0: "female"}
