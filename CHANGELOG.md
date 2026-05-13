# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0-dev] — 2026-05-13 (in progress)

### Added — scientific-correctness sprint per MO-reviewed roadmap

- 🧮 **Polyserial + tetrachoric correlation** (`src/syntha/generator/mixed_corr.py`, 14 tests). The Gaussian copula now uses the **right estimator per pair type**:
  - continuous↔continuous: Kruskal `ρ = 2 sin(π ρₛ/6)` (unchanged)
  - continuous↔binary: **polyserial** (Olsson 1982 two-step) — recovers latent correlation directly via `ρ = r_pb · √(p(1-p)) / φ(τ)`
  - binary↔binary: **tetrachoric** — finds the latent ρ such that the bivariate-normal CDF reproduces the observed 2×2 cell probabilities, solved by bisection
  - dispatch via `GaussianCopulaGenerator.fit(..., corr_method="mixed")` (now default; `"spearman"` preserved for v0.4 reproducibility)
- 🩺 **Synthetic-patient FHIR marker** (G1 from medical-officer review): every Patient resource now carries the standard `HTEST` tag (terminology.hl7.org/CodeSystem/v3-ActReason) **plus** a `syntha-copula` source tag. Matches Synthea's convention and is a patient-safety prerequisite — synthetic patients can no longer be confused for real ones in downstream systems.
- 🧪 **Lab-panel DiagnosticReport grouping** (`src/syntha/fhir/panels.py`, 3 tests). Five panels emitted when their constituent Observations exist: lipid panel (LOINC 57698-3), CBC (58410-2), CMP (24323-8), iron studies (24350-1), BP panel (85354-9). FHIR consumers (HAPI, Aidbox, OMOP ETL) now see ordered-together labs grouped correctly.
- 📋 **Medical Officer Review** (`docs/MEDICAL_OFFICER_REVIEW_v0.5.md`) — explicit clinician-perspective sign-off on the v0.5 roadmap, with 3 mandatory guardrails (G1 ✓ shipped; G2 G3 queued) and revised implementation-priority order.
- 📘 **Expanded ROADMAP** with 6 v0.5 items, each carrying a Method / Reference / Implementation / Success-metric block.

### Validated (empirical, on real source data)

Strict cohort (n=55,141), `gender_is_male` × 14 continuous labs:
- v0.4 Spearman pipeline: **mean magnitude ratio (synthetic / source) = 83.7%**
- v0.5 mixed-corr fix:    **mean magnitude ratio = 94.2%**  (**+10.5 percentage points**)
- Example specific pairs: gender↔hemoglobin source +0.761 → v0.5 +0.735 (was +0.635 in v0.4); gender↔HDL source −0.505 → v0.5 −0.499 (was −0.424).

The strict cohort is "pristine healthy" by construction so disease-flag prevalences are ~0; the binary↔binary tetrachoric estimator has full unit-test coverage on toy data and will deliver larger gains on the tolerant cohort once a fresh CSV is re-ingested.

### Regenerated artifacts

- `app/src/model_strict.json` — refitted with `corr_method="mixed"` (173 KB; same size, better correlations)

### Tests

55 / 55 passing (was 51).

## [0.4.0] — 2026-05-13

### Added
- 🖥️ **Tauri 2 desktop app** (`app/`) — Rust shell + TypeScript frontend, runs the Gaussian copula sampler entirely client-side using a bundled ~170 KB exported model JSON per cohort. No Python required at runtime. UI exposes cohort selection (strict / tolerant), n episodes, seed, physiologic-constraint toggle, missingness toggle. One button → download CSV with timestamped filename.
- 📦 **`syntha export-model` CLI** — serialize a registered copula to compact JSON (downsamples each continuous marginal to ≤ N order statistics; default 200). Used by the app build pipeline.
- 🔧 **`scripts/refresh_app_model.sh`** — regenerates `app/src/model_{tolerant,strict}.json` from the latest fitted copulas.
- 🚀 **`.github/workflows/release.yml`** — builds `.dmg` (macOS aarch64), `-setup.exe` (Windows x64), `.AppImage` (Linux x86_64) on `v*` tag pushes; renames artifacts to stable filenames (`syntha_aarch64.dmg`, `syntha_x64-setup.exe`, `syntha_amd64.AppImage`) and uploads to the GitHub release.
- 🎨 **`scripts/make_assets.py`** — generates Tauri app icons (32 / 128 / 128@2x / `.icns` / `.ico`) and README download-button PNGs (`docs/assets/download-{macos,windows,linux}.png`) procedurally so we don't ship licensed artwork.
- 📥 **Install buttons in README** linking to the latest GitHub release artifacts.

### Notes
- The TS copula implementation in `app/src/copula.ts` matches the Python reference one-for-one (Cholesky on Σ, Φ-CDF mapping, ECDF inverse via linear interpolation on order statistics, **post-v0.3.2 latent threshold** `X = 1{u ≥ 1−p}` for binaries, physiologic-constraint rejection sampling). xoshiro128** PRNG seeded by user input.
- App is **not signed/notarized** by default — Tauri's release workflow stub produces ad-hoc-signed builds. Adding Apple Developer ID / Microsoft Authenticode signing is a v0.5 task (see ROADMAP).

## [0.3.2] — 2026-05-12

### Fixed
- 🐛 **Binary-threshold sign bug in Gaussian copula sampling.** The previous
  implementation used `X = 1{u < p}`, which produced the correct marginal
  P(X=1) = p but **inverted the sign** of every continuous↔binary correlation.
  On the real `pristine_tolerant_episodes.csv`, this meant e.g.
  `corr(age, Hipertansiyon)` was reported as **−0.111** in synthetic output
  vs **+0.207** in the source — wrong direction.
- Switched to the canonical latent-Gaussian threshold form `X = 1{u ≥ 1 − p}`.
  After the fix, every continuous↔binary correlation in the verification
  matches the source in sign (every signed pair: age↔HTN +0.207 → +0.102,
  age↔DM +0.078 → +0.028, BP↔HTN +0.133 → +0.073, etc.).
- Added regression test `test_continuous_binary_correlation_sign_preserved`.

### Known limitation (now explicit, queued for v0.4)
- Magnitudes of continuous↔binary correlations are **attenuated ~50%** even
  after the sign fix, because Spearman rank correlation on a tied (binary)
  column is biased toward 0. The proper fix is **polyserial** correlation for
  binary↔continuous and **tetrachoric** for binary↔binary pairs — added as
  v0.4 in ROADMAP.md.

## [0.3.1] — 2026-05-12

### Added
- 🌐 **`syntha serve`** — minimal in-memory FHIR R4 read-only server (`src/syntha/server.py`, ~150 LOC, stdlib only). Exposes canonical REST endpoints (`GET /Patient`, `GET /Observation/{id}`, `GET /metadata`, `GET /$export`, etc.) backed by a transaction-Bundle NDJSON file. 4 server integration tests.
- 📡 **`scripts/post_to_fhir.sh`** — POSTs every transaction Bundle from an NDJSON file to a configurable FHIR endpoint (defaults to the public HAPI FHIR test server).
- 📖 **README — embedded viewers** — collapsible `<details>` blocks with inline previews of the sample Bundle / CSV / validation report, plus links to the GitHub built-in JSON viewer, Simplifier.net, and the HL7 Clinical FHIR Renderer.
- 📖 **README — FHIR endpoints table** — maps every emitted resource type to its canonical REST endpoint and demonstrates spinning up the local demo server + POSTing to a remote one.
- 📖 **README — three explicit clinician-curation paths**: (1) tell the maintainer agent; (2) open an issue with the Clinical curation template; (3) submit a PR. Lists which files map to which kind of change.

## [0.3.0] — 2026-05-12

### Added
- 🇹🇷 **Turkish localization**: Patient.name (first + last drawn from cohort-realistic Turkish distributions), Patient.address with TR city + ISO 3166-2 province codes, Patient.communication set to `tr`.
- 🩺 **ICD-10 codes** for every comorbidity Condition, emitted alongside SNOMED CT.
- 🌐 **Multilingual displays**: every Condition's `code.text` includes both English and Turkish strings; SNOMED display is the English clinical preferred term.
- 📊 **`syntha validate`** CLI — Kolmogorov–Smirnov per continuous column, Wasserstein distance, correlation-matrix Frobenius diff, binary-prevalence absolute error. Outputs JSON report.
- 🖼️ **Distribution / correlation / prevalence plots** auto-generated from a fitted model and committed under `docs/figures/`.
- 📁 **Sample synthetic output** (100 episodes, full FHIR bundles, validation report) committed to `examples/sample_output/`.
- 📝 **CHANGELOG.md, CONTRIBUTING.md, ROADMAP.md** added.
- 🤖 **GitHub Actions CI**: pytest on Python 3.10 → 3.13 on every push and PR to `main`.
- 📚 **README** rewritten with sections, emojis, plots, embedded example output, and explicit use cases (training-data augmentation, healthy-control cohort for bioinformatics studies, EHR-pipeline integration testing).

### Changed
- LICENSE copyright holder is now **Ariorad Moniri** (was "Ario Moniri" in v0.1).
- `fhir.export` now emits `HumanName`, `Address`, `communication`, and ICD-10 + SNOMED dual coding on every relevant resource.

### Notes
- The training cohort represents **Turkish healthy adults** (anonymized retrospective EHR episodes). Synthetic output therefore reflects Turkish-cohort distributions — disease prevalence is *lower* than Turkish national averages (TÜİK) because the source is pristine-healthy episodes by construction.
- Source CSVs and full trained-model pickles are gitignored and never committed.

## [0.2.0] — 2026-05-12

### Added
- Synthea-style clinical-pathway module framework with 9 modules: hypertension, diabetes, hyperlipidemia, thyroid, depression, anxiety, ischemic heart disease, asthma, COPD.
- FHIR resource builders: Encounter, MedicationRequest, Procedure, CarePlan.
- RxNorm code tables for module-emitted prescriptions.
- Longitudinal trajectory generator: sticky comorbidity flags, Gaussian drift on continuous labs, Poisson encounter counts over a configurable window.
- Trained-model registry with `ModelCard` (source sha256, n_train, schema, per-column summary statistics, top-K Spearman correlations).
- 12 new tests (modules, longitudinal, registry).

### Changed
- `episode_to_bundle` walks the module registry for every active comorbidity flag and merges emitted resources into the transaction Bundle.
- Pipeline now persists every trained model with its model card.

## [0.1.0] — 2026-05-12

### Added
- Initial release.
- Gaussian copula generator with Spearman→Gaussian transform and nearest-PSD projection.
- Physiologic constraint filter (pulse pressure, Friedewald coherence, eGFR/creatinine).
- FHIR R4 transaction Bundle writer with LOINC (labs/vitals) and SNOMED CT (conditions) coding.
- CLI: `generate`, `fit`, `sample`, `fhir`.
- 13 unit + integration tests.
