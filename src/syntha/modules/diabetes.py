"""Type-2 diabetes Synthea-style module."""
from __future__ import annotations

import pandas as pd

from ..fhir import resources as R
from ..fhir.rxnorm import ANTIDIABETICS_FIRST_LINE, ANTIDIABETICS_INSULIN
from .base import ModuleContext, ModuleOutput, SyntheaModule

REASON = ("73211009", "Diabetes mellitus (disorder)")
VISIT = ("103693007", "Diagnostic procedure (procedure)")
HBA1C = ("313835008", "Hemoglobin A1c measurement (procedure)")
LIFESTYLE = [
    ("443846001", "Glucose monitoring at home (regime/therapy)"),
    ("11816003",  "Diet education"),
]


class DiabetesModule(SyntheaModule):
    name = "diabetes"
    triggers_on = ("DM_Tum", "DM_Komplikasyonlu")

    def expand(self, row: pd.Series, ctx: ModuleContext) -> ModuleOutput:
        out = ModuleOutput()
        enc = R.encounter_resource(
            ctx.patient_id, ctx.episode_iso, "AMB", REASON, VISIT,
        )
        out.add(enc)

        out.add(R.procedure_resource(
            ctx.patient_id, enc["id"], ctx.episode_iso, HBA1C,
        ))

        # Glucose-driven choice: very high fasting glucose triggers insulin.
        glu = row.get("glucose_fasting_latest")
        complicated = pd.notna(row.get("DM_Komplikasyonlu")) and int(row.get("DM_Komplikasyonlu")) == 1
        if (pd.notna(glu) and glu >= 250) or complicated:
            for drug in ANTIDIABETICS_INSULIN:
                out.add(R.medication_request_resource(
                    ctx.patient_id, enc["id"], drug, ctx.episode_iso, REASON,
                ))
        for drug in ANTIDIABETICS_FIRST_LINE:
            out.add(R.medication_request_resource(
                ctx.patient_id, enc["id"], drug, ctx.episode_iso, REASON,
            ))

        cond_ref = ctx.condition_ids.get("DM_Tum") or ctx.condition_ids.get("DM_Komplikasyonlu")
        out.add(R.careplan_resource(
            ctx.patient_id, title="Diabetes self-management plan",
            activities=LIFESTYLE, period_start_iso=ctx.episode_iso,
            addresses_condition_id=cond_ref,
        ))
        return out
