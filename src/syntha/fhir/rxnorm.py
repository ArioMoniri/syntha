"""RxNorm code tables for medications prescribed by Synthea-style modules.

Each entry: (rxnorm_code, display, dose_text). Codes are real RxNorm
ingredient/SCD codes; doses are common adult starter doses.
"""
from __future__ import annotations

# (code, display, dose) — RxNorm SCD codes for common starter prescriptions.
ANTIHYPERTENSIVES = [
    ("314076", "Lisinopril 10 MG Oral Tablet", "10 mg daily"),
    ("197361", "Amlodipine 5 MG Oral Tablet", "5 mg daily"),
    ("308135", "Losartan 50 MG Oral Tablet", "50 mg daily"),
    ("310798", "Hydrochlorothiazide 25 MG Oral Tablet", "25 mg daily"),
]

ANTIDIABETICS_FIRST_LINE = [
    ("860975", "Metformin Hydrochloride 1000 MG Oral Tablet", "1000 mg twice daily"),
]
ANTIDIABETICS_INSULIN = [
    ("575145", "Insulin Glargine 100 UNT/ML Injectable Solution", "10 units subcutaneous nightly"),
]

STATINS = [
    ("617312", "Atorvastatin 20 MG Oral Tablet", "20 mg nightly"),
    ("859749", "Rosuvastatin 10 MG Oral Tablet", "10 mg nightly"),
]

LEVOTHYROXINE = [
    ("966247", "Levothyroxine Sodium 0.05 MG Oral Tablet", "50 mcg daily"),
]

SSRIS = [
    ("312940", "Sertraline 50 MG Oral Tablet", "50 mg daily"),
    ("321988", "Escitalopram 10 MG Oral Tablet", "10 mg daily"),
]

ANXIOLYTICS = [
    ("857005", "Buspirone 10 MG Oral Tablet", "10 mg twice daily"),
]

BRONCHODILATORS_SABA = [
    ("329498", "Albuterol 0.09 MG/ACTUAT Metered Dose Inhaler", "2 puffs as needed"),
]
BRONCHODILATORS_LABA = [
    ("637202", "Tiotropium Bromide 0.018 MG Inhalation Capsule", "1 capsule daily"),
]
INHALED_CORTICOSTEROIDS = [
    ("896001", "Fluticasone Propionate 0.11 MG/ACTUAT Metered Dose Inhaler", "2 puffs twice daily"),
]

ANTIPLATELETS = [
    ("243670", "Aspirin 81 MG Oral Tablet", "81 mg daily"),
]

BETA_BLOCKERS = [
    ("866412", "Metoprolol Succinate 50 MG Extended Release Oral Tablet", "50 mg daily"),
]
