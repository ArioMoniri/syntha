"""MCP server smoke tests — verify tool registration + end-to-end invocation.

These tests run only when the optional ``mcp`` extra is installed
(``pip install -e ".[mcp]"``).
"""
from __future__ import annotations

import asyncio
import json

import pytest

mcp = pytest.importorskip("mcp", reason="syntha-mcp requires `pip install 'syntha-ehr[mcp]'`")

from syntha.mcp_server import _app, _load_bundled


def _unwrap(res):
    """FastMCP returns ``list[Content]``. Pull the JSON payload from the first item."""
    assert isinstance(res, list) and res, f"expected non-empty list, got {res!r}"
    text = getattr(res[0], "text", None)
    assert text, f"expected TextContent, got {res[0]!r}"
    return json.loads(text)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if asyncio.get_event_loop().is_running() else asyncio.run(coro)


def test_tool_inventory():
    tools = asyncio.run(_app.list_tools())
    names = {t.name for t in tools}
    expected = {
        "syntha_version",
        "list_bundled_cohorts",
        "get_cohort_summary",
        "generate_cohort_csv",
        "generate_cohort_fhir",
        "sample_conditional",
        "list_clinical_modules",
        "list_physiologic_constraints",
    }
    assert expected.issubset(names), f"missing: {expected - names}"


def test_bundled_models_loadable():
    for name in ("tolerant", "strict"):
        gen = _load_bundled(name)
        assert gen.model is not None
        assert gen.model.n_train > 0
        # Smoke-sample to confirm the loaded model can actually draw
        df = gen.sample(5)
        assert len(df) == 5
        assert len(df.columns) == len(gen.model.columns)


def test_syntha_version():
    payload = _unwrap(asyncio.run(_app.call_tool("syntha_version", {})))
    assert "syntha_version" in payload
    assert payload["license"] == "Apache-2.0"
    assert "tolerant" in payload["bundled_cohorts"]


def test_list_bundled_cohorts():
    payload = _unwrap(asyncio.run(_app.call_tool("list_bundled_cohorts", {})))
    assert set(payload) == {"tolerant", "strict"}
    assert payload["tolerant"]["n_train"] > 100_000
    assert payload["strict"]["n_train"] > 50_000


def test_get_cohort_summary_tolerant_has_real_prevalences():
    payload = _unwrap(asyncio.run(_app.call_tool("get_cohort_summary", {"cohort": "tolerant"})))
    cp = payload["comorbidity_prevalence_percent"]
    # Tolerant must have non-trivial comorbidity prevalence — these are
    # the floor figures from the actual model card; if the bundled JSON
    # changes drastically, this test will catch it.
    assert cp["Hipertansiyon"] > 5.0
    assert cp["DM_Tum"] > 2.0
    assert cp["Tiroid"] > 10.0


def test_generate_cohort_csv_default_drops_curation_flags():
    payload = _unwrap(asyncio.run(_app.call_tool("generate_cohort_csv", {
        "n": 20, "cohort": "tolerant", "seed": 42,
    })))
    assert payload["n_rows"] == 20
    # Curation flags should be absent by default
    cols = set(payload["columns"])
    assert "pristine_strict" not in cols
    assert "berturk_similarity" not in cols
    assert "rf_kanser" not in cols
    # Clinical columns should be present
    assert "age" in cols
    assert "Hipertansiyon" in cols
    assert "bp_systolic" in cols


def test_generate_cohort_csv_opt_in_curation():
    payload = _unwrap(asyncio.run(_app.call_tool("generate_cohort_csv", {
        "n": 10, "cohort": "tolerant", "seed": 42,
        "include_curation_flags": True,
    })))
    cols = set(payload["columns"])
    assert "pristine_strict" in cols  # opt-in: now present


def test_generate_cohort_csv_respects_max_rows():
    payload = _unwrap(asyncio.run(_app.call_tool("generate_cohort_csv", {
        "n": 999_999_999, "cohort": "tolerant",
        "max_rows": 12,
    })))
    assert payload["n_rows"] <= 12


def test_generate_cohort_fhir_returns_valid_bundles():
    payload = _unwrap(asyncio.run(_app.call_tool("generate_cohort_fhir", {
        "n": 3, "cohort": "tolerant", "seed": 7,
    })))
    assert payload["n_bundles"] == 3
    lines = payload["fhir_ndjson"].splitlines()
    assert len(lines) == 3
    for line in lines:
        bundle = json.loads(line)
        assert bundle["resourceType"] == "Bundle"
        types = [e["resource"]["resourceType"] for e in bundle["entry"]]
        assert "Patient" in types


def test_sample_conditional_simple_condition():
    """Hipertansiyon == 1 has ≈ 7.5% prevalence — should reach n=5 in a few rounds."""
    payload = _unwrap(asyncio.run(_app.call_tool("sample_conditional", {
        "condition": "Hipertansiyon == 1",
        "n": 5, "cohort": "tolerant", "seed": 42,
        "oversample_factor": 20.0, "max_rounds": 5,
    })))
    assert payload["n_generated"] == 5
    # Every returned row must satisfy the condition
    import io
    import pandas as pd
    df = pd.read_csv(io.StringIO(payload["csv"]))
    assert (df["Hipertansiyon"] == 1).all()


def test_list_clinical_modules_has_nine():
    payload = _unwrap(asyncio.run(_app.call_tool("list_clinical_modules", {})))
    assert len(payload["modules"]) == 9
    names = {m["name"] for m in payload["modules"]}
    assert "Hypertension" in names
    assert "Diabetes" in names


def test_list_physiologic_constraints():
    payload = _unwrap(asyncio.run(_app.call_tool("list_physiologic_constraints", {})))
    assert len(payload["constraints"]) >= 3
