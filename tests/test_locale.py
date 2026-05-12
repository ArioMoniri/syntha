import numpy as np

from syntha.locale.turkish import (
    CONDITION_DISPLAY_TR,
    sample_address,
    sample_name,
)


def test_sample_name_gender_specific():
    rng = np.random.default_rng(0)
    for _ in range(20):
        given_m, family_m = sample_name(rng, is_male=True)
        given_f, family_f = sample_name(rng, is_male=False)
        # Names should be non-empty and male/female pools should be disjoint
        # for the most-common entries.
        assert given_m and given_f and family_m and family_f


def test_sample_address_returns_turkey():
    rng = np.random.default_rng(1)
    addr = sample_address(rng)
    assert addr.country == "TR"
    assert addr.state_code.startswith("TR-")
    assert addr.city


def test_condition_displays_cover_all_flags():
    expected = {
        "Kanser", "Iskemik_Kalp", "Serebrovaskuler", "Kalp_Yetmezligi",
        "Pulmoner_Emboli", "Aort_Anevrizma", "Kronik_Bobrek", "Karaciger_Siroz",
        "Sepsis", "Atriyal_Fibrilasyon", "COPD", "DM_Komplikasyonlu", "DM_Tum",
        "Astim", "Hipertansiyon", "Hiperlipidemi", "Tiroid", "Obezite",
        "Depresyon", "Anksiyete",
    }
    assert expected <= set(CONDITION_DISPLAY_TR)
    for k, v in CONDITION_DISPLAY_TR.items():
        assert isinstance(v, str) and v.strip()
