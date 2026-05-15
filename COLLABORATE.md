# 🤝 Collaborate on syntha

`syntha` is open-source under Apache 2.0 and built to be **collaborative**. There are concrete tasks where clinical, statistical, and engineering input would materially improve the project, and the desktop app surfaces them live.

This file lists *what's needed*, *who can help*, and *how*. The same list is fetched live from the GitHub Issues tracker by the **Collaborate** panel in the desktop app — pick a task there, type your GitHub handle, and the app opens the relevant issue in your browser with a one-click claim comment pre-filled.

---

## The collaboration platform

`syntha` does **not** run its own server or accept account sign-ups — that would add infrastructure, privacy obligations, and maintenance overhead with no actual benefit over what GitHub already provides. Instead, GitHub is the platform:

- **Identity** — your GitHub handle (we never store passwords; only your typed handle is kept in `localStorage` so the app can pre-fill claim comments).
- **Tasks** — open Issues with the `help-wanted-clinician`, `help-wanted-dev`, or `help-wanted-data` label.
- **Claiming** — a comment with `@your-handle is claiming this — ETA <when>`. The app generates the deep-link.
- **Discussion** — GitHub Discussions for proposals, questions, and "is this the right tool for X?"
- **Code review** — Pull Requests with the CODEOWNERS auto-assigned.
- **Recognition** — [all-contributors](https://allcontributors.org/) emoji table in the README.

This means everything works **offline-first**: the desktop app caches the issue list locally; if you have a GitHub PAT it can authenticate (higher rate limits) but anonymous browsing is the default.

---

## Who can help with what

### 🧑‍⚕️ Clinicians (Turkish primary-care, internal medicine, family medicine)

These tasks need someone with Turkish clinical practice knowledge. Most are 30–60 min of reading + a paragraph of guidance — the implementation is on us.

| Task | What we need from you | Touches |
|---|---|---|
| First-line drug calibration | Confirm or correct the default drug per module (HTN, DM, hyperlipidemia, IHD, depression, anxiety, thyroid, asthma, COPD) against Turkish guidelines (TKD, Türk Hipertansiyon Uzlaşı Raporu, etc.) | `src/syntha/modules/*.py`, `src/syntha/fhir/rxnorm.py` |
| ICD-10 specificity | The current map uses unspecified `.9` forms. Where the source flag carries enough information, suggest the specific code (e.g. `E11.65` for DM with hyperglycemia) | `src/syntha/fhir/codes.py` |
| TR display strings | Confirm clinical-Turkish preferred terms match `Türk Tabipleri Birliği` usage rather than literal translation | `src/syntha/locale/turkish.py` |
| New module: CKD staging | eGFR-driven (G1–G5) — what therapy / monitoring at each stage in TR primary care? | new module under `src/syntha/modules/` |
| New module: MAFLD | ALT/AST + obesity-driven — what's the TR-specific workup? | new module |
| New module: anemia | Hb-driven; what TR primary-care reflex panel triggers? | new module |
| New module: B12 deficiency | vit B12 column is present in source; what's the TR-typical threshold + replacement protocol? | new module |
| Prevalence calibration | Validate synthetic disease rates against TÜİK national figures; flag any mismatches > 5 percentage points | adjusts `binary_p` in the model card before sampling |
| Reference-range review | Confirm the sex-aware reference intervals for the 14 labs match the panel used in your hospital | `src/syntha/reference_ranges.py` |

### 💻 Developers (Python / TypeScript / Rust)

| Task | Skill |
|---|---|
| CTGAN / TVAE backend behind `--engine ctgan` | Python, generative models |
| Differential-privacy wrapper (Gaussian mechanism on marginals + correlations) | Python, DP |
| PADM-style state machines for chronic-disease progression | Python |
| TSTR benchmark via SynthEHRella | Python, sklearn / XGBoost |
| Vite 8 + TypeScript 6 desktop-app upgrade | TypeScript |
| Mobile (Tauri 2 mobile) build | Rust + TS |

### 📊 Data scientists / statisticians

| Task | Skill |
|---|---|
| Validate the polyserial / tetrachoric implementation against R's `polycor` on a synthetic test suite | R + Python |
| Sensitivity analysis on `lab_drift_scale` (currently fixed at 5%) per lab | EHR time-series |
| Population calibration to TÜİK with poststratification weights | Survey statistics |

---

## How to claim a task

### From the desktop app (easiest)

1. Open the syntha desktop app.
2. Click **Collaborate** in the sidebar.
3. Type your GitHub handle once — it's remembered locally for next time.
4. Pick a card. Hit **Claim this**.
5. The app opens the GitHub Issue in your browser with a pre-filled comment so the maintainers know you've started.

### From the web

1. Browse open issues with the relevant label:
   - 🧑‍⚕️ [help-wanted-clinician](https://github.com/ArioMoniri/syntha/labels/help-wanted-clinician)
   - 💻 [help-wanted-dev](https://github.com/ArioMoniri/syntha/labels/help-wanted-dev)
   - 📊 [help-wanted-data](https://github.com/ArioMoniri/syntha/labels/help-wanted-data)
2. Comment on the one you'd like to take. The CODEOWNERS file pings the maintainer automatically.

### Opening a new clinical-curation issue

[🧑‍⚕️ One-click issue template](https://github.com/ArioMoniri/syntha/issues/new?template=clinical_curation.md&labels=help-wanted-clinician&title=%5Bclinical-curation%5D%20)

---

## What you get for contributing

- Credit in the [all-contributors](https://allcontributors.org/) table in the README (with the emoji that matches your contribution kind — code, doc, ideas, review, …).
- Authorship on the v1.0 methods paper for substantive clinical or methodological contributions (clinicians who calibrate a module against TR guidelines, statisticians who add the DP wrapper, etc.). The threshold is: a real change that survives review.
- Direct review from the maintainer within 72 h on weekdays.

---

## Code of conduct

This project follows the [Contributor Covenant 2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). Be kind, be specific, no PHI.

---

## Contact

- 🐛 [Issues](https://github.com/ArioMoniri/syntha/issues) — bug reports + feature requests + clinical curation
- 🗨️ [Discussions](https://github.com/ArioMoniri/syntha/discussions) — open-ended proposals
- 📧 The maintainer responds on the issue tracker; no email gate.
