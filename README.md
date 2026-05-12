# syntha

Synthetic patient record generator, [Synthea](https://github.com/synthetichealth/synthea)-inspired but **data-driven**: trained on `pristine_strict_episodes.csv` / `pristine_tolerant_episodes.csv` (anonymized clinical episodes of healthy patients) and capable of emitting both flat CSV (input schema) and FHIR R4 JSON bundles.

## Why not just fork Synthea?

Synthea is a rule-based disease-progression simulator with hand-curated US-population defaults. For a specific cohort like yours (Turkish, healthy adults), a **Gaussian copula trained on the actual data** preserves the joint distribution of age × gender × labs × comorbidities far more faithfully than Synthea's generic priors. We borrow Synthea's *output format* (FHIR R4, LOINC, SNOMED) but learn distributions from your CSV.

## Pipeline

```
CSV → preprocess → Gaussian copula fit → sample → physiologic-constraint filter → CSV + FHIR R4 JSON
```

1. **Copula** — empirical marginals (continuous via ECDF, binary via Bernoulli) + Spearman-rank correlation, projected to nearest PSD.
2. **Constraints** — rejection sampling for: systolic > diastolic, Friedewald cholesterol coherence, eGFR/creatinine consistency.
3. **FHIR export** — `Patient`, `Observation` per lab/vital with LOINC codes, `Condition` per active comorbidity flag with SNOMED codes, bundled as a `transaction` Bundle (one per synthetic patient).

## Quick start

```bash
# 1. Install
pip install -e .

# 2. Ingest source CSVs (one-time; files are gitignored)
bash scripts/ingest_csvs.sh

# 3. Run full pipeline (both cohorts, CSV + FHIR)
bash scripts/run_full_pipeline.sh

# Or manually:
syntha generate \
  --input data/raw/pristine_strict_episodes.csv \
  --output output/strict \
  --n 5000 \
  --cohort strict
```

## CLI

| Command | Description |
|---|---|
| `syntha generate` | Train copula + generate synthetic episodes + write CSV + FHIR |
| `syntha fit` | Fit copula and save model only |
| `syntha sample` | Sample from a fitted model |
| `syntha fhir` | Convert an existing synthetic CSV to FHIR bundles |

## Repo layout

```
src/syntha/
  schema.py             # column groups, LOINC/SNOMED ranges
  data.py               # CSV loader
  preprocess.py         # impute / encode / split features
  generator/
    copula.py           # Gaussian copula fit/sample
    constraints.py      # physiologic post-filter
  fhir/
    codes.py            # LOINC + SNOMED tables
    export.py           # FHIR R4 Bundle writer
  pipeline.py           # orchestration
  cli.py                # click CLI
tests/                  # unit + integration tests
scripts/                # shell helpers
config/                 # YAML defaults
docs/                   # architecture notes
data/raw/               # source CSVs (gitignored)
output/                 # generated files (gitignored)
```

## Data handling

- Source CSVs are anonymized but treated as sensitive: `data/raw/*` is gitignored.
- No PHI is ever committed.
- Synthetic outputs in `output/` are also gitignored; commit only what you intend to share.

## License

Apache 2.0 (matching Synthea).
