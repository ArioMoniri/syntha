# 🩺 syntha v0.5.0 — scientific-correctness sprint + full engineering polish

This release closes every item from the v0.5 medical-officer-reviewed roadmap, plus the entire Tier 1+2+3+4 engineering-hygiene punch list. **96 tests pass on Py 3.10 → 3.13 across macOS/Windows/Linux.** No PHI ever touches the repo or any installer.

## 🆕 Scientific gains (signed off by CMO + ML engineer in [REVIEW_v0.5_FINAL.md](https://github.com/ArioMoniri/syntha/blob/v0.5.0/docs/REVIEW_v0.5_FINAL.md))

| What | Why | Impact |
|---|---|---|
| 🧮 **Polyserial + tetrachoric latent-Gaussian correlation** | Spearman ranks on tied (binary) columns are biased toward 0; this is the right math for mixed-type pairs | Continuous↔binary correlation magnitudes **94.2% of source** (was 83.7% in v0.4) — proven on the real 55,141-row strict cohort |
| 🧮 **Joint + comorbidity-conditional missingness** | Real EHR missingness is panel-correlated AND condition-driven — diabetics get HbA1c, healthy young adults don't | Lipid-panel co-missingness ~85% in synthetic vs ~0% with v0.4's independent Bernoulli |
| ⏱️ **Lab time-series + intra-encounter BP trajectories** | Single `_latest` snapshot is clinically unrealistic; real EHR has historical measurements + multi-reading BPs per visit | AR(1) drift with Westgard-QC-derived column-specific σ; 3 BP repeats per encounter with white-coat-decline pattern |
| 🛡️ **Privacy audit CI** | Without a formal attack run, we had no quantitative privacy evidence | Membership-inference + attribute-inference attacks run on every push; CI fails if MIA AUC > 0.60 |
| 🩺 **HTEST + syntha-copula tags on every `Patient`** | Patient-safety prerequisite — synthetic must be unambiguously markable | Every Patient.meta.tag carries `terminology.hl7.org/CodeSystem/v3-ActReason#HTEST` |
| 🩹 **Sex-specific clinical reference ranges** | Hb 13.5–17.5 g/dL for males vs 12.0–15.5 for females; lab-flagging correctness | 16 labs with proper reference intervals + `fraction_within_reference()` API |

## 🧠 Output gains

| New FHIR resource | When emitted | Codes |
|---|---|---|
| 🧪 `DiagnosticReport` (×5 panels per patient) | Lipid / CBC / CMP / Iron / BP labs are present | LOINC 57698-3 / 58410-2 / 24323-8 / 24350-1 / 85354-9 |
| 🧾 `RiskAssessment` (Charlson) | `charlson_cci` column is non-null | LOINC 75618-7 |
| 🧠 `Observation` (PHQ-9) | `Depresyon = 1` | LOINC 44261-6 |
| 😰 `Observation` (GAD-7) | `Anksiyete = 1` | LOINC 70274-6 |
| 👨‍👩‍👧 `FamilyMemberHistory` | `rf_kanser` or `rf_kronik_hastalik` is set | SNOMED 363346000 / 237603008 |
| ⏱️ Time-series `Observation` (×2–4 historical) | Per lab with non-null `_latest`, in the preceding 6–24 months | LOINC per the existing lab table |

## 🎯 New CLI

```bash
# Conditional sampling — only return rows matching a filter
syntha sample-conditional \
    --registry output/tolerant/models \
    --name copula_tolerant \
    --output diabetics-over-60.csv \
    --n 1000 \
    --condition "age > 60 & DM_Tum == 1 & bp_systolic >= 140"
```

AST-validated safety: only comparisons, boolean ops, arithmetic, literals, and column-name references allowed. Attribute access, function calls, subscripts, lambdas — all blocked.

## 🇹🇷 Desktop app: Turkish UI

The Tauri app now ships in **English and Turkish** with a locale switcher in the footer. Detection order: saved preference → `navigator.language` prefix → English fallback.

## 🚀 Engineering infrastructure

| Component | What |
|---|---|
| 🐳 Docker | `docker run ghcr.io/ariomoniri/syntha:latest generate ...` — multi-platform (amd64+arm64) |
| 📦 PyPI | OIDC trusted-publisher workflow ready; this release will be the first push (once PyPI name is reserved) |
| 🪟 Windows Authenticode | Workflow ready, fires when `WINDOWS_CERTIFICATE` secret is set ([docs/WINDOWS_SIGNING.md](https://github.com/ArioMoniri/syntha/blob/v0.5.0/docs/WINDOWS_SIGNING.md)) |
| 📊 Benchmark dashboard | https://ariomoniri.github.io/syntha — auto-deployed |
| 🤖 Dependabot | Weekly auto-PRs for 4 ecosystems |
| 🛡️ CodeQL SAST | Python + TypeScript with `security-extended` query pack |
| 🧪 HAPI FHIR validator | Validates 10 bundles per `src/syntha/fhir/**` change |
| 🛡️ Privacy audit | Runs on every push to `generator/` |
| 📜 SBOM | SPDX-JSON attached to every release |
| 🚀 release-please | Conventional-commits → auto-PR → semver + CHANGELOG |
| 🏛️ CITATION.cff | "Cite this repository" button on the repo home |

## 📥 Downloads

| Platform | File |
|---|---|
| 🍎 macOS Apple Silicon | [`syntha_aarch64.dmg`](https://github.com/ArioMoniri/syntha/releases/download/v0.5.0/syntha_aarch64.dmg) — signed + notarized + stapled |
| 🪟 Windows x64 | [`syntha_x64-setup.exe`](https://github.com/ArioMoniri/syntha/releases/download/v0.5.0/syntha_x64-setup.exe) — unsigned for now ([see docs](https://github.com/ArioMoniri/syntha/blob/v0.5.0/docs/WINDOWS_SIGNING.md)) |
| 🐧 Linux x86_64 | [`syntha_amd64.AppImage`](https://github.com/ArioMoniri/syntha/releases/download/v0.5.0/syntha_amd64.AppImage) |
| 🐳 Docker | `docker pull ghcr.io/ariomoniri/syntha:v0.5.0` |
| 🐍 PyPI | `pip install syntha==0.5.0` (after first PyPI publish lands) |

## ⬆️ Upgrade path

- **From v0.4.x via the auto-updater**: launch your installed app; the in-app banner offers "Install & restart" automatically.
- **Fresh installs**: download from the table above.

## ⚠️ Known limitations (honest)

- **Tolerant cohort model JSON** in the Tauri app is still v0.4-fit (Spearman pipeline). The strict cohort is the one refit with the new mixed-corr method. Tolerant needs the source CSV re-ingested; tetrachoric attacks binary↔binary which strict can't exercise (strict has ~0 disease prevalence by inclusion criterion).
- **TSTR (Train-on-Synthetic / Test-on-Real) benchmark** not yet integrated — queued for v0.5.1. The dashboard advertises it; the placeholder card explains.
- **DP-SGD wrapper** (formal differential privacy) deferred to v0.5.2.

## 🤝 Clinician curation still welcome

Five v0.6 tasks waiting on input:
1. TR-specific first-line drug calibration
2. MAFLD / CKD-staging / B12 / anemia modules
3. Prevalence calibration to TÜİK
4. Turkish clinical-display review
5. ICD-10 specificity (.6X-style codes where flags carry info)

[Open a `[clinical-curation]` issue](https://github.com/ArioMoniri/syntha/issues/new?template=clinical_curation.md&labels=clinical-curation&title=%5Bclinical-curation%5D%20) — template prefilled.

## 📜 Full changelog

[CHANGELOG.md](https://github.com/ArioMoniri/syntha/blob/v0.5.0/CHANGELOG.md) — every commit in this release in conventional-commit form.

📄 Apache 2.0 © 2026 **Ariorad Moniri**
