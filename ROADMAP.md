# 🗺️ syntha roadmap

A staged plan for taking `syntha` from a working Gaussian-copula + Synthea-style hybrid to a fully calibrated, publication-grade Turkish synthetic patient generator.

**Legend** — ✅ shipped · 🟡 in progress · ⬜ planned · 🟣 needs clinician curation

For *what* is needed and *how* to help, see [COLLABORATE.md](COLLABORATE.md). The desktop app's **Collaborate** panel surfaces the same task list live from GitHub Issues.

---

## Shipped

### v0.1 — Data-driven core ✅ (`25a1e7e`)

- Gaussian copula with Spearman → Gaussian conversion, nearest-PSD projection
- Empirical marginals (continuous via ECDF, binary via Bernoulli)
- Independent column-wise missingness
- Physiologic constraints: pulse pressure ≥ 20, Friedewald, eGFR ↔ creatinine
- FHIR R4 export (Patient + Observation + Condition) with LOINC + SNOMED
- CSV output matching input schema
- click-based CLI

### v0.2 — Clinical-pathway layer ✅ (`fbd8555`)

- 9 Synthea-style modules: HTN, DM, hyperlipidemia, thyroid, depression, anxiety, IHD, asthma, COPD
- Encounter / MedicationRequest / Procedure / CarePlan FHIR resources
- RxNorm code table
- Longitudinal trajectory generator (sticky flags, lab drift, Poisson encounter counts)
- Trained-model registry with ModelCard (`source_sha256`, `n_train`, marginals, top correlations)

### v0.3 — Turkish localization ✅

- Turkish HumanName from cohort-realistic given/family distributions
- Turkish Address with ISO 3166-2:TR province codes
- ICD-10 alongside SNOMED for every Condition
- Multilingual displays (English + clinical-Turkish text on every concept)
- `Patient.communication.language = tr`
- Source-cohort representativeness documented

### v0.4 — Validation + sample output ✅

- `syntha validate` — per-column KS, Wasserstein, correlation-Frobenius
- Committed sample output (100 episodes + full FHIR Bundle) in `examples/sample_output/`
- Distribution-comparison plots regenerated on each release

### v0.5 — Scientific-correctness sprint ✅ (`v0.5.0` → `v0.5.6`)

- **5.1** Mixed-type correlation: polyserial (continuous↔binary, Olsson 1982) + tetrachoric (binary↔binary, Bonett & Price; Drezner 1978 BVN CDF). Fixed the ~50% magnitude attenuation.
- **5.2** Joint missingness model — conditional rates + panel-co-missingness propagation (lipid, CBC, CMP, iron, BP).
- **5.3** Privacy audit — Stadler 2022 nearest-neighbor MIA + attribute-inference attack via `syntha audit`. CI fails on MIA AUC > 0.60.
- **5.4** FHIR `DiagnosticReport` grouping for ordered-together labs (lipid, CBC, CMP, iron, BP panels).
- **5.5** Lab time-series (AR(1) drift with column-specific Westgard CV) + intra-encounter BP trajectory.
- **5.6** Reference-range coverage report — fraction of synthetic patients with labs within sex-aware reference intervals.

Plus engineering polish: signed installers for all 3 OSes (macOS notarized, Windows code-signed), Tauri 2 auto-updater (minisign), PyPI OIDC trusted-publisher, Docker image on ghcr.io, SBOM, CodeQL, daily install-button verification, Codecov, release-please, [all-contributors](https://allcontributors.org/), and a [test_cli.py](tests/test_cli.py) smoke-test suite.

### v0.5.10 — MCP connector ✅ (current)

- New optional extra: `pip install "syntha-ehr[mcp]"` installs the [Model Context Protocol](https://modelcontextprotocol.io) SDK and registers a `syntha-mcp` console script.
- Eight tools exposed: `list_bundled_cohorts`, `get_cohort_summary`, `generate_cohort_csv`, `generate_cohort_fhir`, `sample_conditional`, `list_clinical_modules`, `list_physiologic_constraints`, `syntha_version`. Bundles the two trained copulas (`tolerant` n=135,569; `strict` n=55,141) inside the Python package via `[tool.setuptools.package-data]` so no source CSV is required at runtime.
- Transports: stdio (Claude Desktop and local MCP clients) and Streamable HTTP (`syntha-mcp --transport http`, for the Claude.com custom-connector slot).
- DXT manifest at [mcp/manifest.json](mcp/manifest.json) ready for submission to the Anthropic [Connector directory](https://www.claude.com/connectors).
- Full guide + Claude Desktop config snippet + connector-directory submission notes: [docs/MCP.md](docs/MCP.md).
- 12 new MCP tests in [tests/test_mcp_server.py](tests/test_mcp_server.py).

### v0.5.6 — Curation cleanup + collaboration platform ✅

- 29 source-pipeline curation flags dropped from default CSV (BERTurk score, `pristine_*`, drug-safety, `rf_*`). Opt back in with `--curation-flags`.
- Desktop app **longitudinal-mode** toggle — multiple encounters per patient with shared HASTA_ID, age-advance, multiplicative Gaussian lab drift.
- Desktop app **Collaborate** panel — pulls live `help-wanted-clinician` / `help-wanted-dev` issues from the GitHub API and lets contributors claim them with their GitHub handle.
- Model JSON bumped to `syntha-copula-v2`: adds `date_lo`, `date_hi`, `curation_columns`; v1 still loads (lazy fallback).
- Identifiers (`RF_EPISODE2`, `HASTA_ID`, `episode_date`) synthesized client-side in the desktop app.
- Preview shows all columns × 50 rows with sticky header and h+v scroll.

---

## Queued

### v0.6 — Clinical curation 🟣 (needs clinician input — see [COLLABORATE.md](COLLABORATE.md))

- 🟣 Calibrate disease prevalence per module to TÜİK national figures so `syntha` can serve as a Turkish-population baseline, not just a healthy baseline
- 🟣 Review and accept/reject the default first-line drug per module against Turkish primary-care reality (e.g. perindopril vs lisinopril, nebivolol vs metoprolol)
- 🟣 Author 4–6 additional modules for high-prevalence conditions not in the source flags: CKD staging (eGFR-driven), MAFLD (ALT/AST + obesity), anemia (Hb-driven), B12 deficiency (vit B12 directly available)
- 🟣 Verify Turkish display strings against `Türk Tabipleri Birliği` / TR-specific clinical usage rather than literal translation
- 🟣 Increase ICD-10 specificity — current mapping uses unspecified `.9` forms; many flags carry enough information to specify further (`E11.65`, `I50.32`, etc.)
- 🟣 Confirm comorbidity → drug class mappings match TR clinical convention

### v0.7 — Advanced generative engines ⬜

- Optional CTGAN / TVAE backend behind a `--engine ctgan` flag (heavier dependency, similar API)
- Differential-privacy wrapper: Gaussian noise calibrated to (ε, δ) on the empirical-quantile marginals, the polyserial/tetrachoric estimates, and the Bernoulli probabilities, with nearest-PSD reprojection ([Frontiers DH 2025](https://www.frontiersin.org/journals/digital-health/articles/10.3389/fdgth.2025.1576290/full) shows DP-Gaussian-copula stays usable at ε ≈ 1.0)
- Conditional generation via SDV-style conditioning rather than rejection (current `sample-conditional` does AST-validated rejection)

### v0.8 — Disease-progression state machines ⬜

- True longitudinal PADM-style state machines for the four highest-impact chronic conditions (HTN, DM, hyperlipidemia, IHD)
- Time-to-event modeling for cardiovascular complications

### v0.9 — Downstream benchmarks ⬜

- TSTR (Train-on-Synthetic, Test-on-Real) ROC-AUC and Brier-score benchmark via the [SynthEHRella](https://github.com/chenxran/synthEHRella) framework: 80/20 split by `HASTA_ID`, train hypertension-risk model (LR + XGBoost) on each, score on the held-out 20% real test set
- Calibration plots; target TSTR within 0.02 ROC-AUC of TRTR

### v1.0 — Stable release ⬜

- All v0.6 hand curation merged and tagged
- Prevalence calibrated to TÜİK and validated on a TR holdout
- DP-wrapped variant published alongside the standard one
- Companion methods paper / data descriptor on arXiv + Zenodo DOI

---

## How to request curation work

If you're a clinician (Dr. Moniri or a collaborator) and want to provide curation:

1. Pick a 🟣 task above (or any open issue with the `help-wanted-clinician` label).
2. **Easiest path:** open the desktop app, hit the **Collaborate** panel, click "Claim this" on the task. The app pre-fills a GitHub Issue comment with your handle so the maintainers know you've started.
3. **Or:** open an issue using the [🧑‍⚕️ Clinical curation template](https://github.com/ArioMoniri/syntha/issues/new?template=clinical_curation.md&labels=help-wanted-clinician&title=%5Bclinical-curation%5D%20).
4. **Or:** paste the clinical Turkish guidance into the issue and the maintainers will implement.
5. **Or:** edit the relevant Python module directly and open a PR (see [CONTRIBUTING.md](CONTRIBUTING.md)).

Most-likely-to-change files for clinical curation:

| Change | Edit |
|---|---|
| Drug a module prescribes | `src/syntha/modules/<condition>.py` |
| RxNorm code / dose text | `src/syntha/fhir/rxnorm.py` |
| SNOMED / ICD-10 code for a Condition | `src/syntha/fhir/codes.py` |
| Turkish display strings | `src/syntha/locale/turkish.py` |
| Prevalence calibration / disease progression | `src/syntha/longitudinal.py`, `src/syntha/generator/missingness.py` |
| Reference ranges (sex-aware) | `src/syntha/reference_ranges.py` |
