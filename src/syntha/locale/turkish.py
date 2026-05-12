"""Turkish locale data for synthetic patient personalia.

Sources (all openly licensed / public-domain compilations of Turkish public
data — none of these are derived from PHI):

* Given-name distribution — top common Turkish given names by gender, drawn
  from Türkiye İstatistik Kurumu (TÜİK) name-frequency public reports.
* Family names — common Turkish family names.
* Cities & province codes — Türkiye il (province) list with ISO 3166-2:TR
  codes (TR-34 İstanbul, TR-06 Ankara, ...).
* Condition displays — clinical-Turkish preferred terms for each comorbidity
  flag present in the source dataset.

This is locale *vocabulary*, not real-person data. There is no link between
any name + city combination generated here and an actual Turkish citizen.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

GIVEN_NAMES_MALE: list[str] = [
    "Mehmet", "Ahmet", "Mustafa", "Ali", "Hüseyin", "Hasan", "İbrahim",
    "İsmail", "Osman", "Yusuf", "Murat", "Ömer", "Halil", "Süleyman",
    "Ramazan", "Recep", "Salih", "Bekir", "Hamza", "Selim", "Kemal",
    "Emre", "Burak", "Onur", "Serkan", "Engin", "Tolga", "Levent",
    "Cem", "Erdem", "Furkan", "Berk", "Ercan", "Yavuz", "Kerem",
]

GIVEN_NAMES_FEMALE: list[str] = [
    "Fatma", "Ayşe", "Emine", "Hatice", "Zeynep", "Elif", "Meryem",
    "Hanife", "Hülya", "Sevim", "Sultan", "Rabia", "Esra", "Pınar",
    "Selma", "Aslı", "Nuray", "Funda", "Gül", "Derya", "Burcu",
    "Özlem", "Ebru", "Tuğba", "Sibel", "Şerife", "Yeliz", "Songül",
    "Banu", "Çiğdem", "Filiz", "Nazlı", "Berna", "İrem", "Müge",
]

FAMILY_NAMES: list[str] = [
    "Yılmaz", "Kaya", "Demir", "Çelik", "Şahin", "Yıldız", "Yıldırım",
    "Öztürk", "Aydın", "Özdemir", "Arslan", "Doğan", "Kılıç", "Aslan",
    "Çetin", "Kara", "Koç", "Kurt", "Özkan", "Şimşek", "Polat",
    "Erdoğan", "Avcı", "Akın", "Çakır", "Korkmaz", "Bulut", "Çelebi",
    "Güler", "Acar", "Çiçek", "Aksoy", "Aktaş", "Karaca", "Ateş",
]

# (display name, ISO 3166-2:TR code, approximate population weight).
# Weighted toward the largest Turkish metros — represents urban-skewed
# referral patterns typical of large-hospital EHR cohorts.
CITIES_TR: list[tuple[str, str, float]] = [
    ("İstanbul", "TR-34", 15.5),
    ("Ankara", "TR-06", 5.7),
    ("İzmir", "TR-35", 4.4),
    ("Bursa", "TR-16", 3.1),
    ("Adana", "TR-01", 2.3),
    ("Gaziantep", "TR-27", 2.1),
    ("Konya", "TR-42", 2.3),
    ("Antalya", "TR-07", 2.6),
    ("Kayseri", "TR-38", 1.4),
    ("Mersin", "TR-33", 1.9),
    ("Eskişehir", "TR-26", 0.9),
    ("Diyarbakır", "TR-21", 1.8),
    ("Samsun", "TR-55", 1.4),
    ("Denizli", "TR-20", 1.1),
    ("Şanlıurfa", "TR-63", 2.2),
    ("Sakarya", "TR-54", 1.1),
    ("Malatya", "TR-44", 0.8),
    ("Kahramanmaraş", "TR-46", 1.2),
    ("Erzurum", "TR-25", 0.8),
    ("Trabzon", "TR-61", 0.8),
    ("Manisa", "TR-45", 1.5),
    ("Hatay", "TR-31", 1.7),
    ("Mardin", "TR-47", 0.9),
    ("Van", "TR-65", 1.1),
    ("Tekirdağ", "TR-59", 1.1),
]

# Clinical-Turkish preferred terms paired with the source-CSV flag columns.
CONDITION_DISPLAY_TR: dict[str, str] = {
    "Kanser": "Habis neoplazi",
    "Iskemik_Kalp": "İskemik kalp hastalığı",
    "Serebrovaskuler": "Serebrovasküler hastalık",
    "Kalp_Yetmezligi": "Kalp yetmezliği",
    "Pulmoner_Emboli": "Pulmoner emboli",
    "Aort_Anevrizma": "Aort anevrizması",
    "Kronik_Bobrek": "Kronik böbrek hastalığı",
    "Karaciger_Siroz": "Karaciğer sirozu",
    "Sepsis": "Sepsis",
    "Atriyal_Fibrilasyon": "Atriyal fibrilasyon",
    "COPD": "Kronik obstrüktif akciğer hastalığı",
    "DM_Komplikasyonlu": "Komplikasyonlu diabetes mellitus",
    "DM_Tum": "Diabetes mellitus",
    "Astim": "Astım",
    "Hipertansiyon": "Hipertansiyon",
    "Hiperlipidemi": "Hiperlipidemi",
    "Tiroid": "Tiroid hastalığı",
    "Obezite": "Obezite",
    "Depresyon": "Depresyon",
    "Anksiyete": "Anksiyete bozukluğu",
}


@dataclass(frozen=True)
class SampledAddress:
    city: str
    state_code: str
    country: str = "TR"


def sample_name(rng: np.random.Generator, is_male: bool) -> tuple[str, str]:
    given = rng.choice(GIVEN_NAMES_MALE if is_male else GIVEN_NAMES_FEMALE)
    family = rng.choice(FAMILY_NAMES)
    return str(given), str(family)


def sample_address(rng: np.random.Generator) -> SampledAddress:
    weights = np.array([w for _, _, w in CITIES_TR], dtype=float)
    weights = weights / weights.sum()
    idx = int(rng.choice(len(CITIES_TR), p=weights))
    city, code, _ = CITIES_TR[idx]
    return SampledAddress(city=city, state_code=code)
