import json

import pandas as pd

from syntha.fhir.export import episode_to_bundle, write_fhir_bundles


def _row():
    return pd.Series({
        "RF_EPISODE2": 123, "HASTA_ID": "SYN_X", "episode_date": "2024-06-01",
        "age": 55, "gender_is_male": 1,
        "glucose_fasting_latest": 95.0, "hdl_latest": 50.0,
        "ldl_direct_latest": 120.0, "cholesterol_total_latest": 200.0,
        "triglycerides_latest": 150.0, "bp_systolic": 130.0, "bp_diastolic": 85.0,
        "Hipertansiyon": 1, "DM_Tum": 0,
    })


def test_bundle_has_patient_and_observations():
    bundle = episode_to_bundle(_row())
    assert bundle["resourceType"] == "Bundle"
    types = [e["resource"]["resourceType"] for e in bundle["entry"]]
    assert types.count("Patient") == 1
    assert types.count("Observation") >= 5
    # Hypertension flag is 1 → one Condition; DM flag is 0 → no DM Condition
    conds = [e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Condition"]
    assert len(conds) == 1
    assert "Hypertensive" in conds[0]["code"]["text"]


def test_loinc_codes_present():
    bundle = episode_to_bundle(_row())
    obs = [e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Observation"]
    codes = {o["code"]["coding"][0]["code"] for o in obs}
    assert "8480-6" in codes  # systolic BP LOINC
    assert "2085-9" in codes  # HDL LOINC


def test_ndjson_writer(tmp_path):
    df = pd.DataFrame([_row(), _row()])
    out = write_fhir_bundles(df, tmp_path, fmt="ndjson")
    assert out.exists()
    with open(out) as f:
        lines = f.readlines()
    assert len(lines) == 2
    for line in lines:
        assert json.loads(line)["resourceType"] == "Bundle"


def test_missing_lab_skipped():
    row = _row()
    row["hdl_latest"] = float("nan")
    bundle = episode_to_bundle(row)
    obs = [e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Observation"]
    codes = {o["code"]["coding"][0]["code"] for o in obs}
    assert "2085-9" not in codes  # HDL was NaN → no observation emitted
