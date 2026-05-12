# 🗺️ syntha roadmap

A staged plan for taking syntha from a working Gaussian-copula + Synthea-style hybrid to a fully calibrated, publication-grade Turkish synthetic patient generator.

Legend: ✅ shipped · 🟡 in progress · ⬜ planned · 🟣 needs clinician (medical doctor) curation

## v0.1 — Data-driven core ✅ (commit `25a1e7e`)

- ✅ Gaussian copula with Spearman→Gaussian conversion, nearest-PSD projection
- ✅ Empirical marginals (continuous via ECDF, binary via Bernoulli)
- ✅ Independent column-wise missingness model
- ✅ Physiologic constraints: pulse pressure ≥ 20, Friedewald coherence, eGFR/creatinine consistency
- ✅ FHIR R4 export (Patient + Observation + Condition) with LOINC and SNOMED codes
- ✅ CSV output matching input schema
- ✅ click-based CLI

## v0.2 — Hybrid (B) clinical-pathway layer ✅ (commit `fbd8555`)

- ✅ 9 Synthea-style modules (HTN, DM, hyperlipidemia, thyroid, depression, anxiety, IHD, asthma, COPD)
- ✅ Encounter / MedicationRequest / Procedure / CarePlan FHIR resources
- ✅ RxNorm code table for emitted prescriptions
- ✅ Longitudinal trajectory generator (sticky flags, lab drift, Poisson encounter counts)
- ✅ Trained-model registry with ModelCard (source sha256, n_train, marginals, top correlations)
- ✅ 25 passing unit + integration tests

## v0.3 — Turkish localization 🟡 (this release)

- 🟡 Turkish HumanName (cohort-realistic first / last name distributions)
- 🟡 Turkish Address (Patient.address with TR city + province codes)
- 🟡 ICD-10 codes alongside SNOMED for every Condition
- 🟡 Multilingual displays: every clinical concept emits both English and Turkish text
- 🟡 Patient.communication includes `tr` as the preferred language
- 🟡 Documentation: explicit statement that the cohort represents Turkish adults

## v0.4 — Validation + sample output 🟡 (this release)

- 🟡 `syntha validate` — per-column KS test, Wasserstein distance, correlation-matrix Frobenius diff
- 🟡 Sample synthetic output (100 episodes, full FHIR) committed to `examples/sample_output/`
- 🟡 Distribution-comparison plots (PNG) generated and embedded in README

## v0.5 — Project polish + CI 🟡 (this release)

- 🟡 GitHub Actions: pytest matrix on Py 3.10–3.13
- 🟡 CHANGELOG following [Keep a Changelog](https://keepachangelog.com/) + SemVer
- 🟡 CONTRIBUTING.md (including clinician-curation workflow)
- 🟡 ROADMAP.md (this file)
- 🟡 LICENSE updated to "Ariorad Moniri"

## v0.6 — Hand curation 🟣 needs medical doctor (Dr. Moniri)

- 🟣 Calibrate disease prevalence per module to Turkish national stats (TÜİK/TURKSTAT)
- 🟣 Review and accept/reject the default first-line drug per module (some Turkish guidelines differ from international, e.g. perindopril is widely used as a first-line ACEi)
- 🟣 Review the comorbidity → drug class mappings (any locally unusual choices? e.g. nebivolol popularity)
- 🟣 Author 4–6 extra modules for high-prevalence conditions not in the source flags (CKD staging, MAFLD, anemia, vitamin B12 deficiency — relevant given the lab columns present)
- 🟣 Verify Turkish display strings match clinical-Turkish convention rather than literal translation
- 🟣 Sanity-check the ICD-10 codes against TR-specific clinical coding practice

## v0.4 — Mixed-type correlation fix 🟡 (next)

The current copula uses **Spearman rank correlation** as the input to the Gaussian copula parameter via the standard `ρ = 2 sin(π ρ_s / 6)` transform. That's exact for **continuous–continuous** pairs but **systematically attenuates** correlations involving binary columns (massive ties bias rank correlation toward 0). After fitting, signs are preserved (since v0.3.2) but magnitudes shrink ~50% on continuous↔binary and ~65% on binary↔binary pairs.

- 🟡 Switch to **polyserial correlation** for binary↔continuous pairs.
- 🟡 Switch to **tetrachoric correlation** for binary↔binary pairs.
- 🟡 Validate against the same `pristine_tolerant_episodes.csv` source — target: shrinkage ratio ≥ 0.9 (currently ~0.5).
- 🟡 Reference: Genest & Nešlehová (2007), *A primer on copulas for count data*.

## v0.7 — Advanced generative models ⬜

- ⬜ Optional CTGAN/TVAE backend behind a `--engine ctgan` flag (heavier dependency, similar API)
- ⬜ Conditional generation: "give me 1000 synthetic 60+ year old males with DM" via SDV-style conditioning
- ⬜ Differential-privacy guarantees (DP-CTGAN or DP synthetic data)

## v0.8 — Disease-progression state machines ⬜

- ⬜ True longitudinal state machines (Synthea PADM-style) for the four highest-impact chronic conditions
- ⬜ Time-to-event modeling for cardiovascular complications

## v0.9 — Benchmarks ⬜

- ⬜ Train a downstream risk model on synthetic data; evaluate on the held-out real test set
- ⬜ Publish a "train on synthetic, test on real" (TSTR) benchmark vs the source CSV split

## v1.0 — Stable release ⬜

- ⬜ All v0.6 hand-curation merged
- ⬜ Calibrated to TR national stats and validated on a holdout
- ⬜ Published to PyPI
- ⬜ Companion methods paper / data descriptor

## How to request curation work

If you're Dr. Moniri (or a collaborating clinician) and want to provide hand curation:

1. Pick a 🟣 task from v0.6.
2. Open an issue using the *Clinical curation* template (see `.github/ISSUE_TEMPLATE/clinical_curation.md` once added).
3. Either edit the relevant Python module / code table directly and open a PR, or paste the Turkish clinical guidance into the issue and request implementation.
