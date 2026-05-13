# 🩺 syntha v0.4.0 — first public release

A [Synthea](https://github.com/synthetichealth/synthea)-inspired **hybrid synthetic patient record generator**:

- 🧠 **(A) Data-driven core** — Gaussian copula trained on the joint distribution of real anonymized Turkish-cohort EHR episodes
- 🧬 **(B) Synthea-style clinical-pathway layer** — nine modules that emit realistic Encounters, prescriptions, procedures, and care plans for each active comorbidity
- 🇹🇷 **Turkish-localized output** — Patient names, addresses, language code, plus clinical-Turkish display strings on every Condition
- 📡 **FHIR R4 + flat CSV** — fully coded with LOINC, SNOMED CT, ICD-10, and RxNorm

This is the **v0.4.0 first public release**, bundling everything from the initial copula prototype through the desktop app. CI runs on Python 3.10 → 3.13 (all green).

---

## 🆕 Highlights

### 🖥️ Desktop app (new in v0.4)

A **Tauri 2** desktop GUI that runs the copula sampler **fully client-side in TypeScript** — no Python required at runtime. Pick cohort, n, seed, toggle physiologic constraints, hit Generate, download a CSV. The bundled model JSONs (~170 KB each) are trained on the full source cohorts (135 569 + 55 141 rows).

📥 **Installers are attached to this release** — see the install buttons in the [README](https://github.com/ArioMoniri/syntha#%EF%B8%8F-desktop-app--generate-synthetic-patients-without-code).

| Platform | File |
|---|---|
| 🍎 macOS Apple Silicon | `syntha_aarch64.dmg` |
| 🪟 Windows x64 | `syntha_x64-setup.exe` |
| 🐧 Linux x86_64 | `syntha_amd64.AppImage` |

### 🧠 Hybrid generator (v0.1 → v0.3)

| Component | What it does |
|---|---|
| Gaussian copula | Spearman → Pearson conversion `ρ = 2 sin(π ρ_s / 6)`, nearest-PSD projection, empirical-quantile inverse, **canonical latent-threshold form** `X = 1{u ≥ 1 − p}` for binaries (fixed in v0.3.2) |
| Physiologic constraint filter | Rejection sampling for `pulse-pressure ≥ 20 mmHg`, Friedewald coherence (`|chol − (HDL + LDL + TG/5)| ≤ 40`), eGFR ↔ creatinine consistency |
| 9 Synthea-style modules | Hypertension, diabetes, hyperlipidemia, thyroid, depression, anxiety, IHD, asthma, COPD — each emits an Encounter + appropriate MedicationRequest(s) + Procedure(s) + CarePlan |
| Longitudinal mode | Sticky comorbidity flags, Gaussian drift on continuous labs, Poisson encounter counts over a configurable history window |
| Trained-model registry | Persists copula + `card.json` (source sha256, n_train, marginals, top-K Spearman correlations) |

### 📡 FHIR endpoints

| Resource | Codes | Endpoint |
|---|---|---|
| 👤 `Patient` | TR HumanName + Address + `tr` language | `/Patient/{id}` |
| 🧪 `Observation` | LOINC | `/Observation` |
| 🩺 `Condition` | SNOMED CT + ICD-10 dual coding + bilingual EN/TR text | `/Condition` |
| 🏥 `Encounter` | SNOMED CT | `/Encounter` |
| 💊 `MedicationRequest` | RxNorm | `/MedicationRequest` |
| 🔬 `Procedure` | SNOMED CT | `/Procedure` |
| 📋 `CarePlan` | SNOMED CT activities | `/CarePlan` |
| 📦 transaction `Bundle` | — | `POST /` |

Spin up a local read-only FHIR R4 server backed by a generated bundles NDJSON:

```bash
syntha serve --bundles examples/sample_output/sample_bundles.ndjson
```

Or POST every bundle to any FHIR server (defaults to the public HAPI test server):

```bash
bash scripts/post_to_fhir.sh
```

### 🇹🇷 Turkish localization

- 35 male + 35 female Turkish given names, 35 family names
- 25 Turkish cities weighted by population, with ISO 3166-2:TR province codes
- Clinical-Turkish preferred terms for all 20 comorbidity flags (`Hipertansiyon`, `Diabetes mellitus`, `İskemik kalp hastalığı`, …)
- Patient.communication set to `tr`
- The source cohort is **Turkish pristine-healthy adults**; synthetic disease prevalence is *lower than Turkish national averages* (TÜİK) by design

### 📊 Validation

`syntha validate` and the pipeline both write `validation_report.json` with:

- Kolmogorov–Smirnov + Wasserstein-1 distance per continuous column
- Mean/std absolute error per continuous column
- Prevalence absolute error per binary column
- Frobenius diff between source and synthetic Spearman correlation matrices

On the committed 100-row sample vs the full 135 569-row tolerant source:

| Metric | Value |
|---|---|
| Max KS | 0.14 |
| Mean KS | 0.07 |
| Max binary-prevalence error | 0.025 |
| Correlation Frobenius diff | 2.94 |

---

## 📦 What's in this release

```
src/syntha/
  schema.py, data.py, preprocess.py        # CSV loader, type coercion
  generator/copula.py, constraints.py      # Gaussian copula + physiologic filter
  modules/                                 # 9 Synthea-style clinical modules
  fhir/codes.py, rxnorm.py, resources.py,  # LOINC/SNOMED/ICD-10/RxNorm tables
       export.py                           # FHIR R4 transaction Bundle writer
  locale/turkish.py                        # Turkish names, cities, displays
  models/registry.py                       # Trained-model registry + ModelCard
  longitudinal.py                          # Trajectory expansion
  validate.py                              # KS / Wasserstein / correlation diff
  server.py                                # Minimal FHIR R4 read-only HTTP server
  export_model.py                          # JSON exporter for the desktop app
  pipeline.py, cli.py                      # Orchestration + click CLI
app/                                       # Tauri 2 desktop app
  src/copula.ts, main.ts                   # TypeScript port of the sampler
  src/model_{tolerant,strict}.json         # Bundled trained models
  src-tauri/                               # Rust shell
.github/workflows/{ci.yml,release.yml}     # CI matrix + Tauri release build
examples/sample_output/                    # 100-episode CSV + FHIR + report
docs/figures/                              # Distribution / correlation / prevalence plots
```

37 unit + integration tests, all passing on the CI matrix.

---

## 🔧 Quick start

### Use the desktop app (no Python)

Download the right installer from the list above, install, run.

### Use the Python library

```bash
git clone https://github.com/ArioMoniri/syntha
cd syntha
pip install -e .

# Drop your CSVs in data/raw/ (gitignored), then:
N=2000 bash scripts/run_full_pipeline.sh

# Or for a single cohort:
syntha generate \
  --input data/raw/pristine_tolerant_episodes.csv \
  --output output/tolerant \
  --n 2000 --cohort tolerant
```

---

## ⚠️ Known limitations

- 🚫 **Not differentially private.** The Gaussian copula reproduces the empirical joint distribution; small rare-combination cohorts will be reproduced too closely. Do not use on small sensitive datasets without a DP mechanism.
- ⚠️ **Continuous↔binary correlation magnitudes attenuated ~50%.** Signs are correct (since v0.3.2), but Spearman correlation on a tied binary column is biased toward zero. Proper fix is polyserial/tetrachoric correlation — queued as **v0.4.x** in [ROADMAP.md](https://github.com/ArioMoniri/syntha/blob/main/ROADMAP.md).
- 🚫 **No disease-progression state machines.** Longitudinal mode adds drift + sticky flags, not a Synthea PADM-style state machine. Queued as **v0.8**.
- 🇹🇷 **Cohort represents Turkish *healthy* adults.** Synthetic disease prevalence is lower than the Turkish national average by construction. Calibration to TÜİK is queued as **v0.6** and is awaiting clinician input — see the *Clinical curation* issue template.

---

## 🤝 Want to help? Clinician curation especially welcome

Five v0.6 tasks are flagged 🟣 in [ROADMAP.md](https://github.com/ArioMoniri/syntha/blob/main/ROADMAP.md) — TR-specific first-line drug calibration, MAFLD / CKD-staging / B12 modules, prevalence calibration to TÜİK, Turkish clinical-display review, ICD-10 specificity.

Three ways to contribute, easiest first:

1. 💬 **Just chat the maintainer** in any open Claude session — paste guidance, the code will land.
2. 📝 [**Open a Clinical curation issue**](https://github.com/ArioMoniri/syntha/issues/new?template=clinical_curation.md&labels=clinical-curation&title=%5Bclinical-curation%5D%20) with the prefilled template.
3. 🔧 Submit a PR — see [CONTRIBUTING.md](https://github.com/ArioMoniri/syntha/blob/main/CONTRIBUTING.md).

---

## 🙏 Acknowledgements

- 🩺 [Synthea](https://github.com/synthetichealth/synthea) — the inspiration for the clinical-module layer and FHIR output format.
- 🌐 Open clinical terminologies: [LOINC](https://loinc.org/), [SNOMED CT](https://www.snomed.org/), [ICD-10](https://icd.who.int/browse10/), [RxNorm](https://www.nlm.nih.gov/research/umls/rxnorm/).
- 📊 The anonymized Turkish-cohort EHR data used to train the copula (de-identified by the upstream data steward; never redistributed by this repo).

---

## 📜 Full changelog

See [CHANGELOG.md](https://github.com/ArioMoniri/syntha/blob/main/CHANGELOG.md). Highlights since the initial prototype:

- **v0.1** — Gaussian copula core, physiologic constraints, FHIR R4 export
- **v0.2** — 9 Synthea-style modules + longitudinal mode + model registry
- **v0.3** — Turkish localization, ICD-10 dual coding, validation report, sample output, plots, CI
- **v0.3.1** — `syntha serve` FHIR R4 demo server + POST helper + embedded README previews
- **v0.3.2** — Critical fix: binary-threshold sign bug in copula (`u < p` → `u ≥ 1 − p`)
- **v0.4.0** — **Tauri desktop app + GitHub Actions release workflow + install buttons** ← this release

📄 Apache 2.0 © 2026 **Ariorad Moniri**
