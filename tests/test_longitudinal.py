import numpy as np
import pandas as pd

from syntha.longitudinal import TrajectoryConfig, expand_to_trajectories


def _baselines(n=10, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "HASTA_ID": [f"B{i:03d}" for i in range(n)],
        "RF_EPISODE2": np.arange(n),
        "episode_date": pd.Timestamp("2020-01-01"),
        "age": rng.integers(30, 70, n),
        "gender_is_male": rng.binomial(1, 0.5, n),
        "bp_systolic": rng.normal(120, 10, n),
        "bp_diastolic": rng.normal(75, 5, n),
        "Hipertansiyon": rng.binomial(1, 0.2, n),
    })


def test_trajectory_expands_each_baseline():
    base = _baselines(n=8)
    out = expand_to_trajectories(
        base, pd.Timestamp("2018-01-01"), pd.Timestamp("2024-12-31"),
        TrajectoryConfig(encounters_per_patient_mean=3.0, random_seed=1),
    )
    # Each baseline yields ≥1 row; the generator assigns a fresh patient ID
    # per baseline, so unique patient count equals the baseline count.
    assert len(out) >= len(base)
    assert out["HASTA_ID"].nunique() == len(base)


def test_sticky_comorbidity_flag():
    base = _baselines(n=5).assign(Hipertansiyon=1)
    out = expand_to_trajectories(
        base, pd.Timestamp("2020-01-01"), pd.Timestamp("2024-12-31"),
        TrajectoryConfig(encounters_per_patient_mean=4.0, random_seed=2),
    )
    assert (out["Hipertansiyon"] == 1).all()


def test_continuous_labs_drift_within_window_but_bounded():
    base = _baselines(n=5)
    out = expand_to_trajectories(
        base, pd.Timestamp("2020-01-01"), pd.Timestamp("2024-12-31"),
        TrajectoryConfig(encounters_per_patient_mean=6.0, lab_drift_scale=0.05, random_seed=3),
    )
    # Within each synthetic patient, BP should vary across encounters but stay
    # in a plausible adult range (Gaussian random walk with 5% sd, bounded
    # well below the physiologic clip).
    for _, grp in out.groupby("HASTA_ID"):
        if len(grp) >= 2:
            assert grp["bp_systolic"].std() > 0
        assert grp["bp_systolic"].between(70, 250).all()
        assert grp["bp_diastolic"].between(40, 150).all()
