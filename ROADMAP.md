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

## v0.5 — Scientific-correctness sprint 🟡 (active)

Six items, each independently mergeable, closing the gap between what the May 2026 SOTA expects and what syntha currently does. Each item lists: the limitation it fixes, the reference, the implementation skeleton, and the success metric.

### 5.1 — Mixed-type correlation (polyserial + tetrachoric)

**Fixes:** continuous↔binary correlation magnitudes shrunk ~50%, binary↔binary ~65% (Limitation #1 in the v0.4.2 audit).

**Why:** The Spearman → Pearson conversion `ρ = 2 sin(π ρₛ/6)` is exact only when both marginals are continuous. For mixed pairs, the standard fix is to estimate the latent Gaussian correlation directly under the latent-threshold model.

**Method:**
- **Polyserial** for continuous↔binary pairs. Closed-form 2-step estimator: rank-transform the continuous variable to standard normal, threshold the binary, compute the Pearson correlation of the latent normal pair from the observed point-biserial correlation via `ρ_polyserial = r_pb · √(p(1-p)) / φ(Φ⁻¹(1-p))` where `r_pb` is the point-biserial. Then full ML refinement via 1-D numerical integration of the bivariate normal CDF.
- **Tetrachoric** for binary↔binary pairs. Compute the 2×2 contingency table; the tetrachoric correlation is the implied `ρ` of a latent bivariate normal that produces those four cell probabilities. Closed-form approximation (Bonett & Price 2005) or Cholesky-iterated ML.

**References:**
- Olsson (1982), *Maximum likelihood estimation of the polychoric correlation coefficient*, Psychometrika
- Größer (2022), *Copulae: An overview and recent developments*, WIREs Computational Statistics
- Genest & Nešlehová (2007), *A primer on copulas for count data*

**Implementation:** new module `src/syntha/generator/mixed_corr.py` (~150 LOC). Update `GaussianCopulaGenerator.fit()` to dispatch by pair-type. `R` reference is the `polycor` package — port the two-step algorithm.

**Success metric:** on the held-out 20% of source, the synthetic Spearman correlation magnitude for each continuous↔binary pair should be ≥ 0.9 × the source magnitude (currently ~0.5).

### 5.2 — Joint missingness model

**Fixes:** Missingness applied independently per column produces "Swiss cheese" patterns that don't match real EHR (Limitation #2).

**Method:** Train a separate Bernoulli MVN copula on the **missingness mask** `M_i = 1[column i is missing]`. Sample the mask first, then sample the value matrix from the conditional copula given the mask. The empirical evidence: in `pristine_tolerant_episodes.csv`, the four lipid-panel columns are missing together >95% of the time — a single binary "lipid panel ordered" indicator drives all four.

**Implementation:** new module `src/syntha/generator/missingness.py` (~120 LOC).

**Success metric:** on held-out source, the Jaccard similarity between the panel-co-missingness sets in synthetic vs source ≥ 0.85 (currently ~0.0 because each column missing independently).

### 5.3 — Differential privacy wrapper

**Fixes:** No formal privacy guarantee (Limitation #4).

**Method:** Add Gaussian noise calibrated to (ε, δ) to:
- Each empirical-quantile value before serializing the marginal
- Each Spearman/polyserial estimate before assembling the correlation matrix
- Each Bernoulli probability

Then project the noisy correlation matrix back to nearest PSD (we already do this).

**Reference:** [Frontiers in Digital Health 2025](https://www.frontiersin.org/journals/digital-health/articles/10.3389/fdgth.2025.1576290/full) shows DP-Gaussian-copula stays usable at ε ≈ 1.0.

**Implementation:** `syntha fit --epsilon 1.0` flag; ~80 LOC added to `copula.py`.

**Success metric:** at ε = 1.0, fidelity (max KS across continuous) ≤ 0.05; membership-inference ROC-AUC ≤ 0.55.

### 5.4 — Lab-panel grouping → FHIR `DiagnosticReport`

**Fixes:** Currently every lab is a standalone `Observation`. Real EHR consumers expect ordered-together labs to be grouped under a `DiagnosticReport` resource referring to the constituent `Observation`s.

**Method:** Hard-coded panel definitions:
- Lipid panel (LOINC `57698-3`): total chol + HDL + LDL + triglycerides
- CBC (LOINC `58410-2`): hemoglobin + WBC + platelets
- Basic metabolic panel (LOINC `24323-8`): glucose + creatinine + eGFR
- Hepatic function panel (LOINC `24325-3`): ALT + AST
- Iron studies (LOINC `24350-1`): ferritin
- Vitamin B12 (LOINC `2132-9` solo)

For each panel where ≥1 constituent observation is non-null, emit a `DiagnosticReport` whose `result` references the Observations and whose `effectiveDateTime` matches.

**Implementation:** new module `src/syntha/fhir/panels.py` (~100 LOC). Called from `fhir/export.py`.

### 5.5 — Lab time-series + intra-encounter vital trajectories

**Fixes:** Single snapshot per lab is unrealistic (the source `_latest` suffix proves there were historical values).

**Method:** For each non-null lab, generate 2–4 prior measurements over the preceding 6–24 months with AR(1)-style drift around the `_latest` value. Use lab-specific drift rates from clinical literature (eGFR declines ~1 mL/min/year normally; HbA1c noise σ ≈ 0.3% over 3 months).

For vitals within one encounter: emit 2–3 BP measurements 5 min apart (a typical clinical practice).

**Implementation:** extend `longitudinal.py` (~80 LOC additions).

### 5.6 — SynthEHRella benchmark integration

**Fixes:** No TSTR validation (Limitation #5).

**Method:** Use the standardized [SynthEHRella](https://github.com/chenxran/synthEHRella) framework:
1. 80/20 random split of source by `HASTA_ID`
2. Train syntha on the 80%, generate equal-sized synthetic dataset
3. Train a hypertension-risk model (logistic regression + XGBoost) on each
4. Score both on the held-out 20% real test set
5. Report ROC-AUC, Brier score, calibration plot

**Implementation:** new `benchmarks/synthehrella_run.py` (~150 LOC). Output goes to `benchmarks/results/v0.5.json` and is regenerated on each release.

**Success metric:** TSTR ROC-AUC within 0.02 of TRTR (train-on-real, test-on-real).

---

## v0.4 — Mixed-type correlation fix 🟢 (subsumed by v0.5.1 above)

## v0.5 — Signed desktop installers ⬜

- ⬜ Apple Developer ID notarization for the `.dmg`
- ⬜ Microsoft Authenticode signing for `-setup.exe`
- ⬜ AppImage signature
- ⬜ Auto-update via Tauri's updater plugin

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
