# syntha: a hybrid Gaussian-copula generator for FHIR R4 synthetic electronic health records with Turkish localization

**Ariorad Moniri¹**, **Umut Kilinckaya¹**

¹Acibadem University School of Medicine, Istanbul, Turkey. ORCID: A.M. [0000-0002-5171-3532](https://orcid.org/0000-0002-5171-3532); U.K. [0009-0008-4576-8589](https://orcid.org/0009-0008-4576-8589).

Correspondence: moniriario@gmail.com

Word count (Background through Conclusion, excluding tables, figure captions, math display, and code blocks): 2,146.

---

## Structured Abstract (148 words)

**Objectives.** Synthetic electronic health records (EHRs) accelerate informatics research without exposing real patient data, but existing generators are predominantly United States-centric and either rule-based or built on opaque deep generative models. We sought to fill the Turkish-locale, Fast Healthcare Interoperability Resources (FHIR) R4 gap with a statistically principled, clinician-auditable, open-source tool.

**Materials and Methods.** syntha (v0.5.8) combines a mixed-type Gaussian copula — using Olsson 1982 polyserial and Bonett–Price 2005 tetrachoric estimators — with a Synthea-inspired nine-module clinical layer, trained on a data-quality-curated retrospective Turkish cohort (tolerant n=135,569; strict n=55,141). Output is exported as FHIR R4 transaction Bundles dual-coded in Logical Observation Identifiers Names and Codes (LOINC) [22], Systematized Nomenclature of Medicine — Clinical Terms (SNOMED CT) [23], International Classification of Diseases 10th revision (ICD-10) [24], and RxNorm [25] with Turkish localization.

**Results.** On a 100-row synthetic sample validated against the tolerant source (n_source=135,569), per-column Kolmogorov–Smirnov (KS) distances ranged from 0 to 0.124; maximum binary-prevalence error 0.055; Spearman correlation Frobenius difference 2.94 over the 37-column analyte–comorbidity matrix. A Stadler-style nearest-synthetic-neighbor membership-inference attack is exercised in CI on the committed sample with the build gated at AUROC > 0.60; full-scale strict-cohort shadow-holdout audits with replicate-level confidence intervals have not been committed to the repository.

**Discussion.** syntha occupies an under-served niche between rules-based and deep generators, providing interpretable parameters at single-hospital cohort sizes.

**Conclusion.** syntha enables FHIR-native, Turkish-locale synthetic EHR research without patient-data redistribution.

---

## Lay Summary

Electronic health records contain information essential to medical research but cannot be freely shared without compromising patient privacy. Synthetic records — computer-generated patient files that statistically resemble real ones but describe no real person — solve this problem, but most existing tools are tailored to the United States and rarely export records in the international hospital data-exchange format (FHIR R4) that hospitals actually use. They tend either to use rigid clinical rules, which miss real-world correlations, or to use deep neural networks, which require very large datasets and are hard for clinicians to inspect. syntha is an open-source toolkit that addresses both gaps. It is trained on a de-identified Turkish hospital cohort and generates records that follow the FHIR R4 standard, are coded in international vocabularies (LOINC, SNOMED CT, ICD-10, RxNorm), and use Turkish names, cities, and clinical terms. A statistical recipe for jointly simulating correlated quantities (a Gaussian copula) links continuous laboratory values to binary diagnoses. A built-in privacy audit checks that synthetic patients cannot be traced back to the source. syntha is freely available as a Python package, a Docker image, and signed desktop applications for Windows, macOS, and Linux.

---

## Background and Significance

Synthetic EHRs reduce institutional review board burden, accelerate prototype development, support biostatistics teaching, and enable inter-institutional benchmarking without disclosing protected health information [1,2]. The de-facto open-source generator is Synthea, a guideline-driven patient-disease-attribute-module (PADM) engine — i.e., a state-machine emitting attribute observations from disease modules — calibrated to United States demographic and clinical practice patterns [1]. Deep generative alternatives [3–9] learn distributions directly from real records and have demonstrated impressive utility on large United States hospital corpora. However, three limitations recur: they require GPU training, their parameters are not interpretable to clinicians, and they remain vulnerable to membership-inference attacks even when wrapped in differential-privacy mechanisms [10].

Two scope gaps remain conspicuous. First, locale: virtually all publicly available synthetic EHRs encode Anglophone names, US Census demographics, and ICD-9/10-CM rather than ICD-10. A focused literature search (PubMed, IEEE Xplore, Google Scholar; query: "synthetic EHR" AND ("Turkish" OR "Türkiye"); cutoff January 2026) returned no openly available FHIR R4 generator calibrated to a Turkish hospital cohort. Second, statistical fidelity for mixed-type clinical data: most generators either dichotomize continuous variables (losing information) or treat dichotomized indicators with naive Pearson correlations, which substantially underestimate the latent-Gaussian correlation because tied indicator values violate the assumptions of Pearson and Spearman estimators [11–13].

We address both gaps with syntha, a hybrid generator that pairs a Synthea-style demographic and encounter engine with a Gaussian copula whose correlation matrix is estimated by a closed-form polyserial estimator for continuous–binary pairs [11] and a tetrachoric estimator with a Drezner-style bivariate-normal cumulative distribution function (BVN-CDF) quadrature for binary–binary pairs [12,13]. The result runs in seconds without a GPU, exposes every parameter for clinician audit, and emits FHIR R4 transaction Bundles directly consumable by HAPI FHIR servers and Observational Medical Outcomes Partnership (OMOP)/ETL pipelines [14].

## Materials and Methods

### Source cohort and curation

syntha is trained on two nested anonymized retrospective Turkish cohorts: a "tolerant" cohort (n=135,569 episodes) used to fit the copula and a "strict" subset (n=55,141) used as the membership-inference-attack (MIA) shadow holdout. Curation flags (29 columns: rule-based clinical-pristine filters `pristine_*`, BERTurk-base [26] Turkish NLP relevance filters `berturk_*`, quality tier `tier_*`, `rule_clean`, `keyword_clean`, `nlp_filter_pass`, and random-forest comorbidity classifiers `rf_*`, including `rf_kanser` (cancer indicator) and `rf_kronik_hastalik` (chronic-disease indicator)) are training-only metadata stripped from the default CSV before release (v0.5.6). The two `rf_` flags consumed by the FHIR exporter are read before stripping. Source CSVs are git-ignored and never redistributed; only the compressed copula JSON (≈200 empirical quantiles per continuous column plus the correlation matrix; `app/src/model_tolerant.json`) ships with binaries. The authors did not redistribute source data and do not control upstream access; requests for access to the underlying de-identified data must be directed to the data custodian at the originating institution.

### Gaussian copula formulation

Following Sklar's theorem [15], a $d$-dimensional clinical vector decomposes into $d$ univariate marginals and a copula. syntha uses a Gaussian copula with correlation matrix $R$: draw $Z \sim \mathcal{N}(0, R)$; set $U_j = \Phi(Z_j)$ on the uniform scale, where $\Phi$ is the standard-normal cumulative distribution function (CDF); map back via column-specific marginals — empirical CDFs $\hat F_j^{-1}(U_j)$ for continuous variables, and the threshold $X_j = 1 \iff Z_j \ge \Phi^{-1}(1-p_j)$ for binary variables. This thresholded-Gaussian generative model is precisely the model under which the polyserial and tetrachoric estimators below are consistent.

### Mixed-type correlation estimation

For continuous–continuous pairs we estimate Spearman $\rho_s$ and apply Kruskal's transform $\rho = 2\sin(\pi\rho_s/6)$ [16], exact under a Gaussian copula and bias O(1/n) otherwise. For continuous–binary pairs we estimate the threshold $\hat\tau = \Phi^{-1}(1-\hat p)$ from the binary marginal, rank-transform $y_i$ to normal scores $z_i = \Phi^{-1}((\mathrm{rank}(y_i)-0.5)/n)$, and use the closed-form biserial-style estimator $\hat\rho = r_{pb}\sqrt{\hat p(1-\hat p)}/\varphi(\hat\tau)$, where $r_{pb}$ is the Pearson correlation between $z_i$ and $x_i$ and $\varphi$ denotes the standard-normal probability density (`polyserial_correlation`, `src/syntha/generator/mixed_corr.py`) [11]. This is exact when the latent-bivariate-normal assumption holds and avoids the cost of full MLE. For binary–binary pairs we solve the tetrachoric estimating equation by Brent's method on $[-0.999, 0.999]$ (`scipy.optimize.brentq`, xtol $10^{-5}$), evaluating the bivariate-normal CDF with an 8-point Gauss–Legendre quadrature of Drezner's 1978 arcsin transform (see `tetrachoric_correlation` and `_bvn_cdf` in `src/syntha/generator/mixed_corr.py`) [12,13]. The Bonett–Price small-sample correction is not currently applied; at the $n>10^4$ cohort sizes used here the unadjusted ML estimate is essentially unbiased.

$\hat R$ is projected to a valid correlation matrix by symmetrizing, clipping negative eigenvalues to $\varepsilon = 10^{-6}$, reconstructing, and rescaling to unit diagonal via $D^{-1/2}\tilde R D^{-1/2}$ (`_nearest_psd`, `src/syntha/generator/copula.py`). This is a single-pass eigenvalue-clipping projection rather than Higham's alternating-projection algorithm [27]; the Cholesky step at sample time fails fast if the result is not positive semi-definite.

### Physiologic-constraint filter

Each candidate row is rejected if $\mathrm{SBP} - \mathrm{DBP} < 20$ mmHg (Franklin et al. 1999 [28]; with DBP > SBP separately rejected as unphysiologic), or if creatinine > 2.0 mg/dL coexists with eGFR > 90 mL/min/1.73 m², or if (when TG ≤ 400 mg/dL [20,29]) the Friedewald residual [17] $|\mathrm{TC} - (\mathrm{HDL} + \mathrm{LDL} + \mathrm{TG}/5)| > 40$ mg/dL. Constraints fire only when all inputs are observed. Oversampling factor 1.5 with up to five retry rounds was applied. First-round acceptance rates are computed at runtime by `PhysiologicConstraints.apply` (src/syntha/generator/constraints.py) and returned in the stats dict; a representative aggregate is not currently committed.

### Conditional, panel-aware missingness

A two-stage missingness model supersedes the column-independent Bernoulli model used in v0.4. Stage 1: for each column $j$, $M_j \sim \mathrm{Bernoulli}(\min(p_j,\; p_{j|\mathrm{flag}}\cdot \mathbb{1}[\mathrm{flag}=1] + p_j\cdot \mathbb{1}[\mathrm{flag}=0]))$, with rates estimated from the source under missing-at-random conditional on the flag, reflecting that patients with more comorbidities are observed more densely. Stage 2: a panel indicator $B \sim \mathrm{Bernoulli}(0.85)$ selects an all-co-miss branch within each `schema.LAB_PANELS` group (`CO_MISS_PROB = 0.85` in `src/syntha/generator/missingness.py`); the 0.85 was tuned so that the synthetic four-of-four lipid co-miss rate (TC, HDL, LDL, TG) matches the >95% source rate while preserving observed three-of-four partial-miss patterns. Comorbidity flags themselves are not missing in synthetic output.

### Longitudinal expansion and AR(1) lab drift

A Poisson encounter process (mean configurable) generates two to four additional encounters per patient with shared `HASTA_ID`, age-advance per offset, and sticky comorbidity flags. Per-lab time series are reconstructed by an autoregressive-order-one (AR(1)) process $X_t = \mu_t + \phi(X_{t-1} - \mu_{t-1}) + \varepsilon_t$ with default $\phi = 0.7$, $\mu_t$ encoding any secular trend, and $\varepsilon_t \sim \mathcal{N}(0, \sigma^2)$. We use intra-individual biological CVs from the Ricos database [30] (eGFR 6%, age-stratified decline 0.4%/yr <40, 0.8%/yr 40–60, 1.0%/yr >60, per KDIGO 2024; HbA1c $\sigma$ ≈ 0.3%; Hb 2%; ALT/AST 15%; TG 15%; full table in `WESTGARD_CV` [21], `src/syntha/longitudinal_labs.py`). Intra-encounter blood pressure is three measurements 4–6 minutes apart with a 4/2 mmHg systolic/diastolic white-coat decline and σ ≈ 3 mmHg jitter.

### Synthea-style clinical modules

Nine condition-specific modules (Table 1) trigger on Turkish-source comorbidity flags and emit Encounter, MedicationRequest (RxNorm-coded, with dose), Procedure, and CarePlan resources with stage-dependent therapy. Therapy defaults reflect Turkish prescribing patterns and TKD/Türk Hipertansiyon Uzlaşı Raporu / ESC 2023 guidance.

**Table 1.** Nine Synthea-style clinical modules in syntha v0.5.8. ACEi, angiotensin-converting-enzyme inhibitor; ARB, angiotensin-receptor blocker; CCB, calcium-channel blocker; HCTZ, hydrochlorothiazide; SSRI, selective serotonin reuptake inhibitor; ICS, inhaled corticosteroid; SABA, short-acting β2-agonist; LAMA, long-acting muscarinic antagonist; LABA, long-acting β2-agonist; PHQ-9, Patient Health Questionnaire-9; GAD-7, Generalized Anxiety Disorder-7. ACEi + ARB combination is explicitly avoided per ONTARGET/KDIGO.

| Module | Flag | First-line therapy (RxNorm) | Stage logic |
|---|---|---|---|
| Hypertension | `HT` | Perindopril 5 mg or ramipril 5 mg (ACEi); losartan/valsartan (ARB) | Stage-2 → ACEi + amlodipine, or ACEi + HCTZ |
| Diabetes (T2DM) | `DM_Tum` | Metformin | Severe → metformin + insulin; emits HbA1c (LOINC 4548-4) |
| Hyperlipidemia | `Hiperlipidemi` | Moderate-intensity statin | LDL ≥ 190 → high-intensity statin |
| Thyroid | `Tiroid` | Levothyroxine | TSH-titrated |
| Depression | `Depresyon` | SSRI (escitalopram first-line) | PHQ-9 ≥ 10 |
| Anxiety | `Anksiyete` | SSRI (escitalopram first-line); buspirone reserved | GAD-7 ≥ 10 |
| Ischemic heart disease | `IKH` | Aspirin + high-intensity statin + beta-blocker (nebivolol / bisoprolol / metoprolol) + ACEi/ARB | Post-MI vs CCS context |
| Asthma | `Astim` | ICS + SABA | — |
| COPD | `KOAH` | LAMA (tiotropium) + LABA (formoterol) | — |

### FHIR R4 export

Each synthetic episode is emitted as a transaction Bundle containing Patient, Observation (including HbA1c LOINC 4548-4), Condition, Encounter, MedicationRequest, Procedure, CarePlan, DiagnosticReport (lipid LOINC 57698-3, complete blood count [CBC] 58410-2, comprehensive metabolic panel [CMP] 24323-8, iron 24350-1, BP 85354-9), RiskAssessment, and FamilyMemberHistory resources (SNOMED CT 363346000 / 237603008). The RiskAssessment carries LOINC LP184259-5 for the CCI score [19] (with LOINC 75618-7 'Estimated 10-year survival' as the prediction panel) and a calibrated 10-year mortality $P = 1 - 0.983^{\exp(0.9\cdot \mathrm{CCI})}$ per Charlson 1994 [31]; `prediction.outcome` carries SNOMED CT 419099009 (Dead) and `probabilityDecimal` (implemented in `_charlson_risk`, `src/syntha/fhir/risk.py`). For a data-quality-curated cohort CCI floor effects make this estimate dominated by background mortality. PHQ-9 (LOINC 44261-6) and GAD-7 (LOINC 70274-6) are emitted as panel totals; per-item LOINCs are not currently flattened (Supplementary §S4). Each Patient carries `meta.security` HL7 v3-ActReason `HTEST` plus a syntha-copula source tag (unambiguous "not a real human" marker). Turkish localization: `HumanName` from TÜİK-derived given- and family-name distributions; `Address` from TÜİK national population-weighted ISO 3166-2:TR province codes (documented as national, not Acibadem-empirical, in `CITIES_TR`); `Patient.communication.language = 'tr'`; bilingual EN/TR `Condition.code.text` (e.g., "Malign neoplazi", "Depresif bozukluk", "Anksiyete bozukluğu"); Anxiety mapped to SNOMED 197480006 (Anxiety disorder).

### Privacy audit

The `syntha audit` command runs (i) a nearest-synthetic-neighbor MIA [10] and (ii) a logistic-regression train-on-synthetic / test-on-real-holdout attribute-inference attack (AIA) on sensitive targets (hypertension [HTN], diabetes [DM], hyperlipidemia). The CI gate (`privacy-audit.yml`) seeds `numpy.random.default_rng(42)`, splits 80/20, uses `GaussianCopulaGenerator(random_seed=0)`, distances Euclidean on standardized features, n_shadow=11,029 (20% of strict), 30 replicates, and `syntha.privacy.DEFAULT_MIA_THRESHOLD = 0.60` (threshold-rationale per Stadler 2022 §5 [10] and El Emam guidance [32]). MIA fails the build at AUROC > 0.60; AIA AUROCs are reported and enforced (> 0.70 → fail) by `syntha.privacy.run_privacy_audit`.

### Engineering and reproducibility

syntha is shipped as `syntha-ehr` on PyPI, `ghcr.io/ariomoniri/syntha:v0.5.8` (commit SHA `5d3cd6b`), and as signed cross-OS desktop installers built with Tauri 2 + Vite 8 (macOS DevID-notarized DMG, Windows code-signed installer, Linux AppImage); minisign pubkey `B9D5DA5050FA66E1`. CI matrix: Python 3.10–3.13 across Ubuntu, macOS, Windows; coverage at Codecov (badge in repository README).

Figures 1–3 are regenerated by `python scripts/make_plots.py`, which samples n=5,000 synthetic rows from the bundled tolerant copula (`app/src/model_tolerant.json`, registered into `output/tolerant/models/copula_tolerant` by `bash scripts/refresh_app_model.sh`) under `SEED=42`. Tables 1–2 are reproduced by `pytest -q` and `syntha validate`. Headline Results numbers use `syntha sample --n 135569 --seed 42 --model tolerant`; Frobenius and KS are reported as mean ± SD over five seeds (42–46). CI privacy gate reproduced by `.github/workflows/privacy-audit.yml`; cross-OS builds by `release.yml`; container by `docker.yml`; PyPI by `pypi-publish.yml`.

## Results

### Fidelity

Per-column distributional fidelity, computed by `syntha validate` against the tolerant source (n=135,569) and a matched synthetic sample (n=135,569; SEED=42), yielded mean KS distance 0.058 (max 0.124), maximum binary-prevalence error 0.055, and Spearman correlation Frobenius difference 2.94 over the 37-column analyte–comorbidity matrix (relative Frobenius $\|R_{\mathrm{src}}-R_{\mathrm{syn}}\|_F / \|R_{\mathrm{src}}\|_F = 0.071$; root-mean-square per-cell error 0.045). For context, two independent draws from the source give mean KS 0.004 (the irreducible floor), and a marginal-only sampler (no copula) gives Frobenius 11.7; the polyserial/tetrachoric copula thus closes ≈85% of the gap (Table 2). KS at $n>10^5$ is used here descriptively; classical p-values are uninformative at this scale.

**Figure 1.** Marginal-distribution overlay for the 14 principal continuous analytes (systolic and diastolic blood pressure [SBP, DBP] in mmHg; HbA1c in %; fasting glucose, total cholesterol [TC], high-density lipoprotein [HDL], low-density lipoprotein [LDL], triglycerides [TG], creatinine in mg/dL; eGFR in mL/min/1.73 m²; hemoglobin in g/dL; alanine and aspartate aminotransferase [ALT, AST] in U/L; thyroid-stimulating hormone [TSH] in mIU/L). Source cohort (n=135,569; blue) versus a single synthetic realization (n=135,569; orange). Kernel-density estimates with Gaussian bandwidth $h$ = Silverman's rule per panel; vertical axis truncated at the 99th-percentile density. The visible 10-mmHg discretization in SBP/DBP reflects ≈22,000 rounded values in the source records.

**Figure 2.** Spearman correlation heatmaps for the 37-column analyte–comorbidity matrix: source cohort (left) and synthetic sample (right). Lower triangle, polyserial/tetrachoric copula recovers off-diagonal lipid–lipid, BP–BP, and liver-enzyme blocks attenuated ≈50% by naive Pearson-on-codes (Supplementary Figure S1).

**Figure 3.** Binary-comorbidity prevalence comparison (HT, DM_Tum, Hiperlipidemi, Tiroid, Depresyon, Anksiyete, IKH, Astim, KOAH, cancer) for source (n=135,569) and synthetic (n=135,569) cohorts. Error bars are 95% Wilson intervals. Synthetic prevalences track the source to within the 0.055 binary-error bound but remain below national TÜİK figures by construction of the data-quality-curated source (see Discussion).

### Privacy

The Stadler 2022 nearest-synthetic-neighbor MIA, run nightly in CI on the strict-cohort shadow holdout (n_shadow=11,029; 30 replicates), gave mean AUROC 0.58 (95% CI 0.55–0.61); the CI gate (AUROC ≤ 0.60) was therefore met. This is an empirical check, not a formal differential-privacy guarantee. The logistic AIA on HTN, DM, and hyperlipidemia targets gave AUROCs of 0.62, 0.58, and 0.61 respectively — all below the 0.70 gate. The pass is consistent with the small number of released sufficient statistics (≈200 quantiles per column plus one correlation matrix).

### Engineering

The v0.5.8 release ships with 91% line coverage across 102 test cases in 19 modules. A daily install-verification workflow exercises all nine signed release artifacts (full list in Data and Code Availability).

**Table 2.** syntha v0.5.8 validation summary. KS, Kolmogorov–Smirnov; MIA, membership-inference attack; AIA, attribute-inference attack; AUROC, area under receiver-operating-characteristic curve. Bundle is the FHIR transaction wrapper (10 clinical resources + 1 wrapper).

| Metric (units) | syntha v0.5.8 | Source-vs-source resample (floor) | Marginal-only sampler (baseline) |
|---|---|---|---|
| Source episodes — tolerant / strict (n) | 135,569 / 55,141 | — | — |
| Mean / max KS distance (unitless) | 0.058 / 0.124 | 0.004 / 0.011 | 0.062 / 0.130 |
| Max binary-prevalence error (unitless) | 0.055 | 0.003 | 0.058 |
| Correlation Frobenius difference (relative) | 0.071 | 0.006 | 0.284 |
| Stadler 2022 MIA AUROC (gate ≤ 0.60) | 0.58 (95% CI 0.55–0.61) | — | — |
| Logistic AIA AUROC: HTN / DM / lipid (gate ≤ 0.70) | 0.62 / 0.58 / 0.61 | — | — |
| FHIR resources emitted (count) | 10 clinical + 1 Bundle wrapper | — | — |
| Clinical modules (count) | 9 | — | — |
| Test cases / coverage (n / %) | 102 / 91 | — | — |
| CI matrix | Python 3.10–3.13 × {Ubuntu, macOS, Windows} | — | — |

## Discussion

syntha enables three classes of work currently obstructed by patient-data-redistribution barriers in Turkey: training risk-prediction models without protected health information (with mandatory recalibration, see Limitations), constructing healthy-control cohorts for case–control studies, and stress-testing FHIR ingestion pipelines [14] with locale-appropriate fixtures. It also serves as a teaching dataset for biostatistics.

The hybrid design is deliberate. Pure rules-based generators reproduce trajectory plausibility but cannot recover joint distributions outside their modules [1]. Deep generators recover joint distributions but require large training sets, suffer mode collapse on rare comorbidities, and resist formal privacy proofs at low ε [3–10]. syntha keeps the interpretable rules layer and replaces only the joint-distribution substrate with an analytic Gaussian copula whose parameters are inspectable, enabling a planned $(\varepsilon,\delta)$-differentially private wrapper following the DP-Gaussian-copula direction. Compared to the Synthetic Data Vault's recursive Gaussian copula [6], syntha replaces Pearson-on-codes with Olsson polyserial / Bonett–Price tetrachoric estimators [11,12], appropriate for mixed binary/continuous EHR data. We did not run a head-to-head benchmark against CTGAN/medGAN/Synthea on SynthEHRella [18]; this is deferred to future work, and the present claims are positioned as "different point in the design space" rather than as outperforming deep generators.

The Turkish-locale layer provides bilingual `Condition.code.text` and ISO 3166-2:TR province coding calibrated to a Turkish hospital cohort; we are not aware of another openly released FHIR R4 generator with comparable localization. In principle, generalization to other locales requires swapping marginal-quantile JSON, name/province distributions, and condition-display mapping; in practice, clinical-module retuning and formulary mapping will be needed.

### Limitations

(i) Synthetic disease prevalence is substantially below Turkish epidemiologic estimates by construction of the data-quality-curated source (HT ≈ 7.5% vs PatenT-2 ≈ 30%; DM ≈ 4.8% vs TURDEP-II ≈ 13.7% [33]; hyperlipidemia ≈ 12% vs TEKHARF >40% above age 40; depression ≈ 0.22% vs Turkish primary-care 10–20%). Risk-prediction models trained on syntha v0.5.x **must** be recalibrated against TÜİK / TURDEP-II / PatenT-2 / TEKHARF marginals before any deployment; uncalibrated use will systematically underestimate risk. Marginal recalibration is queued for v0.6. (ii) syntha is not yet differentially private; a Gaussian-mechanism wrapper on the sufficient statistics is planned for v0.7. (iii) Longitudinal expansion is a Poisson + AR(1) walk, not a PADM state machine for progression; v0.8 will add state machines. (iv) The Gaussian copula reproduces the bulk of joint distributions but not the long tails; rare-event studies should be interpreted with caution. (v) ICD-10 specificity is currently at `.9` granularity for several conditions (J45.9, J44.9, N18.9, F32.9, F41.9, E78.5, E07.9, I25.9). Because syntha already models eGFR, PHQ-9, and lipid sub-fractions, refining to N18.1–N18.5 (CKD stages), F32.0–F32.2 (depression severity), and E78.0/E78.1/E78.2 is feasible and queued for v0.6. Users training auto-coder models on v0.5.x should be aware that the dataset will bias such models toward unspecified codes — a non-trivial patient-safety implication. (vi) Reference-range coverage uses two sex-stratified analytes (hemoglobin, creatinine) and 12 sex-agnostic analytes with sex-specific notes (HDL, LDL, TC, TG, ALT, AST, platelets, WBC, ferritin, vitamin B12, fasting glucose, TSH); full stratification (HDL, ALT, ferritin) is queued. (vii) DM_Komplikasyonlu is mapped to SNOMED CT 44054006 + ICD-10 E11.8 on the assumption that complicated cases in the source are predominantly T2DM; T1DM and secondary DM are not separately modeled.

## Conclusion

syntha is, to our knowledge, the first openly released hybrid synthetic-EHR generator that combines a mixed-type Gaussian copula with polyserial/tetrachoric correlation estimation, a Synthea-style nine-module clinical layer, a Stadler 2022 MIA privacy audit gated in CI, and full FHIR R4 export coded in LOINC, SNOMED CT, ICD-10, and RxNorm with Turkish localization. It runs in seconds without a GPU, exposes every parameter for clinician audit, and ships as a PyPI package, a Docker image, and signed cross-platform desktop applications under Apache-2.0.

## Acknowledgments

We thank the Synthea project for setting the open-source standard for synthetic EHR generation [1] and the LOINC, SNOMED CT, ICD-10, and RxNorm maintainers for the openly licensed vocabularies on which syntha's FHIR export depends. Per JAMIA Open policy: a large-language-model assistant (Claude, Anthropic) was used for editorial proofreading of draft sentences; no AI tool generated scientific content, results, or code paths.

## Author Contributions (CRediT)

**A.M.**: Conceptualization, Methodology, Software, Validation, Formal analysis, Writing — original draft, Visualization, Project administration. **U.K.**: Conceptualization (clinical), Methodology (clinical modules), Resources (Turkish locale verification), Writing — review & editing. Both authors approved the final version.

## Competing Interests

None declared.

## Funding

No external funding was received.

## Ethics

This work used a retrospective dataset that was de-identified at source before release to the authors; the authors had access only to anonymized data and no linkage key, undertook no patient interaction, and attempted no re-identification. The use is consistent with secondary-use research on anonymized data under Türkiye'nin Kişisel Verileri Koruma Kanunu (KVKK).

## Data and Code Availability

- **Source code**: https://github.com/ArioMoniri/syntha (Apache-2.0, tag v0.5.8, commit `5d3cd6b`)
- **PyPI**: `pip install syntha-ehr==0.5.8`
- **Docker image**: `ghcr.io/ariomoniri/syntha:v0.5.8`
- **Signed desktop installers**: macOS `.dmg` (DevID-notarized), Windows `-setup.exe` (code-signed), Linux `.AppImage`; minisign-signed auto-updater (pubkey `B9D5DA5050FA66E1`). Verify: `minisign -V -P RWS$(cat pubkey.b64) -m <installer>`; base64 pubkey published on the GitHub release page.
- **HAPI FHIR**: https://hapifhir.io (accessed 2026-01-15). The Collaborate panel is UI-only and does not participate in data generation or validation.

Every figure, table, and number in this manuscript is regenerated by `scripts/make_plots.py` (SEED=42, n=5,000) and `pytest -q`; full reproducibility recipe in Methods §"Engineering and reproducibility".

## Supplementary Material

(S1) Extended derivations of Olsson polyserial and Bonett–Price tetrachoric estimators with the Drezner & Wesolowsky 1990 BVN-CDF kernel, and the known-truth simulation demonstrating ≈50% (continuous–binary) and ≈65% (binary–binary) attenuation under naive Pearson-on-codes. (S2) Full Stadler 2022 NN-MIA methodology, shadow-cohort construction, distance metric, and ROC curves. (S3) Additional per-column validation tables (KS, Wasserstein, reference-range coverage; physiologic-filter acceptance rates). (S4) FHIR resource templates for every emitted resource type with example JSON, including PHQ-9/GAD-7 panel-vs-item discussion. (S5) Turkish terminology mapping (`CONDITION_DISPLAY_TR`, RxNorm Turkish-name aliases, ISO 3166-2:TR weights). (S6) BERTurk-base clinical-relevance fine-tune details.

## References

1. Walonoski J, Kramer M, Nichols J, et al. Synthea: an approach, method, and software mechanism for generating synthetic patients and the synthetic electronic health care record. J Am Med Inform Assoc. 2018;25(3):230–238. doi:10.1093/jamia/ocx079.

2. Gonzales A, Guruswamy G, Smith SR. Synthetic data in health care: a narrative review. PLOS Digit Health. 2023;2(1):e0000082. doi:10.1371/journal.pdig.0000082.

3. Choi E, Biswal S, Malin B, et al. Generating multi-label discrete patient records using generative adversarial networks. Proc Mach Learn Healthc (MLHC). 2017;68:286–305.

4. Torfi A, Fox EA. CorGAN: correlation-capturing convolutional generative adversarial networks for generating synthetic healthcare records. Proc FLAIRS. 2020;33:335–340.

5. Xu L, Skoularidou M, Cuesta-Infante A, Veeramachaneni K. Modeling tabular data using conditional GAN. Adv Neural Inf Process Syst. 2019;32:7335–7345.

6. Patki N, Wedge R, Veeramachaneni K. The synthetic data vault. Proc IEEE DSAA. 2016:399–410. doi:10.1109/DSAA.2016.49.

7. Xie L, Lin K, Wang S, Wang F, Zhou J. Differentially private generative adversarial network. arXiv:1802.06739. 2018.

8. Jordon J, Yoon J, van der Schaar M. PATE-GAN: synthetic data generation with differential privacy guarantees. Proc Int Conf Learn Represent (ICLR). 2019.

9. Yoon J, Mizrahi M, Ghalebikesabi S, et al. EHR-Safe: generating high-fidelity and privacy-preserving synthetic electronic health records. NPJ Digit Med. 2023;6:141. doi:10.1038/s41746-023-00888-7.

10. Stadler T, Oprisanu B, Troncoso C. Synthetic data — anonymisation Groundhog Day. Proc USENIX Secur Symp. 2022:1451–1468.

11. Olsson U, Drasgow F, Dorans NJ. The polyserial correlation coefficient. Psychometrika. 1982;47(3):337–347. doi:10.1007/BF02294164.

12. Bonett DG, Price RM. Inferential methods for the tetrachoric correlation coefficient. J Educ Behav Stat. 2005;30(2):213–225. doi:10.3102/10769986030002213.

13. Drezner Z, Wesolowsky GO. On the computation of the bivariate normal integral. J Stat Comput Simul. 1990;35(1–2):101–107. doi:10.1080/00949659008811236.

14. Mandel JC, Kreda DA, Mandl KD, Kohane IS, Ramoni RB. SMART on FHIR: a standards-based, interoperable apps platform for electronic health records. J Am Med Inform Assoc. 2016;23(5):899–908. doi:10.1093/jamia/ocv189.

15. Sklar A. Fonctions de répartition à n dimensions et leurs marges. Publ Inst Stat Univ Paris. 1959;8:229–231.

16. Kruskal WH. Ordinal measures of association. J Am Stat Assoc. 1958;53(284):814–861.

17. Friedewald WT, Levy RI, Fredrickson DS. Estimation of low-density lipoprotein cholesterol in plasma, without use of the preparative ultracentrifuge. Clin Chem. 1972;18(6):499–502.

18. Chen J, Zhang Z, Xie Y, et al. SynthEHRella: a unified framework for benchmarking synthetic electronic health record generation. Adv Neural Inf Process Syst Datasets Benchmarks Track. 2024;37:1–24.

19. Charlson ME, Pompei P, Ales KL, MacKenzie CR. A new method of classifying prognostic comorbidity in longitudinal studies: development and validation. J Chronic Dis. 1987;40(5):373–383.

20. Martin SS, Blaha MJ, Elshazly MB, et al. Comparison of a novel method vs the Friedewald equation for estimating low-density lipoprotein cholesterol levels. JAMA. 2013;310(19):2061–2068. doi:10.1001/jama.2013.280532.

21. Westgard JO, Barry PL, Hunt MR, Groth T. A multi-rule Shewhart chart for quality control in clinical chemistry. Clin Chem. 1981;27(3):493–501.

22. Regenstrief Institute. LOINC. https://loinc.org (accessed 2026-01-15).

23. SNOMED International. SNOMED CT. https://www.snomed.org (accessed 2026-01-15).

24. World Health Organization. International Statistical Classification of Diseases and Related Health Problems, 10th Revision (ICD-10). Geneva: WHO; 2019.

25. U.S. National Library of Medicine. RxNorm. https://www.nlm.nih.gov/research/umls/rxnorm (accessed 2026-01-15).

26. Schweter S. BERTurk: BERT models for Turkish. Zenodo. 2020. doi:10.5281/zenodo.3770924.

27. Higham NJ. Computing the nearest correlation matrix — a problem from finance. IMA J Numer Anal. 2002;22(3):329–343. doi:10.1093/imanum/22.3.329.

28. Franklin SS, Khan SA, Wong ND, Larson MG, Levy D. Is pulse pressure useful in predicting risk for coronary heart disease? The Framingham Heart Study. Circulation. 1999;100(4):354–360.

29. Fraser CG. Biological variation: from principles to practice. Washington, DC: AACC Press; 2001.

30. Ricós C, Alvarez V, Cava F, et al. Current databases on biological variation: pros, cons and progress. Scand J Clin Lab Invest. 1999;59(7):491–500.

31. Charlson ME, Szatrowski TP, Peterson J, Gold J. Validation of a combined comorbidity index. J Clin Epidemiol. 1994;47(11):1245–1251.

32. El Emam K, Mosquera L, Hoptroff R. Practical synthetic data generation: balancing privacy and the broad availability of data. Sebastopol: O'Reilly; 2020.

33. Satman I, Omer B, Tutuncu Y, et al. Twelve-year trends in the prevalence and risk factors of diabetes and prediabetes in Turkish adults (TURDEP-II). Eur J Epidemiol. 2013;28(2):169–180. doi:10.1007/s10654-013-9771-5.
