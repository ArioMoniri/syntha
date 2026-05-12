import pandas as pd

from syntha.fhir.export import episode_to_bundle
from syntha.modules import REGISTRY
from syntha.modules.base import ModuleContext


def _row(**overrides):
    base = {
        "RF_EPISODE2": 1, "HASTA_ID": "SYN_A", "episode_date": "2024-06-01",
        "age": 55, "gender_is_male": 1,
        "bp_systolic": 165.0, "bp_diastolic": 95.0,
        "glucose_fasting_latest": 180.0, "ldl_direct_latest": 210.0,
        "hdl_latest": 35.0, "cholesterol_total_latest": 280.0,
        "triglycerides_latest": 175.0,
        "Hipertansiyon": 1, "DM_Tum": 1, "Hiperlipidemi": 1,
        "Tiroid": 0, "Depresyon": 0, "Anksiyete": 0,
        "Iskemik_Kalp": 0, "Astim": 0, "COPD": 0,
    }
    base.update(overrides)
    return pd.Series(base)


def test_registered_modules_unique_names():
    names = [m.name for m in REGISTRY]
    assert len(names) == len(set(names))


def test_hypertension_fires_with_dual_therapy_at_stage2():
    bundle = episode_to_bundle(_row())
    meds = [e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "MedicationRequest"]
    htn_meds = [m for m in meds if any(
        "Hypertensive" in (rc.get("text") or "") for rc in (m.get("reasonCode") or [])
    )]
    assert len(htn_meds) == 2  # stage-2 systolic → dual therapy


def test_diabetes_emits_hba1c_and_metformin():
    bundle = episode_to_bundle(_row())
    types = [e["resource"]["resourceType"] for e in bundle["entry"]]
    assert "Procedure" in types
    procs = [e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Procedure"]
    assert any(p["code"]["coding"][0]["code"] == "313835008" for p in procs)
    meds = [e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "MedicationRequest"]
    assert any("Metformin" in m["medicationCodeableConcept"]["text"] for m in meds)


def test_no_modules_when_flag_zero():
    row = _row(Hipertansiyon=0, DM_Tum=0, Hiperlipidemi=0)
    bundle = episode_to_bundle(row)
    types = [e["resource"]["resourceType"] for e in bundle["entry"]]
    assert "MedicationRequest" not in types
    assert "Encounter" not in types


def test_modules_can_be_disabled():
    bundle = episode_to_bundle(_row(), run_modules=False)
    types = [e["resource"]["resourceType"] for e in bundle["entry"]]
    assert "MedicationRequest" not in types
    # Conditions and Observations are still emitted (those are direct-mapped).
    assert "Condition" in types
    assert "Observation" in types


def test_anxiety_with_concurrent_depression_uses_buspirone():
    row = _row(Anksiyete=1, Depresyon=1, Hipertansiyon=0, DM_Tum=0, Hiperlipidemi=0)
    bundle = episode_to_bundle(row)
    meds = [e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "MedicationRequest"]
    texts = [m["medicationCodeableConcept"]["text"] for m in meds]
    # Sertraline (depression) + Buspirone (anxiety, because already on SSRI).
    assert any("Sertraline" in t for t in texts)
    assert any("Buspirone" in t for t in texts)
