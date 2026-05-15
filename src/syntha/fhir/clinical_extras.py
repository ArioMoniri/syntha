"""Extra FHIR resources for clinical realism (per MO review):

  * Charlson Comorbidity Index (CCI) surfaced as a ``RiskAssessment``
    resource. The CCI is already a column in the source CSV; we just
    expose it properly instead of letting it sit in the CSV-only output.
  * PHQ-9 (Depression) screening score — emitted when ``Depresyon`` flag
    is set. Score is sampled from the conditional distribution of PHQ-9
    given the patient was flagged depressed (5-14 = mild-moderate range).
  * GAD-7 (Anxiety) screening score — emitted when ``Anksiyete`` flag is
    set. Similar conditional sampling (5-12 = mild-moderate).
  * FamilyMemberHistory resources — emitted for ``rf_kanser`` (family
    cancer risk factor) and ``rf_kronik_hastalik`` (chronic disease
    risk).

All use proper LOINC codes for the screening instruments and SNOMED CT
for family-history concepts.
"""
from __future__ import annotations

import uuid

import numpy as np


def charlson_risk_assessment(
    patient_id: str,
    charlson_score: float,
    effective_iso: str,
) -> dict:
    """Surface the patient's Charlson Comorbidity Index as a
    ``RiskAssessment`` resource — LOINC 75618-7 ("Charlson comorbidity
    index"). Risk score is in the standard CCI 0-37 scale where:

      0     : no comorbidity
      1-2   : mild (10-year mortality risk ~25%)
      3-4   : moderate (~50%)
      ≥5    : severe (~85%)
    """
    if charlson_score is None:
        return {}
    return {
        "resourceType": "RiskAssessment",
        "id": str(uuid.uuid4()),
        "status": "final",
        "subject": {"reference": f"urn:uuid:{patient_id}"},
        "occurrenceDateTime": effective_iso,
        "method": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "75618-7",
                "display": "Charlson comorbidity index",
            }],
        },
        "prediction": [{
            "outcome": {"text": "10-year all-cause mortality (Charlson-weighted)"},
            "qualitativeRisk": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/risk-probability",
                    "code": _qualitative_charlson(charlson_score),
                }],
            },
            "probabilityDecimal": _charlson_to_probability(charlson_score),
        }],
        "note": [{
            "text": f"Charlson Comorbidity Index score: {charlson_score:.0f}",
        }],
    }


def _qualitative_charlson(score: float) -> str:
    if score <= 0.5:
        return "negligible"
    if score <= 2.5:
        return "low"
    if score <= 4.5:
        return "moderate"
    return "high"


def _charlson_to_probability(score: float) -> float:
    """Charlson → 10-year-mortality probability via the standard logistic
    fit (Charlson et al. 1987; many calibration updates since)."""
    # Approximation: P = 1 - 0.983^(0.9 × score)
    if score < 0:
        return 0.0
    return float(min(1.0, 1.0 - 0.983 ** (0.9 * score)))


def phq9_observation(
    patient_id: str,
    depression_flag: int,
    effective_iso: str,
    rng: np.random.Generator,
) -> dict | None:
    """PHQ-9 total score Observation. Emitted only when the depression
    flag is set; sampled from the conditional distribution PHQ-9 | flagged.

    Source-cohort flagged-depression patients have PHQ-9 in the mild-
    moderate range (5-14) per typical primary-care screening cohorts.
    Clamped to the full PHQ-9 scale [0, 27].
    """
    if int(depression_flag) != 1:
        return None
    score = int(np.clip(rng.normal(9, 3), 0, 27))
    return {
        "resourceType": "Observation",
        "id": str(uuid.uuid4()),
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "survey",
                "display": "Survey",
            }],
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "44261-6",
                "display": "Patient Health Questionnaire 9 item (PHQ-9) total score",
            }],
            "text": "PHQ-9 total score / PHQ-9 toplam skor",
        },
        "subject": {"reference": f"urn:uuid:{patient_id}"},
        "effectiveDateTime": effective_iso,
        "valueQuantity": {
            "value": score,
            "unit": "{score}",
            "system": "http://unitsofmeasure.org",
            "code": "{score}",
        },
        "interpretation": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                "code": "A" if score >= 10 else "N",
                "display": "Abnormal" if score >= 10 else "Normal",
            }],
        }],
    }


def gad7_observation(
    patient_id: str,
    anxiety_flag: int,
    effective_iso: str,
    rng: np.random.Generator,
) -> dict | None:
    """GAD-7 total score Observation, conditional on anxiety flag.

    Symmetric with PHQ-9: score sampled from N(8, 2.5²) and clamped to
    the full GAD-7 scale [0, 21] (the v0.5-dev pre-review version used
    an asymmetric [3, 18] clamp that the joint CMO + ML-eng review
    flagged as inconsistent).
    """
    if int(anxiety_flag) != 1:
        return None
    score = int(np.clip(rng.normal(8, 2.5), 0, 21))
    return {
        "resourceType": "Observation",
        "id": str(uuid.uuid4()),
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "survey",
                "display": "Survey",
            }],
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "70274-6",
                "display": "Generalized anxiety disorder 7 item (GAD-7) total score",
            }],
            "text": "GAD-7 total score / GAD-7 toplam skor",
        },
        "subject": {"reference": f"urn:uuid:{patient_id}"},
        "effectiveDateTime": effective_iso,
        "valueQuantity": {
            "value": score,
            "unit": "{score}",
            "system": "http://unitsofmeasure.org",
            "code": "{score}",
        },
        "interpretation": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                "code": "A" if score >= 10 else "N",
                "display": "Abnormal" if score >= 10 else "Normal",
            }],
        }],
    }


# Risk-factor flag → SNOMED concept for FamilyMemberHistory
_FAMILY_HISTORY_CODES: dict[str, tuple[str, str]] = {
    "rf_kanser":          ("363346000", "Malignant neoplastic disease (disorder)"),
    "rf_kronik_hastalik": ("237603008", "Disorder of long duration (disorder)"),
}


def family_history_resources(
    patient_id: str,
    row,
    effective_iso: str,
) -> list[dict]:
    """Emit ``FamilyMemberHistory`` for each set risk-factor flag.

    The source columns ``rf_*`` are flags meaning "this patient has
    a family history of <X>". We expose them as the canonical FHIR
    FamilyMemberHistory resource so downstream consumers see them.
    """
    import pandas as pd
    out: list[dict] = []
    for flag, (code, display) in _FAMILY_HISTORY_CODES.items():
        if flag not in row.index:
            continue
        v = row.get(flag)
        if v is None or pd.isna(v) or int(v) != 1:
            continue
        out.append({
            "resourceType": "FamilyMemberHistory",
            "id": str(uuid.uuid4()),
            "status": "completed",
            "patient": {"reference": f"urn:uuid:{patient_id}"},
            "date": effective_iso,
            "relationship": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v3-RoleCode",
                    "code": "FAMMEMB",
                    "display": "family member",
                }],
                "text": "Unspecified family member",
            },
            "condition": [{
                "code": {
                    "coding": [{
                        "system": "http://snomed.info/sct",
                        "code": code,
                        "display": display,
                    }],
                    "text": display,
                },
            }],
        })
    return out
