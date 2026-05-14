"""Tests for clinical_extras: RiskAssessment, PHQ-9, GAD-7, FamilyMemberHistory."""
import numpy as np
import pandas as pd

from syntha.fhir.clinical_extras import (
    _charlson_to_probability,
    _qualitative_charlson,
    charlson_risk_assessment,
    family_history_resources,
    gad7_observation,
    phq9_observation,
)


def test_charlson_score_to_qualitative_categories():
    assert _qualitative_charlson(0) == "negligible"
    assert _qualitative_charlson(1) == "low"
    assert _qualitative_charlson(3) == "moderate"
    assert _qualitative_charlson(6) == "high"


def test_charlson_score_to_probability_monotonic():
    """Higher CCI → higher mortality probability."""
    probs = [_charlson_to_probability(s) for s in range(0, 11)]
    assert probs == sorted(probs)
    assert 0.0 <= probs[0] <= probs[-1] <= 1.0


def test_risk_assessment_resource_structure():
    r = charlson_risk_assessment("test-uuid", 4.0, "2024-06-01T12:00:00Z")
    assert r["resourceType"] == "RiskAssessment"
    assert r["subject"]["reference"] == "urn:uuid:test-uuid"
    assert r["method"]["coding"][0]["code"] == "75618-7"
    assert r["prediction"][0]["qualitativeRisk"]["coding"][0]["code"] == "moderate"


def test_phq9_emitted_only_when_depression_flag_set():
    rng = np.random.default_rng(0)
    assert phq9_observation("u", 0, "2024-01-01T00:00:00Z", rng) is None
    obs = phq9_observation("u", 1, "2024-01-01T00:00:00Z", rng)
    assert obs is not None
    assert obs["code"]["coding"][0]["code"] == "44261-6"
    # Score in valid clinical range
    score = obs["valueQuantity"]["value"]
    assert 4 <= score <= 22


def test_gad7_emitted_only_when_anxiety_flag_set():
    rng = np.random.default_rng(1)
    assert gad7_observation("u", 0, "2024-01-01T00:00:00Z", rng) is None
    obs = gad7_observation("u", 1, "2024-01-01T00:00:00Z", rng)
    assert obs is not None
    assert obs["code"]["coding"][0]["code"] == "70274-6"


def test_family_history_emitted_for_set_rf_flags():
    row = pd.Series({"rf_kanser": 1, "rf_kronik_hastalik": 0})
    res = family_history_resources("u", row, "2024-01-01T00:00:00Z")
    assert len(res) == 1
    assert res[0]["resourceType"] == "FamilyMemberHistory"
    assert res[0]["condition"][0]["code"]["coding"][0]["code"] == "363346000"


def test_phq9_interpretation_flag():
    """PHQ-9 ≥ 10 should be marked 'Abnormal'."""
    rng = np.random.default_rng(99)
    found_normal = found_abnormal = False
    for _ in range(50):
        obs = phq9_observation("u", 1, "2024-01-01", rng)
        if obs is None:
            continue
        score = obs["valueQuantity"]["value"]
        interp = obs["interpretation"][0]["coding"][0]["code"]
        if score < 10:
            assert interp == "N"
            found_normal = True
        else:
            assert interp == "A"
            found_abnormal = True
    # Both branches exercised across 50 draws
    assert found_normal and found_abnormal
