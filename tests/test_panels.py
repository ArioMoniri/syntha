"""Test lab-panel DiagnosticReport grouping."""
import pandas as pd

from syntha.fhir.export import episode_to_bundle


def _row(**overrides):
    base = {
        "RF_EPISODE2": 1, "HASTA_ID": "SYN_A", "episode_date": "2024-06-01",
        "age": 55, "gender_is_male": 1,
        "bp_systolic": 130.0, "bp_diastolic": 85.0,
        "glucose_fasting_latest": 95.0, "creatinine_latest": 1.0, "egfr_latest": 90.0,
        "alt_latest": 25.0, "ast_latest": 22.0,
        "hemoglobin_latest": 14.5, "wbc_latest": 6.5, "platelets_latest": 230,
        "hdl_latest": 50.0, "ldl_direct_latest": 120.0,
        "cholesterol_total_latest": 200.0, "triglycerides_latest": 150.0,
    }
    base.update(overrides)
    return pd.Series(base)


def test_panel_reports_emitted_when_constituents_present():
    bundle = episode_to_bundle(_row(), run_modules=False)
    reports = [e["resource"] for e in bundle["entry"]
               if e["resource"]["resourceType"] == "DiagnosticReport"]
    codes = {r["code"]["coding"][0]["code"] for r in reports}
    # We populated lipid, CBC, CMP, and BP — all four panels should exist.
    assert "57698-3" in codes, "lipid panel missing"
    assert "58410-2" in codes, "CBC panel missing"
    assert "24323-8" in codes, "CMP panel missing"
    assert "85354-9" in codes, "BP panel missing"


def test_panel_references_observations_correctly():
    bundle = episode_to_bundle(_row(), run_modules=False)
    obs_by_id = {e["resource"]["id"]: e["resource"]
                 for e in bundle["entry"]
                 if e["resource"]["resourceType"] == "Observation"}
    lipid = next(e["resource"] for e in bundle["entry"]
                 if e["resource"]["resourceType"] == "DiagnosticReport"
                 and e["resource"]["code"]["coding"][0]["code"] == "57698-3")
    # Lipid panel should reference 4 observations (chol, HDL, LDL, TG)
    refs = [r["reference"].replace("urn:uuid:", "") for r in lipid["result"]]
    assert len(refs) == 4
    # Each reference resolves to a real Observation in the bundle.
    for ref in refs:
        assert ref in obs_by_id


def test_no_panel_when_constituents_missing():
    """If we strip the lipid columns, no lipid panel should be emitted."""
    row = _row(cholesterol_total_latest=None, hdl_latest=None,
               ldl_direct_latest=None, triglycerides_latest=None)
    bundle = episode_to_bundle(row, run_modules=False)
    codes = {e["resource"]["code"]["coding"][0]["code"]
             for e in bundle["entry"]
             if e["resource"]["resourceType"] == "DiagnosticReport"}
    assert "57698-3" not in codes


def test_synthetic_marker_present_on_patient():
    """G1: every emitted Patient carries the HTEST synthetic-data marker."""
    bundle = episode_to_bundle(_row(), run_modules=False)
    patient = next(e["resource"] for e in bundle["entry"]
                   if e["resource"]["resourceType"] == "Patient")
    tags = patient["meta"]["tag"]
    codes = {t["code"] for t in tags}
    assert "HTEST" in codes, "FHIR synthetic-data marker (HTEST) missing"
    assert "syntha-copula" in codes, "syntha source marker missing"
