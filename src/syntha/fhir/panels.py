"""FHIR DiagnosticReport panel grouping.

Real EHR consumers (HAPI, OMOP ETL, Aidbox) expect ordered-together labs
to be grouped under a DiagnosticReport pointing at its constituent
Observations, not emitted as bare Observations. This module defines the
common ambulatory panels and an emitter that wraps a set of already-
emitted Observation resources into a DiagnosticReport.

Panel definitions follow LOINC's PanelHierarchy ontology.
"""
from __future__ import annotations

import uuid

# (panel-LOINC, display, constituent-columns).
# The "constituent-columns" list must reference the columns in the
# source/synthetic data; the emitter only groups observations whose
# column key appears here.
PANELS: list[tuple[str, str, list[str]]] = [
    ("57698-3", "Lipid panel with direct LDL — Serum or Plasma",
     ["cholesterol_total_latest", "hdl_latest", "ldl_direct_latest", "triglycerides_latest"]),
    ("58410-2", "Complete blood count (hemogram) panel — Blood by Automated count",
     ["hemoglobin_latest", "wbc_latest", "platelets_latest"]),
    ("24323-8", "Comprehensive metabolic panel — Serum or Plasma",
     ["glucose_fasting_latest", "creatinine_latest", "egfr_latest", "alt_latest", "ast_latest"]),
    ("24350-1", "Iron and binding capacity — Serum or Plasma",
     ["ferritin_latest"]),
    ("85354-9", "Blood pressure panel with all children optional",
     ["bp_systolic", "bp_diastolic"]),
]


def _observation_index(resources: list[dict]) -> dict[str, dict]:
    """Map LOINC code → Observation resource for grouping lookup."""
    idx: dict[str, dict] = {}
    for r in resources:
        if r.get("resourceType") != "Observation":
            continue
        try:
            code = r["code"]["coding"][0]["code"]
            idx[code] = r
        except (KeyError, IndexError):
            continue
    return idx


def diagnostic_reports_for(
    resources: list[dict],
    patient_id: str,
    effective_iso: str,
    lab_loinc: dict[str, tuple[str, str, str]],
) -> list[dict]:
    """Build DiagnosticReport resources grouping the existing Observations.

    Parameters
    ----------
    resources:
        Already-emitted Observation resources (will be referenced, not modified).
    patient_id:
        Patient UUID — used as the `subject.reference`.
    effective_iso:
        ISO 8601 timestamp shared by all observations in this episode.
    lab_loinc:
        The LAB_LOINC table mapping source-column → (loinc, display, unit).

    Returns
    -------
    A list of DiagnosticReport resources. Empty if no panel has any
    observed constituents.
    """
    by_loinc = _observation_index(resources)
    reports: list[dict] = []

    for panel_code, panel_display, columns in PANELS:
        # Resolve constituent Observations via the panel's source columns.
        constituent_obs = []
        for col in columns:
            if col not in lab_loinc:
                continue
            loinc_code, _display, _unit = lab_loinc[col]
            obs = by_loinc.get(loinc_code)
            if obs is not None:
                constituent_obs.append(obs)
        if not constituent_obs:
            continue

        reports.append({
            "resourceType": "DiagnosticReport",
            "id": str(uuid.uuid4()),
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                    "code": "LAB",
                    "display": "Laboratory",
                }],
            }],
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": panel_code,
                    "display": panel_display,
                }],
                "text": panel_display,
            },
            "subject": {"reference": f"urn:uuid:{patient_id}"},
            "effectiveDateTime": effective_iso,
            "issued": effective_iso,
            "result": [
                {"reference": f"urn:uuid:{obs['id']}"} for obs in constituent_obs
            ],
        })

    return reports
