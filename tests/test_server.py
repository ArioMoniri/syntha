import json
import threading
import time
import urllib.request
from pathlib import Path

import pandas as pd
import pytest

from syntha.fhir.export import write_fhir_bundles
from syntha.server import serve

PORT = 18642


def _build_ndjson(tmp_path: Path) -> Path:
    df = pd.DataFrame([{
        "RF_EPISODE2": 1, "HASTA_ID": "SYN_TEST", "episode_date": "2024-06-01",
        "age": 55, "gender_is_male": 1,
        "bp_systolic": 130.0, "bp_diastolic": 85.0,
        "hdl_latest": 50.0, "ldl_direct_latest": 120.0,
        "Hipertansiyon": 1,
    }])
    write_fhir_bundles(df, tmp_path, fmt="ndjson")
    return tmp_path / "bundles.ndjson"


@pytest.fixture
def server(tmp_path):
    ndjson = _build_ndjson(tmp_path)
    srv = serve(ndjson, host="127.0.0.1", port=PORT)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)
    yield f"http://127.0.0.1:{PORT}"
    srv.shutdown()


def _get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=2) as r:
        return json.loads(r.read())


def test_metadata_returns_capability_statement(server):
    cap = _get(f"{server}/metadata")
    assert cap["resourceType"] == "CapabilityStatement"
    assert cap["fhirVersion"] == "4.0.1"
    types = {r["type"] for r in cap["rest"][0]["resource"]}
    assert {"Patient", "Observation", "Condition", "MedicationRequest"} <= types


def test_search_patient_returns_searchset(server):
    bundle = _get(f"{server}/Patient")
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "searchset"
    assert bundle["total"] == 1
    assert bundle["entry"][0]["resource"]["resourceType"] == "Patient"


def test_read_observation_by_id(server):
    obs_bundle = _get(f"{server}/Observation")
    assert obs_bundle["total"] >= 1
    obs_id = obs_bundle["entry"][0]["resource"]["id"]
    single = _get(f"{server}/Observation/{obs_id}")
    assert single["resourceType"] == "Observation"
    assert single["id"] == obs_id


def test_unknown_resource_returns_operation_outcome(server):
    try:
        urllib.request.urlopen(f"{server}/Foobar", timeout=2)
        assert False, "should have raised"
    except urllib.error.HTTPError as e:
        body = json.loads(e.read())
        assert body["resourceType"] == "OperationOutcome"
        assert body["issue"][0]["severity"] == "error"
