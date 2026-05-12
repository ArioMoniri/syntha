"""FHIR R4 resource builders beyond Patient/Observation/Condition.

Encounter, MedicationRequest, CarePlan, and Procedure resources used by the
Synthea-style modules in src/syntha/modules/.
"""
from __future__ import annotations

import uuid
from typing import Iterable


def _now_or(iso: str) -> str:
    return iso


def encounter_resource(
    patient_id: str,
    when_iso: str,
    encounter_class: str = "AMB",
    reason_snomed: tuple[str, str] | None = None,
    type_snomed: tuple[str, str] = ("185349003", "Encounter for check up (procedure)"),
    duration_minutes: int = 30,
) -> dict:
    enc_id = str(uuid.uuid4())
    res = {
        "resourceType": "Encounter",
        "id": enc_id,
        "status": "finished",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": encounter_class,
            "display": {"AMB": "ambulatory", "IMP": "inpatient encounter",
                        "EMER": "emergency"}.get(encounter_class, encounter_class),
        },
        "type": [{
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": type_snomed[0], "display": type_snomed[1],
            }],
            "text": type_snomed[1],
        }],
        "subject": {"reference": f"urn:uuid:{patient_id}"},
        "period": {"start": when_iso, "end": when_iso},
    }
    if reason_snomed is not None:
        res["reasonCode"] = [{
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": reason_snomed[0], "display": reason_snomed[1],
            }],
            "text": reason_snomed[1],
        }]
    return res


def medication_request_resource(
    patient_id: str,
    encounter_id: str | None,
    rxnorm: tuple[str, str, str],
    authored_iso: str,
    reason_snomed: tuple[str, str] | None = None,
) -> dict:
    code, display, dose = rxnorm
    res = {
        "resourceType": "MedicationRequest",
        "id": str(uuid.uuid4()),
        "status": "active",
        "intent": "order",
        "medicationCodeableConcept": {
            "coding": [{
                "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                "code": code, "display": display,
            }],
            "text": display,
        },
        "subject": {"reference": f"urn:uuid:{patient_id}"},
        "authoredOn": authored_iso,
        "dosageInstruction": [{"text": dose}],
    }
    if encounter_id is not None:
        res["encounter"] = {"reference": f"urn:uuid:{encounter_id}"}
    if reason_snomed is not None:
        res["reasonCode"] = [{
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": reason_snomed[0], "display": reason_snomed[1],
            }],
            "text": reason_snomed[1],
        }]
    return res


def procedure_resource(
    patient_id: str,
    encounter_id: str | None,
    when_iso: str,
    snomed: tuple[str, str],
) -> dict:
    code, display = snomed
    res = {
        "resourceType": "Procedure",
        "id": str(uuid.uuid4()),
        "status": "completed",
        "code": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": code, "display": display,
            }],
            "text": display,
        },
        "subject": {"reference": f"urn:uuid:{patient_id}"},
        "performedDateTime": when_iso,
    }
    if encounter_id is not None:
        res["encounter"] = {"reference": f"urn:uuid:{encounter_id}"}
    return res


def careplan_resource(
    patient_id: str,
    title: str,
    activities: Iterable[tuple[str, str]],
    period_start_iso: str,
    addresses_condition_id: str | None = None,
) -> dict:
    """activities: iterable of (snomed_code, display)."""
    activity_entries = [
        {
            "detail": {
                "status": "in-progress",
                "code": {
                    "coding": [{
                        "system": "http://snomed.info/sct",
                        "code": code, "display": display,
                    }],
                    "text": display,
                },
            }
        }
        for code, display in activities
    ]
    res = {
        "resourceType": "CarePlan",
        "id": str(uuid.uuid4()),
        "status": "active",
        "intent": "plan",
        "title": title,
        "subject": {"reference": f"urn:uuid:{patient_id}"},
        "period": {"start": period_start_iso},
        "activity": activity_entries,
    }
    if addresses_condition_id is not None:
        res["addresses"] = [{"reference": f"urn:uuid:{addresses_condition_id}"}]
    return res
