# 🩺 syntha

> **A [Synthea](https://github.com/synthetichealth/synthea)-inspired hybrid synthetic patient record generator**
> — learns the joint distribution of real anonymized Turkish-cohort EHR episodes with a Gaussian copula, then layers Synthea-style clinical pathways on top to emit fully-coded FHIR R4 bundles in Turkish.

[![CI](https://github.com/ArioMoniri/syntha/actions/workflows/ci.yml/badge.svg)](https://github.com/ArioMoniri/syntha/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![FHIR R4](https://img.shields.io/badge/FHIR-R4-orange)](https://hl7.org/fhir/R4/)
[![Locale: tr-TR](https://img.shields.io/badge/locale-tr--TR-red)](#-turkish-cohort--turkish-output)

---

## 📑 Table of contents

- [🔍 Why syntha?](#-why-syntha)
- [🎯 What it produces](#-what-it-produces)
- [⚠️ The catch (what it is *not*)](#%EF%B8%8F-the-catch-what-it-is-not)
- [🇹🇷 Turkish cohort + Turkish output](#-turkish-cohort--turkish-output)
- [🧪 Use cases](#-use-cases)
- [🚀 Quick start](#-quick-start)
- [📊 Distribution fidelity](#-distribution-fidelity)
- [📦 Example output](#-example-output-embedded)
- [🧱 Architecture](#-architecture)
- [🧬 Synthea-style clinical modules](#-synthea-style-clinical-modules)
- [🛠️ CLI reference](#%EF%B8%8F-cli-reference)
- [🗺️ Roadmap](#%EF%B8%8F-roadmap)
- [🤝 Contributing](#-contributing--clinician-curation-welcome)
- [📄 License + citation](#-license--citation)

---

## 🔍 Why syntha?

Synthea is the gold standard for synthetic FHIR patients, but it is **rules-only** and tuned to US population priors. CTGAN-style purely-generative models capture data faithfully but emit physiologically impossible tuples and have no clinical-pathway awareness. **syntha gives you both:**

|  | Synthea (rules-only) | CTGAN / copula-only | **syntha (hybrid)** |
|---|---|---|---|
| Matches *this cohort's* lab distributions | ❌ generic US priors | ✅ | ✅ |
| Coherent prescriptions per condition | ✅ | ❌ | ✅ |
| Physiologically valid (BP, eGFR…) | ✅ | ⚠️ sometimes | ✅ |
| LOINC + SNOMED + ICD-10 + RxNorm-coded FHIR | ✅ | ❌ | ✅ |
| Longitudinal trajectories | ✅ state machines | ❌ | ✅ drift + sticky flags |
| Turkish locale (names, addresses, displays) | ❌ | ❌ | ✅ |

## 🎯 What it produces

For each synthetic patient, syntha emits a FHIR R4 *transaction* `Bundle` containing:

- 👤 **Patient** — Turkish HumanName + Address + `tr` language code, derived birthDate
- 🧪 **Observation** × ~12 — LOINC-coded labs and vitals (glucose, lipid panel, CBC, LFTs, eGFR, BP, …)
- 🩺 **Condition** × N — every active comorbidity flag, **dual-coded SNOMED CT + ICD-10**, with English/Turkish display text
- 🏥 **Encounter** × M — one per active condition, driven by the relevant clinical module
- 💊 **MedicationRequest** × P — RxNorm-coded, dosage included
- 🔬 **Procedure** × Q — e.g. HbA1c, lipid panel, ECG, spirometry
- 📋 **CarePlan** × R — disease-specific lifestyle / monitoring plans

Plus a flat CSV that matches the **input schema** for drop-in use as training data.

## ⚠️ The catch (what it is *not*)

- 🚫 **Not** a substitute for real PHI when validity hinges on rare events — the copula reproduces the *bulk* of the joint distribution, not the long tails.
- 🚫 **Not** privacy-proof. Gaussian copulas are not differentially private; if the source has fewer than ~50 patients with a rare combination, syntha may reproduce that combination too closely. **Do not use** when the source is a small sensitive cohort without adding a DP mechanism.
- 🚫 **No disease *progression* simulator** yet — the copula gives a cross-sectional snapshot; longitudinal mode adds plausible drift but is not a Synthea-PADM state machine. (See [v0.8 in the roadmap](ROADMAP.md).)
- 🚫 The source CSVs are **anonymized retrospective Turkish-cohort episodes of healthy patients** — synthetic disease prevalence is *lower* than Turkish national averages (TÜİK). If you need a population-representative Turkish cohort, calibrate per the [`v0.6` roadmap items](ROADMAP.md).

## 🇹🇷 Turkish cohort + Turkish output

The training data comes from `pristine_strict_episodes.csv` and `pristine_tolerant_episodes.csv` — anonymized retrospective EHR episodes from a Turkish patient cohort selected to represent *clinically pristine* (i.e. healthy / minimally medicated) adults. Source CSVs are **never** committed to this repo (gitignored).

Synthetic output is **Turkish-localized**:

- Patient names sampled from common Turkish given-name and family-name distributions (`src/syntha/locale/turkish.py`).
- Addresses use real Turkish cities weighted by approximate population, with ISO 3166-2:TR province codes.
- Every Condition emits both an English SNOMED display and a clinical-Turkish translation in `Condition.code.text`.
- Patient.communication is set to `tr`.

All clinical terminology used (LOINC, SNOMED CT, ICD-10, RxNorm) comes from **open international standards** — no licensed terminology content is reproduced or embedded.

## 🧪 Use cases

| Where to use it | Why |
|---|---|
| 🤖 **Training ML risk models** without exposing real PHI | The copula preserves joint distributions, so a model trained on synthetic data transfers reasonably to real test sets (TSTR benchmark in v0.9). |
| 🧬 **Bioinformatics healthy-control cohorts** | The source is *pristine healthy* episodes — use the synthetic patients as a normal-baseline group to compare against your disease cohort. |
| 🛠️ **EHR pipeline / ETL integration testing** | Realistic-but-fake FHIR R4 bundles with valid LOINC/SNOMED/ICD-10/RxNorm codes are ideal for testing FHIR consumers, mapping pipelines, and OMOP/i2b2 ETLs without DPA paperwork. |
| 📚 **Teaching / coursework** | Drop-in dataset for biostatistics, epidemiology, and clinical-informatics teaching without IRB. |
| 🔬 **Data augmentation** | Boost rare-event coverage by oversampling synthetic patients with specific comorbidity combinations (conditional sampling lands in v0.7). |

## 🚀 Quick start

```bash
# 1. Install
git clone https://github.com/ArioMoniri/syntha.git
cd syntha
pip install -e .

# 2. (Optional) Ingest your source CSVs — files in data/raw/ are gitignored
bash scripts/ingest_csvs.sh

# 3. Generate 1000 synthetic episodes + FHIR bundles + model card + validation report
syntha generate \
  --input data/raw/pristine_tolerant_episodes.csv \
  --output output/tolerant \
  --n 1000 --cohort tolerant

# 4. Longitudinal — 500 baseline patients × ~4 encounters over 3 years
syntha generate \
  --input data/raw/pristine_tolerant_episodes.csv \
  --output output/tolerant_long \
  --n 2000 --cohort tolerant \
  --longitudinal --encounters-per-patient 4 --years-of-history 3

# 5. Validate any synthetic CSV against its source
syntha validate \
  --source data/raw/pristine_tolerant_episodes.csv \
  --synthetic output/tolerant/synthetic_tolerant_episodes.csv \
  --output output/tolerant/validation.json
```

## 📊 Distribution fidelity

A 100-episode sample of `tolerant` cohort vs the full 135 569-row source:

### Marginal distributions

![Marginal distributions — source vs synthetic](docs/figures/distributions.png)

### Spearman correlation structure

![Spearman correlations — source vs synthetic vs diff](docs/figures/correlations.png)

### Disease prevalence

![Comorbidity prevalence — source vs synthetic](docs/figures/prevalence.png)

### Numbers (from `examples/sample_output/sample_validation_report.json`)

| Metric | Value |
|---|---|
| n (source / synthetic) | 135 569 / 100 |
| **Max Kolmogorov–Smirnov** across continuous columns | **0.14** |
| Mean KS | 0.07 |
| **Max binary-prevalence error** | **0.025** (`has_rx_data`) |
| Disease-prevalence error (HTN / DM / hyperlipidemia) | 0.015 / 0.004 / 0.010 |
| Spearman correlation-matrix Frobenius diff | 2.94 |

> 📝 The KS statistic is well below the typical 0.20 "noticeable difference" threshold for every column; binary marginals (gender, disease prevalence) match to within ~1 percentage point.

## 📦 Example output (embedded)

A pretty-printed sample FHIR Bundle, a 100-episode CSV, the validation report, and the model card all live under [`examples/sample_output/`](examples/sample_output/) and are tracked in git.

**Patient resource — Turkish localized:**

```json
{
  "resourceType": "Patient",
  "id": "…",
  "gender": "female",
  "name": [{"use": "official", "family": "Bulut", "given": ["Pınar"]}],
  "address": [{
    "use": "home", "type": "physical",
    "city": "Antalya", "state": "TR-35", "country": "TR"
  }],
  "communication": [{
    "language": {"coding": [{"system": "urn:ietf:bcp:47", "code": "tr", "display": "Turkish"}]},
    "preferred": true
  }],
  "birthDate": "1970-…"
}
```

**Condition — dual SNOMED + ICD-10 + Turkish display:**

```json
{
  "resourceType": "Condition",
  "code": {
    "coding": [
      {"system": "http://snomed.info/sct", "code": "414545008",
       "display": "Ischemic heart disease (disorder)"},
      {"system": "http://hl7.org/fhir/sid/icd-10", "code": "I25.9",
       "display": "Chronic ischaemic heart disease, unspecified"}
    ],
    "text": "Ischemic heart disease (disorder) / İskemik kalp hastalığı"
  }
}
```

**MedicationRequest — RxNorm-coded:**

```json
{
  "resourceType": "MedicationRequest",
  "medicationCodeableConcept": {
    "coding": [{
      "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
      "code": "243670", "display": "Aspirin 81 MG Oral Tablet"
    }]
  },
  "dosageInstruction": [{"text": "81 mg daily"}]
}
```

## 🧱 Architecture

```
┌──────────────┐    ┌──────────────────┐    ┌──────────────────────┐
│  Source CSV  │──▶│  Gaussian copula  │──▶│ Physiologic filter   │
│ (Turkish     │    │ (Spearman → ρ;   │    │ (BP, Friedewald,     │
│  pristine)   │    │ nearest-PSD)     │    │  eGFR/creatinine)    │
└──────────────┘    └──────────────────┘    └─────────┬────────────┘
                                                       │
                                  ┌────────────────────┴────────────────────┐
                                  │                                         │
                                  ▼                                         ▼
                       ┌──────────────────┐                  ┌──────────────────────────┐
                       │ Longitudinal     │   (optional)     │  Direct single-episode   │
                       │ expansion        │ ───────────────▶│  CSV + FHIR R4 export     │
                       │ (drift, Poisson) │                  │  with Synthea-style       │
                       └─────────┬────────┘                  │  module activation        │
                                 │                            └──────────────────────────┘
                                 ▼
                          (same FHIR export)
```

Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the math (Spearman→Gaussian transform, nearest-PSD projection, constraint rules).

## 🧬 Synthea-style clinical modules

Nine modules ship out of the box (`src/syntha/modules/`); each fires on its corresponding source-CSV comorbidity flag:

| Module | Flag(s) | Emits |
|---|---|---|
| 🫀 Hypertension | `Hipertansiyon` | Encounter, 1–2 antihypertensives (stage 2 → dual), CarePlan |
| 🍬 Diabetes | `DM_Tum`, `DM_Komplikasyonlu` | Encounter, HbA1c, metformin (+ insulin if severe), CarePlan |
| 🧀 Hyperlipidemia | `Hiperlipidemi` | Encounter, lipid panel, statin (high-intensity if LDL ≥ 190) |
| 🦋 Thyroid | `Tiroid` | Encounter, TSH, levothyroxine |
| 😔 Depression | `Depresyon` | Psych encounter, sertraline, CBT CarePlan |
| 😰 Anxiety | `Anksiyete` | Psych encounter, escitalopram (or buspirone if already on SSRI) |
| ❤️ IHD | `Iskemik_Kalp` | Cardiology encounter, ECG, aspirin + β-blocker + statin |
| 🌬️ Asthma | `Astim` | Resp encounter, spirometry, SABA + ICS |
| 🚭 COPD | `COPD` | Resp encounter, spirometry, LABA + SABA |

See [docs/MODULES.md](docs/MODULES.md) for the authoring guide. Clinician contributions for **TR-specific drug choices** are highly welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## 🛠️ CLI reference

| Command | Description |
|---|---|
| `syntha generate` | End-to-end: train copula + sample + modules + CSV/FHIR + model card + validation report |
| `syntha fit` | Fit and persist a copula in a registry without sampling |
| `syntha sample` | Raw sampling from a registered model |
| `syntha fhir` | Convert an existing synthetic CSV to FHIR bundles |
| `syntha validate` | KS / Wasserstein / correlation diff between source and synthetic |
| `syntha list-models` | List models in a registry |
| `syntha show-card` | Print a model card |

Run `syntha <cmd> --help` for full option lists.

## 🗺️ Roadmap

The full phased roadmap (v0.1 → v1.0) lives in [ROADMAP.md](ROADMAP.md). Highlights:

- **v0.6 — clinician curation** 🟣 — needs Dr. Moniri (or a collaborator)
- **v0.7 — optional CTGAN/TVAE backend** ⬜
- **v0.8 — true Synthea PADM-style state machines** ⬜
- **v0.9 — TSTR benchmark** ⬜
- **v1.0 — PyPI + paper** ⬜

## 🤝 Contributing — clinician curation welcome

Open an issue with the [Clinical curation template](.github/ISSUE_TEMPLATE/clinical_curation.md) or just paste your guidance into a fresh issue. Code contributions: see [CONTRIBUTING.md](CONTRIBUTING.md). All tests must pass in CI before merge.

## 📄 License + citation

Apache 2.0 © 2026 **Ariorad Moniri** — see [LICENSE](LICENSE).

If you use syntha in academic work, please cite:

```
Moniri, A. (2026). syntha: hybrid synthetic patient record generator
trained on Turkish pristine-healthy EHR cohorts.
https://github.com/ArioMoniri/syntha
```

---

### Acknowledgements

- 🩺 [Synthea](https://github.com/synthetichealth/synthea) — the inspiration for the clinical-module layer and FHIR output format.
- 🌐 Open clinical terminologies: [LOINC](https://loinc.org/), [SNOMED CT](https://www.snomed.org/), [ICD-10](https://icd.who.int/browse10/), [RxNorm](https://www.nlm.nih.gov/research/umls/rxnorm/).
- 📊 The anonymized Turkish-cohort EHR data used to train the copula (de-identified by the upstream data steward; never redistributed by this repo).
