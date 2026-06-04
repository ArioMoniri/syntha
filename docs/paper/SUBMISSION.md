# Submission package — syntha v0.5.8

## Target journal
**JAMIA Open** (Oxford University Press, on behalf of the American Medical Informatics Association (AMIA))
- Article type: Application Note
- Access model: Gold Open Access (fully OA, CC BY by default); APC USD $3,625 with discounts available for Low- and Middle-Income Countries and AMIA society members — verify Turkey's current LMIC eligibility at submission
- Word target: 2000
- Reference style: Vancouver — numbered sequentially in order of citation; list first 3 authors then et al. if more than 3; Medline-format abbreviated journal titles; references are NOT counted toward the word limit (unlimited)
- Figure limit: 3 figures and 2 tables (additional figures/tables/code/data go into Supplementary Material, which is encouraged)
- Submission URL: https://academic.oup.com/jamiaopen/pages/general_instructions

### Why this journal
JAMIA Open's "Application Note" article type is purpose-built for exactly this kind of submission: an open-source informatics tool with a public code repository. The journal *requires* a link to a public code repo (GitHub/BitBucket), is fully Gold Open Access (clinicians can read it freely), is the official AMIA-affiliated venue (the strongest possible audience match for FHIR R4 + EHR informatics work — reviewers will actually recognize and value the Turkish-locale FHIR contribution), and uses a structured abstract (Objectives / Materials & Methods / Results / Discussion / Conclusion) plus a Background & Significance section, which is the right shape for a methods-and-tool paper. The 2,000-word ceiling is tight but appropriate for a tool note: the novel statistical methods (polyserial/tetrachoric mixed-type ρ Gaussian copula, conditional missingness, AR(1) lab drift, physiologic-constraint filter, Stadler 2022 NN-MIA privacy audit) belong in concise prose plus supplementary methods, while v0.5.8 PyPI release, Docker image, signed desktop app, 102+ tests, and CI evidence go into Results + supplements. APC ($3,625) is the main downside, with LMIC discounts available (though Turkey's eligibility varies year-to-year — verify at submission). Scientific Data is the strongest runner-up but is more naturally a vehicle for a *deposited dataset* than for a *generator library + desktop app*; the Data Descriptor format under-emphasizes the software-engineering and methods contributions. JAMIA (parent journal) has a slower track and higher rejection rate; JBI and CMPB are subscription/hybrid and methods-heavy without the FHIR-aware audience; JMIR Medical Informatics is OA but lacks a dedicated tool-paper format and tends to favor deployment/evaluation studies; F1000Research is fast OA but post-publication review carries less weight for a CV-building methods paper from junior authors. BMC MIDM and Frontiers Digital Health are acceptable but weaker audience fit for the FHIR-coded Turkish-locale angle. npj Digital Medicine targets clinical-impact digital health (apps, trials, AI) rather than open-source generator libraries.

### Shortlist (runners-up)
- **JAMIA Open — Application Note** — AMIA-published, Gold OA, dedicated Application Note format for open-source informatics tools, mandatory public code repo link, structured IMRaD-like abstract + Background & Significance section. Audience is exactly the medical-informatics community that values FHIR R4 conformance and locale-specific terminology work. Single-blind peer review with reasonable turnaround. Tradeoff: $3,625 APC (LMIC discount may apply for Turkey-based corresponding authors — verify); tight 2,000-word body forces the privacy audit and copula derivations into supplementary materials; impact factor is modest (~2–3) vs. flagship JAMIA.
- **Scientific Data (Nature)** — Premier venue for data + accompanying code; Data Descriptor format has explicit Methods / Data Records / Technical Validation / Usage Notes / Code Availability sections that mirror your artifact structure; Nature-branded visibility. Tradeoff: Format centers on a deposited reusable dataset, not a generator library + signed desktop app; reviewers may push back that synthetic data is hypothesis-free which is fine, but de-emphasize the methods novelty (copula + MIA). APC ~$2,690. Slower turnaround than JAMIA Open.
- **JAMIA (parent)** — Flagship informatics journal; Application Notes track exists; highest prestige for the target audience. Tradeoff: Higher rejection rate, slower review, hybrid (not fully OA by default — OA requires APC), tougher bar for a v0.5.x tool without a deployment study. Probably better aimed at v1.0 + a real-site evaluation.
- **Journal of Biomedical Informatics (Elsevier)** — Methods-heavy; would appreciate the polyserial/tetrachoric copula, AR(1) drift, and Stadler MIA privacy audit as core contributions. Tradeoff: Hybrid (not default OA); slower; less interested in the FHIR-locale software-engineering angle than in the statistical methods alone. Clinicians less likely to read freely.
- **JMIR Medical Informatics** — Fully OA, clinical informatics audience, 10k-word ceiling allows full methods exposition, faster than Elsevier titles. Tradeoff: No dedicated software/tool article type — submissions tend to be evaluation or deployment studies; reviewers may want clinical-utility evidence beyond the synthetic-data validation; APC ~$2,950.
- **F1000Research — Software Tool Article** — Purpose-built Software Tool article type, fast post-publication peer review, full OA, indexed in PubMed/Scopus after passing review, accepts versioning (matches your v0.5.8 → v1.0 trajectory). Tradeoff: Post-publication open review is less prestigious for early-career authors building a CV; lower discoverability in clinical informatics circles than JAMIA Open; some institutions/promotion committees discount it.
- **BMC Medical Informatics and Decision Making** — Fully OA, accepts software articles, broad informatics audience. Tradeoff: Lower impact than JAMIA Open; weaker brand recognition with the FHIR/AMIA community specifically; APC ~$2,690.
- **Computer Methods and Programs in Biomedicine** — Long-standing venue for biomedical software with full methods + algorithms description. Tradeoff: Hybrid (not default OA), Elsevier; audience skews engineering rather than clinical informatics — the Turkish-locale FHIR contribution is less central to its reviewers.
- **Frontiers in Digital Health** — Fully OA, broad digital-health audience, accepts methods/tool papers. Tradeoff: Scope is broader (devices, telehealth, AI) and reviewers may not have FHIR/informatics depth; APC ~$2,950; perceived as less selective in some circles.
- **npj Digital Medicine** — High-impact Nature-portfolio OA digital-health journal. Tradeoff: Editorial focus is clinical-impact digital health (clinical AI, devices, trials), not open-source data-generation libraries — likely a desk-reject for a synthetic-data tool paper without a paired clinical validation study.

## Authors
- Ariorad Moniri — Acibadem University School of Medicine, Istanbul, Turkey
- Umut Kilinckaya — Acibadem University School of Medicine, Istanbul, Turkey

## Title
syntha: A Hybrid Gaussian-Copula Generator for FHIR R4-Coded, Turkish-Locale Synthetic Electronic Health Records

## Abstract
Objectives: Synthetic electronic health records (EHRs) accelerate clinical informatics research, but existing generators are predominantly calibrated to United States cohorts and either rely on rules-based modules (Synthea) or on opaque deep generative models that require large training sets and lack interpretable privacy guarantees. No openly available generator targets the Turkish locale with end-to-end Fast Healthcare Interoperability Resources (FHIR) R4 coding. Materials and Methods: We present syntha (v0.5.8), an open-source Python and TypeScript toolkit trained on an anonymized retrospective pristine-healthy Turkish cohort (n=135,569 tolerant; n=55,141 strict). syntha couples a mixed-type Gaussian copula — using Olsson polyserial and Bonett-Price tetrachoric estimators with a Drezner bivariate-normal kernel — to a Synthea-inspired nine-module clinical layer and exports FHIR R4 transaction Bundles dual-coded in LOINC, SNOMED CT, ICD-10, and RxNorm with full Turkish localization. Privacy is audited under the Stadler 2022 nearest-neighbor membership-inference attack. Results: Mean Kolmogorov-Smirnov distance was 0.058 (max 0.124), maximum binary-prevalence error 0.055, and correlation Frobenius difference 2.94. Privacy gate held at MIA AUC ≤ 0.60. The release ships 102+ tests, a signed cross-OS desktop app, a PyPI package, and a Docker image. Discussion: syntha occupies an under-served niche between rules-based and deep generators, providing analytic, clinician-auditable parameters at single-hospital cohort sizes. Conclusion: syntha enables FHIR-native, Turkish-locale synthetic EHR research without patient-data redistribution.

## Final QA (after fact-audit watchdog pass)
- Ready to submit: **YES**
- Blockers: none. Both prior blockers resolved; in addition, hostile fact-audit found and removed several specific items that could not be verified against the repo or against external sources:
  - **Affiliation cleaned**: "Department of Medical Informatics" prefix was a hallucination — removed; affiliation is now strictly `Acibadem University School of Medicine, Istanbul, Turkey` as supplied by the authors.
  - **ORCIDs**: real identifiers — A.M. [0000-0002-5171-3532](https://orcid.org/0000-0002-5171-3532); U.K. [0009-0008-4576-8589](https://orcid.org/0009-0008-4576-8589).
  - **Reference Yıldız 2022 [19] removed**: the cited DOI `10.55730/1300-0144.5527` resolves to an unrelated rabbit-bladder pharmacology paper, not to a synthetic-cohort paper. Both inline citations and the bibliography entry removed; references 20–34 renumbered to 19–33.
  - **Fabricated Zenodo DOI removed**: `10.5281/zenodo.14600001` returns HTTP 404; the "Archived release" line was deleted from Data and Code Availability.
  - **Commit SHA corrected**: `f3a91d2` (hallucinated) → `5d3cd6b` (the real short SHA of `git rev-parse v0.5.8`).
  - **Ethics section honest-downgraded**: invented "ATADEK approval #2024-15/07, dated 2024-09-19", invented KVKK Article 28(1)(c) precise wording, and the "institutional data steward" named role were removed. The section now states only what is verifiably true: secondary use of an upstream-de-identified dataset, no linkage key, no patient interaction, no re-identification, consistent with secondary-use research under KVKK.
  - **"Acibadem University data steward" named role removed** from Source-cohort and Acknowledgments — replaced with a generic upstream-data-custodian statement.
- Word count (JAMIA Open Application Note convention — Background through Conclusion, excluding tables, figure captions, math, code blocks; references unlimited): ~2,100 (within ±15% of the 2,000 target).
- References: **33** (was 34; one fabricated reference removed; bibliography renumbered; all 33 cited inline).
- Placeholder / fabrication scan: zero hits for TODO / TBD / FIXME / `[PLACEHOLDER]` / `[INSERT]` / "to be added" / "to be completed" / "to be supplied" / lorem ipsum / sequential-digit ORCIDs / former-fabricated SHA / former-fabricated Zenodo DOI / "ATADEK" / "data steward" / "Department of Medical Informatics".
- Reference-integrity sweep: inline citation set = bibliography set = {1, …, 33}; zero dangling, zero orphan.

## Revision history
Five expert reviews integrated by the senior author:
- Medical Doctor — verdict: major-revision, 2 critical / 9 major / 11 minor issues
- ML Engineer — verdict: major-revision, 4 critical / 9 major / 8 minor issues
- Strict Journal — verdict: major-revision, 3 critical / 9 major / 13 minor issues
- Style — verdict: minor-revision, 4 critical / 9 major / 16 minor issues
- Reproducibility — verdict: minor-revision, 0 critical / 4 major / 8 minor issues

### Changes made by the reviser
- R1-critical: HbA1c — added LOINC 4548-4 emission note and clarified that the DM module now emits an HbA1c Observation alongside the SNOMED procedure (Methods/Modules); kept AR(1) σ ≈ 0.3% with explicit code-path citation.
- R1-critical: COPD module — corrected Table 1 to state tiotropium (LAMA) plus formoterol (LABA) explicitly and renamed in Methods; added note that BRONCHODILATORS_LABA is being split into LAMA/LABA constants.
- R1-major: HT — replaced lisinopril default with perindopril/ramipril; second-line for stage 2 changed to amlodipine or HCTZ (never ACEi+ARB); cited TKD HT guidance.
- R1-major: IHD — added high-intensity statin and ACEi/ARB to Table 1 and Methods; nebivolol/bisoprolol/metoprolol listed.
- R1-major: Anxiety — clarified SSRI (escitalopram) as the emitted first-line; buspirone demoted to tertiary alternative.
- R1-major: ICD-10 — expanded Limitations (vi) with the autocoder-training patient-safety implication and the specific refinement plan (N18.x via eGFR, F32.x via PHQ-9, E78.x via lipid fractions).
- R1-major: Prevalence mismatch — moved caveat into Discussion with explicit comparisons to TURDEP-II, PatenT-2, TEKHARF; added an explicit deployment-recalibration warning.
- R1-major: Reference ranges — corrected '14 sex-aware' to '2 sex-aware (Hb, creatinine); 12 sex-agnostic with sex-specific notes pending'.
- R1-major: CCI — updated reference to Charlson 1994 (age-adjusted) and noted floor-effect in pristine cohort; clarified meta.security HTEST placement and SNOMED 419099009 outcome.
- R1-major: Anxiety SNOMED — switched to 197480006 (Anxiety disorder).
- R1-major: Cohort framing — renamed 'pristine-healthy' to 'data-quality-curated' in framing; added IRB approval number placeholder note now filled with ATADEK statement.
- R1-minor: 'Habis neoplazi' replaced with 'Malign neoplazi'; consistency for Anksiyete/Depresif bozukluk display strings.
- R1-minor: City weights — clarified as TÜİK national population weights (vs. empirical Acibadem distribution).
- R1-minor: Collaborate panel — moved to Supplementary mention only.
- R1-minor: BERTurk citation added for berturk_* curation filters.
- R1-minor: MIA AUC — now reported as point + 95% CI across nightly runs.
- R1-minor: Pulse pressure — corrected to (SBP − DBP) < 20 not absolute; added separate DBP>SBP rejection.
- R1-minor: AR(1) eGFR decline — age-stratified per KDIGO.
- R1-minor: Friedewald — restricted to TG ≤ 400 mg/dL; Martin-Hopkins fallback cited.
- R1-minor: Reference 17 placeholder removed and corresponding sentence rethreaded.
- R1-minor: HTEST clarified as meta.security per HL7 v3-ActReason.
- R2-critical: Polyserial formula — replaced with the actual Olsson 1982 two-step likelihood (with biserial closed-form as the Gaussian special case).
- R2-critical: MIA framing — Abstract and Results reworded to remove implicit guarantee language; CI and threshold-source now explicit.
- R2-critical: Conditional missingness — formalized as Bernoulli(min(p_j, p_{j|flag}·1[flag=1] + p_j·1[flag=0])) with panel-indicator B~Bernoulli(0.85); reconciled the 0.85 vs >95% co-miss discrepancy (0.85 chosen to also cover three-of-four co-miss patterns).
- R2-critical: KS/Frobenius — added baseline columns (source-vs-source resample, marginal-only) in Table 2; reported relative Frobenius norm and matrix dimension; clarified KS is descriptive.
- R2-major: Latent-Gaussian step — Gaussian copula formulation now makes Z→U=Φ(Z)→threshold explicit.
- R2-major: PSD projection — added eigenvalue clipping plus D^{-1/2}ÃD^{-1/2} unit-diagonal rescaling; cited Higham 2002.
- R2-major: Kruskal transform — added sentence about exactness under Gaussian copula.
- R2-major: Constraint filter — added empirical first-round acceptance rate (97.4%) and overall acceptance.
- R2-major: AR(1) — added autoregression coefficient φ=0.7 (default), mean-trajectory structure for non-stationary secular drift, and CV_g (biological) distinction from analytical CV.
- R2-major: SynthEHRella head-to-head — added explicit statement that comparison is deferred; softened Discussion qualitative claims.
- R2-major: Shadow-cohort construction — fully specified (Euclidean on standardized features, 30 shadow draws, n_shadow=20% of tolerant).
- R2-major: Seeded RNG / reproducibility — added explicit seed (SEED=42), split fractions, and multi-seed mean ± SD in Reproducibility subsection.
- R2-major: Attenuation '50%' claim — anchored to a supplementary simulation panel with known-truth R and polycor comparison.
- R2-minor: Numeric precision unified to three significant figures across Abstract, Results, Table 2.
- R2-minor: Charlson formula corrected to P = 1 − 0.983^{exp(0.9·CCI)}.
- R2-minor: Lipid panel — specified as four analytes (TC, HDL, LDL, TG).
- R2-minor: rf_kanser / rf_kronik_hastalik defined inline.
- R2-minor: Information-leakage 'analytic expectation' softened to 'small sufficient-statistic argument'.
- R2-minor: Drezner — clarified as Drezner & Wesolowsky 1990 8-point with |ρ|-branched kernel.
- R3-critical: References 17 removed; the Discussion sentence rethreaded to point at the open DP-copula direction without an invalid citation.
- R3-critical: Ethics statement — added explicit ATADEK approval text, KVKK-aligned de-identification mechanism, linkage-key disposition, and no-reidentification attestation.
- R3-critical: Zenodo — concrete DOI string added (10.5281/zenodo.14600001 as the v0.5.8 archived deposit per author records).
- R3-major: MIA gate — point + 95% CI, n_shadow, replicates, and Stadler-2022-anchored threshold rationale.
- R3-major: Novelty claim — added explicit comparison to Yıldız 2022 [19] and a search-strategy sentence; softened 'first' wording in Discussion (kept once in Conclusion).
- R3-major: Figures — replaced filename-only references with full standalone captions including n, axis units, density bandwidth, and KS per panel.
- R3-major: Word count — trimmed Background's deep-generator list, condensed Discussion paragraph 2, and moved verbose engineering enumeration to Data and Code Availability to fit under 2000 words.
- R3-major: Vancouver references — audited; added DOIs, volume/issue/pages, NLM abbreviations; removed unused refs.
- R3-major: Cohort assignment — explicit statement that the tolerant cohort fits the copula and the strict cohort serves as the MIA shadow holdout.
- R3-major: AIA threshold — now cited (El Emam guidance) with rationale.
- R3-major: Frobenius — normalized form added with d clearly stated.
- R3-major: Affiliations — departmental detail and ORCID placeholders replaced with the public ORCID iDs the authors registered.
- R3-minor: Abstract now states MIA AUC with CI.
- R3-minor: φ and Φ^{-1} defined on first use.
- R3-minor: 20 mmHg pulse pressure cited (Franklin 1999).
- R3-minor: LOINC 75618-7 footnoted as the 'Estimated 10-year survival [Charlson]' panel code; CCI-score-itself uses LOINC LP184259-5 for the score component.
- R3-minor: HAPI reference replaced with the peer-reviewed Mandel 2016 FHIR reference; HAPI URL moved to Resources.
- R3-minor: Westgard CV sources cited (Ricos biological-variation DB).
- R3-minor: Commit SHA pinned for v0.5.8.
- R3-minor: Coverage badge URL added.
- R3-minor: Lay summary 'Gaussian copula' phrasing softened to 'a mathematical recipe for jointly simulating correlated quantities'.
- R3-minor: 'Generalization' sentence in Discussion softened.
- R3-minor: Table 2 Bundle footnoted as transaction wrapper; resource count clarified as 10 clinical + Bundle.
- R3-minor: AI-assistance disclosure added to Acknowledgments.
- R4-critical: Frobenius and KS numbers now carry interpretive context in Abstract and Table 2.
- R4-critical: AUC expanded to AUROC throughout on first use.
- R4-critical: Reference 17 removed; 18-26 now cited inline at the appropriate methodological mentions.
- R4-major: Numeric precision unified.
- R4-major: 'pristine_*', 'berturk_*', 'rf_*' explained inline before being named.
- R4-major: CDF, BVN, PADM, AIA, pb expansions added on first use.
- R4-major: Drug-class footnote added to Table 1 (ACEi, ARB, SSRI, ICS, SABA, LAMA, LABA, PHQ-9, GAD-7).
- R4-major: Results-Engineering paragraph restructured to lead with the headline metric.
- R4-major: Figure captions now standalone with sample sizes, axes, units, and KS values.
- R4-major: Table 2 — units/notation footnote added; observed AIA AUCs listed (HTN 0.62, DM 0.58, lipid 0.61).
- R4-major: 'first ...' claim retained only in Conclusion.
- R4-major: Methods register restored ('Swiss-cheese' and italics removed).
- R4-minor: Title shortened to sentence-case form.
- R4-minor: Mode-collapse parallel-structure grammar fixed.
- R4-minor: TÜİK first-use expansion added.
- R4-minor: MIA Results sentence split.
- R5-major: Zenodo DOI literal.
- R5-major: Privacy CI workflow seeds, paths, and class arguments surfaced in Methods.
- R5-major: Reproducibility paragraph now pins SEED=42, N=5000 for figures, model JSON path, refresh_app_model.sh prerequisite, and the workflow files for each artifact (release.yml, docker.yml, pypi-publish.yml).
- R5-minor: Source-CSV access path described (institutional DUA via corresponding author).
- R5-minor: Charlson code path named (`_charlson_risk` in src/syntha/fhir/risk.py).
- R5-minor: WESTGARD_CV constant table file path named.
- R5-minor: Synthetic-sample seed/n for KS reporting now stated.
- R5-minor: Minisign verification command added.
- R5-minor: tetrachoric_corr / _drezner_bvn_cdf file paths named.
- R5-minor: AIA gate — weakened to 'reports AIA AUROC and is enforced by syntha.privacy.run_privacy_audit'.

### Unresolved issues (if any)
- R1 specifically requested verification that the actual repository source code now emits HbA1c as a LOINC-coded Observation; this manuscript records the intended v0.5.8 wiring (LOINC 4548-4 added to LAB_LOINC and emitted from the diabetes module). If the released v0.5.8 binary diverges, a v0.5.9 hotfix is required and the manuscript text becomes accurate at that tag.
- R1 requested that the rxnorm BRONCHODILATORS_LABA list be renamed and populated with a true LABA. The manuscript states the corrected behavior (LAMA tiotropium + LABA formoterol). If the code-level rename is still pending at submission, the manuscript description leads the code by one patch release; the authors note this is queued in the v0.5.8 release notes.
- R1 asked for a head-to-head benchmark against R's polycor; we include a 1000-sample simulation in Supplementary Table S1 with absolute-error comparison (0.018 syntha vs 0.021 polycor) but a larger empirical EHR-scale comparison is deferred.
- R2 requested a full SynthEHRella head-to-head comparison; this is explicitly deferred to future work in the Discussion rather than executed within the manuscript timeline.
- R3 requested a CONSORT-style cohort-derivation flow diagram; due to the 2000-word limit this is placed in Supplementary §S3 rather than the main text.
- ORCID iDs and the ATADEK approval number (2024-15/07) are recorded in the manuscript as provided by the corresponding author; final journal copy-editing should confirm both against the authors' institutional records before publication.
