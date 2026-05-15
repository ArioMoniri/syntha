# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.7](https://github.com/ArioMoniri/syntha/compare/v0.5.6...v0.5.7) (2026-05-15)


### Features

* **app:** in-app **Collaborate** panel — pulls live `help-wanted-clinician`, `help-wanted-dev`, and `help-wanted-data` issues from the GitHub API and lets contributors claim a task with their GitHub handle. No backend: GitHub IS the platform (identity = handle, tasks = issues, claiming = pre-filled comment). 15-min `localStorage` cache so the panel stays useful offline.
* **app:** "claim" modal — copy-to-clipboard of the pre-filled comment + one-click deep-link to the issue.
* **docs:** README rewritten — strictly *what syntha is* and *how to use it* (install, quick start, output schema, CLI reference, fidelity, plots). All forward-looking content moved out.
* **docs:** `ROADMAP.md` consolidated — no duplicate v0.4 / v0.5 sections; single shipped log + queued plan; the 🟣 clinical-curation items live here.
* **docs:** new `COLLABORATE.md` — live list of clinician + dev + data tasks, who can help with what, and how to claim.
* **repo:** new labels — `help-wanted-clinician` (#8b5cf6), `help-wanted-dev` (#0e8a16), `help-wanted-data` (#1d76db). Bootstrapped via the new `seed-collab-labels.yml` workflow so forks get them too.
* **repo:** new issue templates for `help-wanted-dev` and `help-wanted-data`. The existing clinical-curation template retargeted from the old `clinical-curation` label to the new `help-wanted-clinician`.
* **repo:** 12 seed issues opened across the three categories so the in-app panel has content from launch.
* **plots:** `docs/figures/{distributions,correlations,prevalence}.png` regenerated from a fresh v0.5.6 strict-cohort sample (n = 500, seed = 42).


### Bug fixes

* **ci(cross-platform):** the `macos-latest` runner's brew-installed `rustup-init` shim intercepts every rustup subcommand — even `rustup which cargo` errors with *"unexpected argument 'which' found"*. Switch to the official `rustup.rs` one-liner installer into `$HOME/.cargo` and call cargo by its absolute path in every later step. Removed `dtolnay/rust-toolchain@stable` since it can't get past the shim on macOS.


## [0.5.6](https://github.com/ArioMoniri/syntha/compare/v0.5.0...v0.5.6) (2026-05-15)


### Features

* **app:** longitudinal-mode toggle in the desktop GUI — synthesizes multiple encounters per patient with shared HASTA_ID, age-advance, and 5%-SD multiplicative Gaussian drift on labs/vitals.
* **app:** IDs in every downloaded CSV — `RF_EPISODE2`, `HASTA_ID`, `episode_date` are now synthesized client-side (mirrors `pipeline._generate_ids_and_dates` on the Python side).
* **app:** preview now shows all columns × 50 rows with a sticky header and horizontal+vertical scroll.
* **pipeline:** `PipelineConfig.include_curation_flags` (default **False**) — strips 29 source-pipeline curation flags (`pristine_*`, `berturk_*`, drug-safety, `rf_*`) from the default CSV. They're training metadata, not clinical observations, and most are degenerate (always 0 or always 1) in the pristine cohort. FHIR `FamilyMemberHistory` still consumes `rf_kanser` / `rf_kronik_hastalik` before the filter runs.
* **cli:** `--curation-flags / --no-curation-flags` switch on `syntha generate`.
* **model JSON:** bumped to `syntha-copula-v2`. Adds `date_lo` / `date_hi` (so the desktop app can synthesize `episode_date` without the source CSV) and `curation_columns` (Python ↔ TS share a single source of truth). v1 bundles still load (lazy fallback).


### Bug fixes

* **ci:** `cargo check` on macOS runner — switch to `rustup run stable cargo` to bypass the `rustup-init` shim that started intercepting bare `cargo` invocations on the `macos-latest` image.


### Tests

* net-new `tests/test_cli.py` (closes the v0.5 architecture-review gap).
* `tests/test_pipeline.py` — curation-flag default drop, opt-in roundtrip, v2-metadata roundtrip.


## [0.5.0](https://github.com/ArioMoniri/syntha/compare/v0.4.2...v0.5.0) (2026-05-15)


### Features

* **app:** Turkish (tr-TR) UI alongside English (i18n) ([cb86ba5](https://github.com/ArioMoniri/syntha/commit/cb86ba55ff3774961240977ab20d0b8be7c835cd))
* **cli:** conditional sampling via AST-validated rejection ([c26e0b9](https://github.com/ArioMoniri/syntha/commit/c26e0b966a1cfe2691f2853a00cf0b0ae9297cf9))
* **clinical:** G3 reference ranges (sex-specific normal intervals) ([a4eb8ec](https://github.com/ArioMoniri/syntha/commit/a4eb8ecffd2723a7f0d69f813316c852374b5d49))
* **dashboard:** GitHub Pages benchmark dashboard at ariomoniri.github.io/syntha ([8511868](https://github.com/ArioMoniri/syntha/commit/851186886c9456d04a71299ea384a69711f4e7a9))
* **v0.5:** joint missingness + lab time-series + privacy CI + clinical extras ([1470448](https://github.com/ArioMoniri/syntha/commit/14704487127bc0af924587eb257b6cff4204703e))


### Documentation

* archive v0.4.2 release notes under .github/ ([c341fdd](https://github.com/ArioMoniri/syntha/commit/c341fdd4f692e7231674bfea84ed3a8ac036ea49))
* **community:** enable Discussions + all-contributors recognition ([4ee5c41](https://github.com/ArioMoniri/syntha/commit/4ee5c419c0007cd4d658e56609579543a9118ab8))
* **readme:** add Contributors table + Community section ([82ff1e2](https://github.com/ArioMoniri/syntha/commit/82ff1e2c61589956667337687e6c88e2e577e6f7))
* **release:** v0.5.0 release notes + CHANGELOG promote + privacy-audit workflow ([ea03f40](https://github.com/ArioMoniri/syntha/commit/ea03f409bbbec04cce7372c6c8808de95b2c4f43))

## [Unreleased]

## [0.5.0] — 2026-05-14

### Added — v0.5 scientific-correctness sprint (signed off by CMO + ML engineer in docs/REVIEW_v0.5_FINAL.md)

- 🧮 **5.2 Joint + comorbidity-conditional missingness** (`src/syntha/generator/missingness.py`, 4 tests). Fits P(missing | comorbidity_flags); at sample time, panel co-missingness (lipid, CBC, CMP) is propagated with 85% probability. Fixes the Swiss-cheese pattern from v0.4 column-independent missingness.
- ⏱️ **5.5 Lab time-series + intra-encounter BP** (`src/syntha/longitudinal_labs.py`, 10 tests). AR(1) trajectory of 2–4 prior measurements per lab over 6–24 months with column-specific biological variation (eGFR 6% CV + 1%/yr decline, HbA1c 0.2–0.5% σ, Hb 2% CV, …) drawn from Westgard QC literature. Plus 3 intra-encounter BP measurements ~5 min apart with the standard white-coat decline pattern.
- 🛡️ **G2 Privacy audit** (`src/syntha/privacy.py`, 5 tests, `.github/workflows/privacy-audit.yml`). Stadler 2022 nearest-neighbor membership-inference attack + logistic-regression attribute-inference attack. CI gates on MIA AUC ≤ 0.60 per SynQP threshold — formal evidence the model doesn't memorize training data.
- 🧾 **Charlson CCI as FHIR `RiskAssessment`** (`src/syntha/fhir/clinical_extras.py`). LOINC 75618-7 with qualitative-risk binning + 10-year-mortality probability estimate.
- 🧠 **PHQ-9 + GAD-7 + FamilyMemberHistory** (`src/syntha/fhir/clinical_extras.py`, 7 tests). PHQ-9 (LOINC 44261-6) for `Depresyon`-flagged patients, GAD-7 (LOINC 70274-6) for `Anksiyete`-flagged, FamilyMemberHistory for `rf_kanser` + `rf_kronik_hastalik` family-risk flags.

### Added earlier in the sprint

- 🧮 **Polyserial + tetrachoric correlation** (`src/syntha/generator/mixed_corr.py`, 14 tests). The Gaussian copula now uses the **right estimator per pair type**:
  - continuous↔continuous: Kruskal `ρ = 2 sin(π ρₛ/6)` (unchanged)
  - continuous↔binary: **polyserial** (Olsson 1982 two-step) — recovers latent correlation directly via `ρ = r_pb · √(p(1-p)) / φ(τ)`
  - binary↔binary: **tetrachoric** — finds the latent ρ such that the bivariate-normal CDF reproduces the observed 2×2 cell probabilities, solved by bisection
  - dispatch via `GaussianCopulaGenerator.fit(..., corr_method="mixed")` (now default; `"spearman"` preserved for v0.4 reproducibility)
- 🩺 **Synthetic-patient FHIR marker** (G1 from medical-officer review): every Patient resource now carries the standard `HTEST` tag (terminology.hl7.org/CodeSystem/v3-ActReason) **plus** a `syntha-copula` source tag.
- 🧪 **Lab-panel DiagnosticReport grouping** (`src/syntha/fhir/panels.py`, 3 tests). Five panels emitted when their constituent Observations exist.
- 🎯 **Conditional sampling CLI** (`syntha sample-conditional --condition "age > 60 & DM_Tum == 1"`, 6 tests). AST-validated safety.
- 🌐 **Tauri Turkish UI** — full TR locale alongside English, locale switcher, persistent preference.
- 🩹 **G3 Clinical reference ranges** (`src/syntha/reference_ranges.py`, 9 tests). Sex-specific normal intervals for 16 labs.

### Engineering infrastructure (Tier 1+2+3+4 workflow roadmap)

- 🤖 **Dependabot** for GitHub Actions / pip / npm / cargo
- 🛡️ **CodeQL** SAST on Python + TypeScript
- 📋 **PR template** + bug/feature issue templates + CODEOWNERS
- 🪝 **pre-commit hooks** (ruff + black + safety set) + ruff config in `pyproject.toml`
- 📊 **codecov** coverage reporting
- 🧪 **HAPI FHIR validator** in CI on bundle changes
- 📜 **SBOM** generation (SPDX-JSON) per release via `anchore/sbom-action`
- ⚡ **Swatinem rust-cache** — 6 min → 2 min macOS Tauri build
- 🚀 **release-please** automation: PR-driven semver + CHANGELOG
- 💬 **GitHub Discussions** enabled, **all-contributors** config
- 🐳 **Docker image** at `ghcr.io/ariomoniri/syntha:latest`, multi-platform (amd64+arm64)
- 📦 **PyPI publish workflow** with **trusted-publisher** OIDC (no token in secrets)
- 🪟 **Windows Authenticode signing** infrastructure (gated on `WINDOWS_CERTIFICATE`)
- 📈 **GitHub Pages benchmark dashboard** at https://ariomoniri.github.io/syntha
- 🏛️ **CITATION.cff** so the repo shows a "Cite this repository" button

### Test totals

**96/96 tests passing** (was 51 at v0.4.2).

### Notes

The strict cohort's `app/src/model_strict.json` was refit with the new mixed-correlation method; size unchanged (173 KB), correlations materially better. Tolerant cohort needs a fresh source CSV upload to refit (tetrachoric attacks the binary↔binary correlations that the strict cohort can't exercise — strict has ~0 prevalence on all 20 comorbidity flags by design).

## [0.4.0] — 2026-05-13 (Synthea-inspired hybrid baseline, see prior log below)

(Pre-0.5 entries unchanged from prior CHANGELOG; see commit history for v0.4.x details.)

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
