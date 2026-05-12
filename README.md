# syntha

[Synthea](https://github.com/synthetichealth/synthea)-inspired **hybrid** synthetic patient record generator:

* **(A) data-driven core** — a Gaussian copula trained on the actual `pristine_strict_episodes.csv` / `pristine_tolerant_episodes.csv` learns the joint distribution of age × gender × labs × comorbidities;
* **(B) Synthea-style clinical modules** — declarative pathways that, for each active comorbidity flag, emit realistic Encounters, MedicationRequests (RxNorm-coded), Procedures, and CarePlans on top of the sampled episode;
* **Physiologic constraint filter** — rejection sampling for impossible tuples (pulse pressure, Friedewald coherence, eGFR/creatinine).

Outputs both flat CSV (input schema) and FHIR R4 NDJSON bundles with LOINC/SNOMED/RxNorm codes.

## Why hybrid?

| | Synthea (rules-only) | CTGAN/copula-only | **syntha (hybrid)** |
|---|---|---|---|
| Matches *this cohort's* lab distributions | No (US defaults) | Yes | **Yes** |
| Coherent prescriptions per condition | Yes | No | **Yes** |
| Physiologically valid (BP, eGFR…) | Yes | Sometimes | **Yes** |
| LOINC/SNOMED/RxNorm-coded FHIR | Yes | No | **Yes** |
| Longitudinal trajectories | Yes (state machines) | No | **Yes** (drift + sticky flags) |

## Pipeline

```
CSV → preprocess → Gaussian copula fit → sample
    → physiologic constraint filter
    → (optional) longitudinal trajectory expansion
    → CSV  +  FHIR R4 bundles (with Synthea-style modules firing per condition)
    → trained-model registry (model.pkl + card.json)
```

## Quick start

```bash
pip install -e .

# 1. One-time ingest of WhatsApp-shared CSVs (data/raw/* is gitignored)
bash scripts/ingest_csvs.sh

# 2. Full pipeline both cohorts
N=2000 bash scripts/run_full_pipeline.sh

# Longitudinal: 500 baseline patients × ~4 encounters over 3 years ≈ 2000 rows
syntha generate \
  --input data/raw/pristine_tolerant_episodes.csv \
  --output output/tolerant_long \
  --n 2000 --cohort tolerant \
  --longitudinal --encounters-per-patient 4 --years-of-history 3
```

## CLI

| Command | Description |
|---|---|
| `syntha generate` | Train copula + sample + modules + CSV/FHIR + register model |
| `syntha fit` | Fit and store a copula in a registry without sampling |
| `syntha sample` | Raw sampling from a registered model |
| `syntha fhir` | Convert an existing synthetic CSV to FHIR bundles |
| `syntha list-models` | List models in a registry |
| `syntha show-card` | Print a model card (sha256, n_train, marginals, top correlations) |

## Synthea-style modules

Nine modules ship in the box (`src/syntha/modules/`); each fires on its corresponding comorbidity flag:

| Module | Flag(s) | What it emits |
|---|---|---|
| Hypertension | `Hipertansiyon` | Encounter, 1–2 antihypertensives, CarePlan |
| Diabetes | `DM_Tum`, `DM_Komplikasyonlu` | Encounter, HbA1c, metformin (+insulin if severe), CarePlan |
| Hyperlipidemia | `Hiperlipidemi` | Encounter, lipid panel, statin |
| Thyroid | `Tiroid` | Encounter, TSH, levothyroxine |
| Depression | `Depresyon` | Psych encounter, sertraline, CBT plan |
| Anxiety | `Anksiyete` | Psych encounter, escitalopram (or buspirone if already on SSRI) |
| IHD | `Iskemik_Kalp` | Cardiology encounter, ECG, aspirin + β-blocker + statin |
| Asthma | `Astim` | Resp encounter, spirometry, SABA + ICS |
| COPD | `COPD` | Resp encounter, spirometry, LABA + SABA |

See [docs/MODULES.md](docs/MODULES.md) for the authoring guide.

## Repo layout

```
src/syntha/
  schema.py             # column groups, physiologic ranges
  data.py               # CSV loader
  preprocess.py         # impute / encode / coerce
  generator/
    copula.py           # Gaussian copula fit/sample
    constraints.py      # physiologic post-filter
  modules/              # Synthea-style clinical modules (9)
  fhir/
    codes.py            # LOINC + SNOMED tables
    rxnorm.py           # RxNorm tables for module Rx
    resources.py        # Encounter/MedReq/Procedure/CarePlan builders
    export.py           # bundle writer
  models/registry.py    # trained-model registry + model card
  longitudinal.py       # trajectory expansion
  pipeline.py           # orchestration
  cli.py                # click CLI
tests/                  # 25 unit + integration tests
scripts/                # ingest_csvs.sh, run_full_pipeline.sh
docs/                   # ARCHITECTURE.md, MODULES.md
config/                 # YAML defaults
data/raw/               # source CSVs (gitignored)
output/                 # generated CSV + FHIR + model artifacts (gitignored)
```

## Data handling

* `data/raw/*` is gitignored — source CSVs (even anonymized) never enter the repo.
* `output/` is gitignored — generated CSV/FHIR/model artifacts stay local unless you opt in.
* Each saved model carries a `card.json` containing the source-CSV sha256, so reproducibility is verifiable without committing the data.

## License

Apache 2.0 (matching Synthea).
