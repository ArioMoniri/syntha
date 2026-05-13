<!--
Thanks for contributing to syntha! Please fill out the checklist below.
For clinician-curation PRs, see also CONTRIBUTING.md.
-->

## What this PR does

<!-- One or two sentences. Link any issue with "Closes #N". -->

## Type of change

- [ ] 🐛 Bug fix
- [ ] ✨ New feature
- [ ] 🩺 Clinical curation (drug choices, ICD codes, Turkish display strings)
- [ ] 🧪 Test-only change
- [ ] 📖 Documentation only
- [ ] 🔧 Infrastructure / CI / build
- [ ] ⚠️ Breaking change

## Checklist

- [ ] **Tests pass locally** — `PYTHONPATH=src python3 -m pytest -q`
- [ ] **New code has tests** if it changes generator behavior or FHIR output
- [ ] **No PHI** — source CSVs (`data/raw/*`) and generated outputs (`output/*`) are gitignored; nothing in this PR contains real patient data
- [ ] **Scientific changes verified** — if this changes copula math, FHIR coding, or constraint logic, the README's "what it is *not*" section + the validation report still apply, or have been updated
- [ ] **`CHANGELOG.md` updated** under `[Unreleased]` for user-visible changes
- [ ] **Conventional-commit style** in the commit subject (`feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`) so release-please can pick it up

## Screenshots / output

<!-- For UI / output changes, show before / after. -->

## Clinical sign-off (required for `🩺 Clinical curation` PRs)

<!-- If you're a clinician contributor, paste the guideline/source you used
     (e.g. TKD 2023 HTN guideline, ESC/ESH 2024, NICE NG18) and the
     specific recommendation. -->

- **Guideline source:**
- **Affected files:**
- **Why this changes the current default:**
