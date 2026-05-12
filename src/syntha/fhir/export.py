"""FHIR R4 Bundle writer for synthetic episodes."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import pandas as pd

from .codes import CONDITION_SNOMED, GENDER_MAP, LAB_LOINC


def _is_present(v) -> bool:
    if v is None:
        return False
    try:
        return not bool(pd.isna(v))
    except (TypeError, ValueError):
        return True


def _patient_resource(row: pd.Series, patient_id: str) -> dict:
    age = int(row.get("age")) if _is_present(row.get("age")) else None
    gender = GENDER_MAP.get(int(row.get("gender_is_male", 0)), "unknown") if _is_present(row.get("gender_is_male")) else "unknown"
    # Approximate birthDate from episode_date − age years. Falls back to today.
    episode_dt = pd.to_datetime(row.get("episode_date"), errors="coerce")
    if pd.isna(episode_dt):
        episode_dt = pd.Timestamp.utcnow()
    birth = (episode_dt - pd.DateOffset(years=age)) if age is not None else None
    res = {
        "resourceType": "Patient",
        "id": patient_id,
        "gender": gender,
        "extension": [
            {
                "url": "http://hl7.org/fhir/StructureDefinition/patient-birthPlace",
                "valueAddress": {"country": "TR"},
            }
        ],
        "meta": {"profile": ["http://hl7.org/fhir/StructureDefinition/Patient"]},
    }
    if birth is not None:
        res["birthDate"] = birth.strftime("%Y-%m-%d")
    return res


def _observation_resource(
    row: pd.Series, patient_id: str, column: str, effective_iso: str
) -> dict | None:
    value = row.get(column)
    if not _is_present(value):
        return None
    code, display, unit = LAB_LOINC[column]
    is_vital = column in {"bp_systolic", "bp_diastolic"}
    category = "vital-signs" if is_vital else "laboratory"
    return {
        "resourceType": "Observation",
        "id": str(uuid.uuid4()),
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": category,
                        "display": category.replace("-", " ").title(),
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {"system": "http://loinc.org", "code": code, "display": display}
            ],
            "text": display,
        },
        "subject": {"reference": f"urn:uuid:{patient_id}"},
        "effectiveDateTime": effective_iso,
        "valueQuantity": {
            "value": float(value),
            "unit": unit,
            "system": "http://unitsofmeasure.org",
            "code": unit,
        },
    }


def _condition_resource(
    patient_id: str, column: str, onset_iso: str
) -> dict:
    code, display = CONDITION_SNOMED[column]
    return {
        "resourceType": "Condition",
        "id": str(uuid.uuid4()),
        "clinicalStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": "active",
                }
            ]
        },
        "verificationStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                    "code": "confirmed",
                }
            ]
        },
        "code": {
            "coding": [
                {"system": "http://snomed.info/sct", "code": code, "display": display}
            ],
            "text": display,
        },
        "subject": {"reference": f"urn:uuid:{patient_id}"},
        "onsetDateTime": onset_iso,
    }


def episode_to_bundle(row: pd.Series) -> dict:
    patient_id = str(uuid.uuid4())
    episode_dt = pd.to_datetime(row.get("episode_date"), errors="coerce")
    if pd.isna(episode_dt):
        episode_dt = pd.Timestamp.utcnow()
    effective_iso = episode_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    entries = [
        {
            "fullUrl": f"urn:uuid:{patient_id}",
            "resource": _patient_resource(row, patient_id),
            "request": {"method": "POST", "url": "Patient"},
        }
    ]
    for col in LAB_LOINC:
        if col in row.index:
            obs = _observation_resource(row, patient_id, col, effective_iso)
            if obs is not None:
                entries.append(
                    {
                        "fullUrl": f"urn:uuid:{obs['id']}",
                        "resource": obs,
                        "request": {"method": "POST", "url": "Observation"},
                    }
                )
    for col in CONDITION_SNOMED:
        if col in row.index and _is_present(row.get(col)) and int(row.get(col)) == 1:
            cond = _condition_resource(patient_id, col, effective_iso)
            entries.append(
                {
                    "fullUrl": f"urn:uuid:{cond['id']}",
                    "resource": cond,
                    "request": {"method": "POST", "url": "Condition"},
                }
            )

    return {
        "resourceType": "Bundle",
        "id": str(uuid.uuid4()),
        "type": "transaction",
        "timestamp": effective_iso,
        "entry": entries,
    }


def write_fhir_bundles(
    df: pd.DataFrame,
    out_dir: str | Path,
    fmt: str = "ndjson",
) -> Path:
    """Write one Bundle per row.

    fmt='ndjson' → single newline-delimited JSON file (Synthea bulk style).
    fmt='json'   → one pretty-printed JSON file per bundle in a directory.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if fmt == "ndjson":
        target = out / "bundles.ndjson"
        with open(target, "w", encoding="utf-8") as f:
            for _, row in df.iterrows():
                f.write(json.dumps(episode_to_bundle(row), ensure_ascii=False))
                f.write("\n")
        return target
    bundles_dir = out / "bundles"
    bundles_dir.mkdir(parents=True, exist_ok=True)
    for i, (_, row) in enumerate(df.iterrows()):
        bundle = episode_to_bundle(row)
        with open(bundles_dir / f"patient_{i:06d}.json", "w", encoding="utf-8") as f:
            json.dump(bundle, f, ensure_ascii=False, indent=2)
    return bundles_dir
