# syntha — Connector Listing Copy

Paste-ready text for the Anthropic Connector directory submission form (and Smithery / mcp.so).

---

## Display name

```
syntha — synthetic patient generator
```

## One-line tagline (≤ 80 chars)

```
Generate realistic synthetic patient cohorts (CSV + FHIR R4) for safe ML / teaching.
```

## Short description (≤ 200 chars)

```
Generate realistic, fully synthetic patient cohorts — CSV or FHIR R4 — from a trained Gaussian copula with Synthea-style clinical modules and a Turkish-locale layer. Never returns real-patient data.
```

## Long description (≈ 800 chars — paste into the form's "About" field)

```
syntha generates fully synthetic patient cohorts for ML training, healthy-control cohorts in case–control studies, FHIR pipeline integration tests, data-augmentation, and biostatistics teaching — without redistributing any real EHR record.

A mixed-type Gaussian copula (polyserial + tetrachoric correlations) is paired with nine Synthea-style clinical modules and a Turkish-locale layer that emits LOINC + SNOMED CT + ICD-10 + RxNorm coded resources with bilingual EN/TR display strings.

Eight tools cover generation (CSV, FHIR R4 NDJSON), AST-validated conditional rejection sampling, and inspection of the bundled cohorts (tolerant n=135,569; strict n=55,141). Every release runs the Stadler 2022 NN-MIA privacy audit in CI.

Apache 2.0. No PHI ever returned. No telemetry. No filesystem side-effects.
```

## Tags / keywords

```
synthetic-data, synthetic-ehr, fhir, fhir-r4, healthcare, clinical-informatics,
gaussian-copula, turkish, loinc, snomed, icd-10, rxnorm, biostatistics,
data-augmentation, research, open-source
```

## Category

```
Healthcare & Life Sciences
```

(secondary: `Developer Tools`, `Data & Analytics`)

## Tool list (≤ 100 chars each — for the submission form's tool-by-tool table)

| Tool | Description |
|---|---|
| `syntha_version` | Library version and bundled-cohort fingerprints. |
| `list_bundled_cohorts` | List the two bundled cohorts (tolerant, strict) with size + format. |
| `get_cohort_summary` | n_train, comorbidity prevalences, lab/vital columns, source date window. |
| `generate_cohort_csv` | N synthetic patients as a CSV string (default n=100, max 10,000). |
| `generate_cohort_fhir` | N synthetic patients as FHIR R4 NDJSON with nine clinical modules. |
| `sample_conditional` | AST-validated rejection sampling against a pandas-style filter expression. |
| `list_clinical_modules` | The nine Synthea-style modules and the source flag each fires on. |
| `list_physiologic_constraints` | The validity-rejection rules (pulse pressure, Friedewald, eGFR↔creatinine). |

## Sample prompts (for the listing's "Try it" section)

1. *"Using the syntha connector, give me 50 synthetic patients aged 60+ with hypertension and diabetes, as a CSV."*
2. *"Generate 10 FHIR R4 bundles from syntha's tolerant cohort and show me the LOINC codes in the first bundle."*
3. *"What's the prevalence of thyroid disorders in syntha's tolerant cohort? Then sample 20 patients with that condition."*
4. *"From syntha, generate 200 synthetic patients with hyperlipidemia where LDL > 160, save as CSV, and tell me the mean age."*
5. *"Show me the nine clinical modules syntha can fire and list which Turkish source flag each one uses."*

## Demo screenshots

Located under `docs/figures/`:

- `docs/figures/distributions.png` — marginal-distribution overlay (source vs synthetic) for 6 key analytes.
- `docs/figures/prevalence.png` — comorbidity-prevalence comparison.
- `docs/figures/correlations.png` — Spearman correlation heatmap (source / synthetic / difference).

Upload these directly via the submission form's image upload field.

## URLs to paste into the form

| Field | URL |
|---|---|
| Homepage | https://github.com/ArioMoniri/syntha |
| Documentation | https://github.com/ArioMoniri/syntha/blob/main/docs/MCP.md |
| Source repository | https://github.com/ArioMoniri/syntha |
| License | https://www.apache.org/licenses/LICENSE-2.0 |
| Privacy policy | https://github.com/ArioMoniri/syntha/blob/main/PRIVACY.md |
| Terms of use | https://github.com/ArioMoniri/syntha/blob/main/TERMS.md |
| Security policy | https://github.com/ArioMoniri/syntha/blob/main/SECURITY.md |
| Support | https://github.com/ArioMoniri/syntha/issues |

## Author block

```
Ariorad Moniri
Acibadem University School of Medicine, Istanbul, Turkey
ORCID: 0000-0002-5171-3532
```

Co-author (paper): Umut Kilinckaya — ORCID 0009-0008-4576-8589.

## License

Apache-2.0 — full text at https://www.apache.org/licenses/LICENSE-2.0.txt or `LICENSE` in the repo.

## Pricing

Free (open source). No paid tier, no usage caps from the maintainer side.

## What runs where

- **DXT install path (recommended)**: the connector runs **fully locally** inside Claude Desktop. No data leaves the user's machine.
- **HTTP install path**: the user (or you, if you choose to host it) runs `syntha-mcp --transport http` on a host they control. The connector still emits no telemetry; data flows are entirely between the user's Claude client and their chosen host.
