# 🩺 syntha

> **A [Synthea](https://github.com/synthetichealth/synthea)-inspired hybrid synthetic patient record generator.** Learns the joint distribution of real anonymized Turkish-cohort EHR episodes with a Gaussian copula, then layers Synthea-style clinical pathways on top to emit fully-coded FHIR R4 bundles in Turkish.

[![CI](https://github.com/ArioMoniri/syntha/actions/workflows/ci.yml/badge.svg)](https://github.com/ArioMoniri/syntha/actions/workflows/ci.yml)
[![Cross-platform](https://github.com/ArioMoniri/syntha/actions/workflows/cross-platform.yml/badge.svg)](https://github.com/ArioMoniri/syntha/actions/workflows/cross-platform.yml)
[![Release](https://github.com/ArioMoniri/syntha/actions/workflows/release.yml/badge.svg?event=push)](https://github.com/ArioMoniri/syntha/actions/workflows/release.yml)
[![Install buttons](https://github.com/ArioMoniri/syntha/actions/workflows/verify-install-buttons.yml/badge.svg)](https://github.com/ArioMoniri/syntha/actions/workflows/verify-install-buttons.yml)
[![Codecov](https://img.shields.io/codecov/c/github/ArioMoniri/syntha?label=coverage)](https://codecov.io/gh/ArioMoniri/syntha)
[![Latest release](https://img.shields.io/github/v/release/ArioMoniri/syntha?include_prereleases&sort=semver&label=latest&color=2563eb)](https://github.com/ArioMoniri/syntha/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/ArioMoniri/syntha/total?color=2563eb)](https://github.com/ArioMoniri/syntha/releases)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![FHIR R4](https://img.shields.io/badge/FHIR-R4-orange)](https://hl7.org/fhir/R4/)
[![Locale: tr-TR](https://img.shields.io/badge/locale-tr--TR-red)](#turkish-cohort--turkish-output)

---

## What it is

`syntha` is a Python library, command-line tool, and signed cross-platform desktop app for generating realistic *synthetic* patient records — flat CSVs and FHIR R4 transaction Bundles — that match the statistical structure of an anonymized Turkish-cohort EHR while staying physiologically valid and clinically coded.

The pipeline is **hybrid**:

1. **Gaussian copula** fitted on real anonymized episodes — preserves marginal distributions (age, labs, vitals, comorbidity prevalence) and their joint correlation structure.
2. **Physiologic filter** — rejects samples that violate pulse-pressure, Friedewald lipid coherence, or eGFR ↔ creatinine constraints.
3. **Synthea-style clinical modules** — nine condition-specific state activations that emit Encounters, MedicationRequests (RxNorm-coded), Procedures, and CarePlans matching each patient's comorbidity profile.
4. **FHIR R4 export** — Patient + Observation + Condition + Encounter + MedicationRequest + Procedure + CarePlan + DiagnosticReport + RiskAssessment + FamilyMemberHistory, dual-coded LOINC / SNOMED CT / ICD-10 / RxNorm, Turkish locale (names, addresses, language code, display text).

## Desktop app

<p align="center">
  <a href="https://github.com/ArioMoniri/syntha/releases/latest/download/syntha_aarch64.dmg"><img src="docs/assets/download-macos.png" alt="Download macOS Apple Silicon (.dmg)" height="64"/></a>
  &nbsp;
  <a href="https://github.com/ArioMoniri/syntha/releases/latest/download/syntha_x64-setup.exe"><img src="docs/assets/download-windows.png" alt="Download Windows installer (.exe)" height="64"/></a>
  &nbsp;
  <a href="https://github.com/ArioMoniri/syntha/releases/latest/download/syntha_amd64.AppImage"><img src="docs/assets/download-linux.png" alt="Download Linux AppImage" height="64"/></a>
</p>

A Tauri 2 app bundling the trained Gaussian copula. Picks cohort + n + seed + constraints, samples synthetic patients **fully client-side** (no Python at runtime), downloads a CSV. macOS DMG is Developer-ID signed + notarized + stapled. Windows installer is code-signed. All three OSes ship a [minisign-signed auto-updater](app/src-tauri/tauri.conf.json) — existing installs get an in-app upgrade banner on next launch.

Install URLs auto-resolve to the latest release via `releases/latest/download/…` — no per-version link maintenance.

## Install

```bash
# PyPI
pip install syntha-ehr

# Or from source
git clone https://github.com/ArioMoniri/syntha
cd syntha
pip install -e ".[dev]"

# Or Docker
docker pull ghcr.io/ariomoniri/syntha:latest
```

## Quick start

```bash
# Generate 1 000 synthetic episodes + FHIR bundles + model card + validation report
syntha generate \
  --input data/raw/pristine_tolerant_episodes.csv \
  --output output/tolerant \
  --n 1000 --cohort tolerant

# Longitudinal — multiple encounters per patient with shared HASTA_ID
syntha generate \
  --input data/raw/pristine_tolerant_episodes.csv \
  --output output/tolerant_long \
  --n 2000 --cohort tolerant \
  --longitudinal --encounters-per-patient 4 --years-of-history 3

# Validate a synthetic CSV against the source it was trained on
syntha validate \
  --source data/raw/pristine_tolerant_episodes.csv \
  --synthetic output/tolerant/synthetic_tolerant_episodes.csv \
  --output output/tolerant/validation.json

# Run a privacy audit (MIA + AIA)
syntha audit \
  --source data/raw/pristine_tolerant_episodes.csv \
  --synthetic output/tolerant/synthetic_tolerant_episodes.csv \
  --output output/tolerant/privacy.json
```

By default the CSV writer drops 29 source-pipeline curation flags (`pristine_*`, `berturk_*`, drug-safety filters, `rf_*`) — those are training metadata, not clinical observations, and most are degenerate (constant 0 or 1) in the pristine cohort. Pass `--curation-flags` to keep them for QA work.

## What it produces

For every synthetic patient, `syntha` emits a FHIR R4 transaction `Bundle`:

| Resource | Coding | What |
|---|---|---|
| 👤 **Patient** | — | Turkish HumanName + Address (ISO 3166-2:TR province), `communication.language = tr`, derived birthDate |
| 🧪 **Observation** ×~12 | LOINC | Labs (glucose, full lipid panel, CBC, LFTs, eGFR/creatinine, ferritin, B12) + vitals (BP) |
| 🩺 **Condition** ×N | SNOMED CT + ICD-10 | Every active comorbidity, dual-coded, with English + clinical-Turkish display |
| 🏥 **Encounter** ×M | SNOMED CT | One per active condition, fired by the relevant module |
| 💊 **MedicationRequest** ×P | RxNorm | First-line therapy per condition, with dosage |
| 🔬 **Procedure** ×Q | SNOMED CT | HbA1c, lipid panel, ECG, spirometry, etc. |
| 📋 **CarePlan** ×R | SNOMED CT | Disease-specific lifestyle + monitoring plans |
| 📊 **DiagnosticReport** | LOINC | Lipid, CBC, CMP, iron, BP panels grouping their constituent Observations |
| 🎯 **RiskAssessment** | SNOMED CT | Charlson Comorbidity Index |
| 👪 **FamilyMemberHistory** | SNOMED CT | When `rf_kanser` / `rf_kronik_hastalik` are set |

…plus a flat CSV matching the input schema (minus the 29 dropped curation flags) for drop-in use as training data, a JSON model card with the `source_sha256` and marginals, and a validation report.

## Distribution fidelity

A 100-episode sample of `tolerant` vs the full 135 569-row source:

| Metric | Value |
|---|---|
| n source / synthetic | 135 569 / 100 |
| Max Kolmogorov–Smirnov across continuous columns | **0.14** |
| Mean KS | 0.07 |
| Max binary-prevalence error | **0.025** (`has_rx_data`) |
| Disease-prevalence error (HTN / DM / hyperlipidemia) | 0.015 / 0.004 / 0.010 |
| Spearman correlation Frobenius diff | 2.94 |
| Fraction of synthetic patients with all labs in reference range | reported per cohort in `validation_report.json` |

### Marginals

![Marginal distributions — source vs synthetic](docs/figures/distributions.png)

### Spearman correlation structure

![Spearman correlations — source vs synthetic vs diff](docs/figures/correlations.png)

### Disease prevalence

![Comorbidity prevalence — source vs synthetic](docs/figures/prevalence.png)

## FHIR endpoints

```bash
# Spin up a local read-only FHIR R4 server
syntha serve --bundles examples/sample_output/sample_bundles.ndjson --port 8080

# Then:
curl http://127.0.0.1:8080/metadata           # CapabilityStatement
curl http://127.0.0.1:8080/Patient            # search-set Bundle
curl http://127.0.0.1:8080/Patient/{id}
curl http://127.0.0.1:8080/\$export           # Bulk Data NDJSON
```

`scripts/post_to_fhir.sh` posts every transaction Bundle in an NDJSON file to any FHIR R4 endpoint (default: the public [HAPI test server](https://hapi.fhir.org/baseR4)).

## Turkish cohort + Turkish output

The trained models bundled with the desktop app and the example output come from `pristine_strict_episodes.csv` and `pristine_tolerant_episodes.csv` — anonymized retrospective EHR episodes from a Turkish patient cohort selected to represent *clinically pristine* adults. The source CSVs themselves are gitignored and never redistributed.

The output is Turkish-localized:

- Patient names sampled from Turkish given-name and family-name distributions (`src/syntha/locale/turkish.py`).
- Addresses use Turkish cities weighted by approximate population with ISO 3166-2:TR province codes.
- Every Condition carries both an English SNOMED display and a clinical-Turkish translation in `Condition.code.text`.
- `Patient.communication.language` is `tr`.

All clinical terminology used (LOINC, SNOMED CT, ICD-10, RxNorm) comes from open international standards. No licensed terminology content is embedded.

## Synthea-style clinical modules

Nine modules ship out of the box (`src/syntha/modules/`); each fires on its corresponding comorbidity flag.

| Module | Source flag(s) | Emits |
|---|---|---|
| 🫀 Hypertension | `Hipertansiyon` | Encounter, 1–2 antihypertensives (stage 2 → dual), CarePlan |
| 🍬 Diabetes | `DM_Tum`, `DM_Komplikasyonlu` | Encounter, HbA1c, metformin (+ insulin if severe), CarePlan |
| 🧀 Hyperlipidemia | `Hiperlipidemi` | Encounter, lipid panel, statin (high-intensity if LDL ≥ 190) |
| 🦋 Thyroid | `Tiroid` | Encounter, TSH, levothyroxine |
| 😔 Depression | `Depresyon` | Psych encounter, sertraline, CBT CarePlan |
| 😰 Anxiety | `Anksiyete` | Psych encounter, escitalopram (or buspirone if already on an SSRI) |
| ❤️ Ischemic heart disease | `Iskemik_Kalp` | Cardiology encounter, ECG, aspirin + β-blocker + statin |
| 🌬️ Asthma | `Astim` | Resp encounter, spirometry, SABA + ICS |
| 🚭 COPD | `COPD` | Resp encounter, spirometry, LABA + SABA |

Module authoring guide: [docs/MODULES.md](docs/MODULES.md).

## Architecture

```
┌──────────────┐    ┌──────────────────┐    ┌──────────────────────┐
│  Source CSV  │──▶│  Gaussian copula  │──▶│ Physiologic filter   │
│ (Turkish     │    │ (mixed-type ρ;   │    │ (BP, Friedewald,     │
│  pristine)   │    │ nearest-PSD)     │    │  eGFR ↔ creatinine)  │
└──────────────┘    └──────────────────┘    └─────────┬────────────┘
                                                       │
                                  ┌────────────────────┴────────────────────┐
                                  │                                         │
                                  ▼                                         ▼
                       ┌──────────────────┐                  ┌──────────────────────────┐
                       │ Longitudinal     │   (optional)     │  Single-encounter CSV +  │
                       │ expansion        │ ───────────────▶│  FHIR R4 export with      │
                       │ (drift, Poisson) │                  │  module activation        │
                       └─────────┬────────┘                  └──────────────────────────┘
                                 │
                                 ▼
                          (same FHIR export)
```

Full math (mixed-type correlation, nearest-PSD projection, conditional missingness, AR(1) lab drift): [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## CLI reference

| Command | What |
|---|---|
| `syntha generate` | End-to-end: train copula → sample → modules → CSV + FHIR + model card + validation |
| `syntha fit` | Fit and persist a copula in a registry without sampling |
| `syntha sample` | Raw sampling from a registered model |
| `syntha sample-conditional` | AST-validated rejection sampling against a pandas filter expression |
| `syntha fhir` | Convert an existing synthetic CSV to FHIR R4 bundles |
| `syntha validate` | KS / Wasserstein / correlation diff + reference-range coverage |
| `syntha audit` | Privacy audit (membership-inference + attribute-inference) |
| `syntha serve` | Read-only FHIR R4 demo server |
| `syntha export-model` | Export a registered copula to v2 JSON for the desktop app |
| `syntha list-models`, `show-card` | Inspect the registry |

Run `syntha <cmd> --help` for full option lists.

## Example output

A pretty-printed sample Bundle, a 100-episode synthetic CSV, the model card, and the validation report all live under [`examples/sample_output/`](examples/sample_output/) and are tracked in git.

| File | What |
|---|---|
| [`sample_bundle_pretty.json`](examples/sample_output/sample_bundle_pretty.json) | One pretty-printed transaction Bundle |
| [`sample_bundles.ndjson`](examples/sample_output/sample_bundles.ndjson) | 100 Bundles, one per line (Bulk-FHIR style) |
| [`sample_episodes.csv`](examples/sample_output/sample_episodes.csv) | 100 synthetic episodes matching the input schema |
| [`sample_model_card.json`](examples/sample_output/sample_model_card.json) | `source_sha256`, `n_train`, marginals, top correlations |
| [`sample_validation_report.json`](examples/sample_output/sample_validation_report.json) | KS / Wasserstein / correlation-Frobenius per column |

For FHIR-aware rendering: drop the Bundle onto [simplifier.net](https://simplifier.net/) or the [HL7 Clinical FHIR Renderer](https://clinical-fhir.github.io/Renderer/).

## What it is *not*

- **Not** privacy-proof. Gaussian copulas are not differentially private. Run `syntha audit` before sharing any synthetic dataset trained on a small or sensitive cohort.
- **Not** a substitute for real PHI when validity hinges on rare events — the copula reproduces the bulk of the joint distribution, not the long tails.
- **Not** a population-representative Turkish cohort by default — the source is selected for clinically-pristine adults, so synthetic disease prevalence is *lower* than TÜİK national figures. Calibration to TÜİK is a curation task — see [ROADMAP.md](ROADMAP.md) and [COLLABORATE.md](COLLABORATE.md) for how to help.

## Contributing + collaboration

Open-source, Apache 2.0, contributions welcome from clinicians, data scientists, and software engineers alike. Three places to start:

- 🧑‍⚕️ **Clinicians** — see [COLLABORATE.md](COLLABORATE.md) for the live list of tasks needing clinical-Turkish guidance (drug calibration, ICD specificity, new modules), plus the in-app **Collaborate** panel that surfaces the same list with one-click "claim" via your GitHub handle.
- 💻 **Developers** — [CONTRIBUTING.md](CONTRIBUTING.md) for dev setup, commit conventions, and the test matrix.
- 🗺️ **Project direction** — [ROADMAP.md](ROADMAP.md) for the staged plan, what's shipped, and what's queued.

## License + citation

Apache 2.0 © 2026 **Ariorad Moniri** — see [LICENSE](LICENSE). If you use `syntha` in academic work, please cite:

```
Moniri, A. (2026). syntha: hybrid synthetic patient record generator
trained on Turkish pristine-healthy EHR cohorts.
https://github.com/ArioMoniri/syntha
```

## Acknowledgements

| | Project | What it gives us |
|---|---|---|
| 🩺 | [**Synthea**](https://github.com/synthetichealth/synthea) | Inspiration for the clinical-module layer and FHIR output format |
| 🧪 | [**LOINC**](https://loinc.org/) | Lab and observation codes |
| 🧬 | [**SNOMED CT**](https://www.snomed.org/) | Condition, procedure, encounter, and care-plan terminology |
| 📑 | [**ICD-10**](https://icd.who.int/browse10/) | Diagnosis coding alongside SNOMED |
| 💊 | [**RxNorm**](https://www.nlm.nih.gov/research/umls/rxnorm/) | Medication coding |
| 📊 | **Turkish-cohort EHR data steward** | De-identified retrospective episodes (anonymized upstream; never redistributed by this repo) |

## Contributors

Want to be on this list? See [**COLLABORATE.md**](COLLABORATE.md) or pick a card in the in-app **Collaborate** panel.

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%">
        <a href="https://github.com/ArioMoniri">
          <img src="https://avatars.githubusercontent.com/u/92126657?v=4&s=80" width="80px;" alt="Ariorad Moniri"/>
          <br /><sub><b>Ariorad Moniri</b></sub>
        </a><br />
        <span title="Maintainer">🧑‍💼</span>
        <a href="https://github.com/ArioMoniri/syntha/commits?author=ArioMoniri" title="Code">💻</a>
        <a href="#design-ArioMoniri" title="Design">🎨</a>
        <a href="https://github.com/ArioMoniri/syntha/commits?author=ArioMoniri" title="Documentation">📖</a>
        <a href="#maintenance-ArioMoniri" title="Maintenance">🚧</a>
        <a href="#ideas-ArioMoniri" title="Ideas & Planning">🤔</a>
        <a href="https://github.com/ArioMoniri/syntha/pulls?q=is%3Apr+reviewed-by%3AArioMoniri" title="Reviewed Pull Requests">👀</a>
        <a href="#infra-ArioMoniri" title="Infrastructure">🚇</a>
        <a href="https://github.com/ArioMoniri/syntha/commits?author=ArioMoniri" title="Tests">⚠️</a>
      </td>
    </tr>
  </tbody>
</table>
<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

Powered by [all-contributors](https://allcontributors.org/) — comment `@all-contributors please add @username for code,doc` on any issue or PR to nominate someone.

## Community

<table>
  <tr>
    <td align="center" width="33%">
      <a href="https://github.com/ArioMoniri/syntha/discussions">
        <strong>💬 Discussions</strong>
      </a><br />
      <sub>Open questions, "is this the right tool for X?", show-and-tell</sub>
    </td>
    <td align="center" width="33%">
      <a href="https://github.com/ArioMoniri/syntha/issues">
        <strong>🐛 Issues</strong>
      </a><br />
      <sub>Bug reports + feature requests + clinical curation</sub>
    </td>
    <td align="center" width="34%">
      <a href="COLLABORATE.md">
        <strong>🤝 Collaborate</strong>
      </a><br />
      <sub>Live list of clinician + dev + data tasks · also surfaced in the desktop app</sub>
    </td>
  </tr>
  <tr>
    <td align="center">
      <a href="CONTRIBUTING.md"><strong>📖 Contributing</strong></a><br />
      <sub>Dev setup, commit conventions, test matrix</sub>
    </td>
    <td align="center">
      <a href="ROADMAP.md"><strong>🗺️ Roadmap</strong></a><br />
      <sub>Shipped + queued + what needs a clinician</sub>
    </td>
    <td align="center">
      <a href="CHANGELOG.md"><strong>📋 Changelog</strong></a><br />
      <sub>Semver, Keep-a-Changelog, generated by release-please</sub>
    </td>
  </tr>
</table>
