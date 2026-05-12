# Contributing to syntha 🩺

Thanks for your interest in improving syntha. The most valuable contributions fall in three buckets:

## 1. 🧑‍⚕️ Clinical curation (medical doctors most welcome!)

We genuinely need clinician eyes on:

- **First-line drug choices** per module (`src/syntha/modules/`). The defaults are international guideline-typical, but Turkish clinical practice differs in spots (perindopril for hypertension, nebivolol prevalence, dual-PPI use, etc.).
- **Turkish display strings** for SNOMED concepts (`src/syntha/locale/turkish.py`). Are they clinical-Turkish or too literal?
- **ICD-10 codes** mapped from the source comorbidity flags (`src/syntha/fhir/codes.py`). The current mapping uses unspecified-form ICD-10 codes; specifying further (e.g. `E11.65` vs `E11.9`) would improve downstream realism.
- **New modules** for high-prevalence conditions not yet covered (CKD staging, MAFLD, anemia, B12 deficiency — relevant given the source lab columns).
- **Prevalence calibration** against Turkish national statistics (TÜİK / TURKSTAT).

If you don't want to write code:

> Open an issue with the title **`[clinical-curation] <topic>`** and paste your guidance. We'll implement it.

If you want to write code: follow the *dev* section below.

## 2. 🐛 Bug reports

Open an issue with:
- Steps to reproduce.
- The synthetic-CSV / FHIR output that surprised you (a small snippet is enough — please do **not** attach real PHI).
- Expected vs actual behavior.

## 3. 🧪 Dev

### Setup

```bash
git clone https://github.com/ArioMoniri/syntha.git
cd syntha
pip install -e ".[dev]"
```

### Run tests

```bash
pytest -q
```

All tests must pass before a PR is reviewable. CI runs the matrix `Py 3.10 → 3.13`.

### Run the full pipeline locally

```bash
bash scripts/ingest_csvs.sh        # one-time, with WhatsApp paths (or override $STRICT_SRC / $TOLERANT_SRC)
N=1000 bash scripts/run_full_pipeline.sh
```

### Project conventions

- **No PHI ever** enters the repo. `data/raw/*` and `output/*` are gitignored.
- Source files stay **under 500 lines**.
- Public APIs are **typed**.
- New modules go in `src/syntha/modules/` and are registered in `src/syntha/modules/__init__.py`.
- New ICD-10 / SNOMED / RxNorm / LOINC codes go in the corresponding table under `src/syntha/fhir/`.

### Adding a Synthea-style module

```python
# src/syntha/modules/mything.py
from .base import SyntheaModule, ModuleContext, ModuleOutput
from ..fhir import resources as R

class MyModule(SyntheaModule):
    name = "mything"
    triggers_on = ("MyFlagColumn",)

    def expand(self, row, ctx: ModuleContext) -> ModuleOutput:
        out = ModuleOutput()
        enc = R.encounter_resource(ctx.patient_id, ctx.episode_iso)
        out.add(enc)
        # ... add MedicationRequest, Procedure, CarePlan as needed
        return out
```

Then append `MyModule()` to `REGISTRY` in `src/syntha/modules/__init__.py` and add a test in `tests/test_modules.py`.

## Code of conduct

Be kind, be specific, assume the other person has read the issue. Anything else: see [Contributor Covenant 2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).
