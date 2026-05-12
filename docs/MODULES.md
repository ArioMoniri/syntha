# Synthea-style clinical modules

Modules are the hybrid's "(B) layer" — they take a copula-sampled episode and
attach realistic clinical activity (encounters, prescriptions, procedures,
care plans) for each active comorbidity flag. They run automatically during
FHIR export unless disabled with `--no-modules`.

## Registered modules

| Module | Triggers on | Emits |
|---|---|---|
| Hypertension | `Hipertansiyon=1` | Encounter; 1 or 2 antihypertensives (stage 2 → dual therapy); CarePlan |
| Diabetes | `DM_Tum=1` or `DM_Komplikasyonlu=1` | Encounter; HbA1c Procedure; metformin; insulin if glucose ≥250 or complicated; CarePlan |
| Hyperlipidemia | `Hiperlipidemi=1` | Encounter; lipid panel Procedure; atorvastatin (or rosuvastatin if LDL ≥190) |
| Thyroid | `Tiroid=1` | Encounter; TSH Procedure; levothyroxine |
| Depression | `Depresyon=1` | Psych Encounter; sertraline; CBT CarePlan |
| Anxiety | `Anksiyete=1` | Psych Encounter; escitalopram (or buspirone if already on SSRI for depression) |
| Ischemic heart disease | `Iskemik_Kalp=1` | Cardiology Encounter; ECG; aspirin + β-blocker + statin |
| Asthma | `Astim=1` | Resp Encounter; spirometry; SABA + ICS |
| COPD | `COPD=1` | Resp Encounter; spirometry; LABA + SABA |

## Authoring a new module

```python
# src/syntha/modules/myhing.py
from .base import SyntheaModule, ModuleContext, ModuleOutput
from ..fhir import resources as R
from ..fhir.rxnorm import STATINS

class MyModule(SyntheaModule):
    name = "mything"
    triggers_on = ("MyFlagColumn",)

    def expand(self, row, ctx: ModuleContext) -> ModuleOutput:
        out = ModuleOutput()
        enc = R.encounter_resource(ctx.patient_id, ctx.episode_iso)
        out.add(enc)
        out.add(R.medication_request_resource(
            ctx.patient_id, enc["id"], STATINS[0], ctx.episode_iso))
        return out
```

Then register it in `src/syntha/modules/__init__.py` by appending to `REGISTRY`.

## Why not port Synthea's PADM directly?

Synthea's modules are JSON state machines (PADM) authored in their GUI. They
encode *progression over time* (e.g. prediabetes → diabetes → diabetic
nephropathy). Our cohort is cross-sectional — one episode per row — so a
state-machine has no temporal axis to walk. Modules here are simpler: "if
flag is set in this episode, emit the standard-of-care activity for it." The
longitudinal mode (`--longitudinal`) is the place where progression would be
added in a v2.
