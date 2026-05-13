import pandas as pd

from syntha.generator.constraints import ConstraintConfig, PhysiologicConstraints


def test_systolic_diastolic_rejection():
    df = pd.DataFrame({
        "bp_systolic":  [120, 110,  80, 160],
        "bp_diastolic": [ 80,  70, 100,  90],
    })
    pc = PhysiologicConstraints(ConstraintConfig())
    kept, stats = pc.apply(df)
    # Row 2 is invalid (systolic < diastolic).
    assert stats["rows_kept"] == 3
    assert (kept["bp_systolic"] >= kept["bp_diastolic"] + 20).all()


def test_friedewald_filter():
    df = pd.DataFrame({
        "cholesterol_total_latest": [200, 200],
        "hdl_latest":                [ 50,  50],
        "ldl_direct_latest":         [120, 350],   # row 2 is impossible
        "triglycerides_latest":      [150, 150],
    })
    pc = PhysiologicConstraints(ConstraintConfig(
        enforce_systolic_gt_diastolic=False, enforce_egfr_creatinine=False
    ))
    _, stats = pc.apply(df)
    assert stats["rows_dropped"] == 1


def test_egfr_creatinine_filter():
    df = pd.DataFrame({
        "egfr_latest":      [ 95, 100,  35],
        "creatinine_latest": [0.9, 2.5, 2.0],   # row 2 contradicts itself
    })
    pc = PhysiologicConstraints(ConstraintConfig(
        enforce_systolic_gt_diastolic=False, enforce_cholesterol_friedewald=False
    ))
    _, stats = pc.apply(df)
    assert stats["rows_dropped"] == 1


def test_repair_clips_to_bounds():
    df = pd.DataFrame({"bp_systolic": [400, 50, 130]})
    pc = PhysiologicConstraints()
    out = pc.repair(df)
    assert out["bp_systolic"].max() <= 250
    assert out["bp_systolic"].min() >= 70
