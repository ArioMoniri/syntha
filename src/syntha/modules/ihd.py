"""Ischemic heart disease Synthea-style module."""
from __future__ import annotations

import pandas as pd

from ..fhir import resources as R
from ..fhir.rxnorm import ANTIPLATELETS, BETA_BLOCKERS, STATINS
from .base import ModuleContext, ModuleOutput, SyntheaModule

REASON = ("414545008", "Ischemic heart disease (disorder)")
CARD_VISIT = ("390906007", "Follow-up encounter (procedure)")
ECG = ("29303009", "Electrocardiographic procedure (procedure)")


class IschemicHeartDiseaseModule(SyntheaModule):
    name = "ihd"
    triggers_on = ("Iskemik_Kalp",)

    def expand(self, row: pd.Series, ctx: ModuleContext) -> ModuleOutput:
        out = ModuleOutput()
        enc = R.encounter_resource(ctx.patient_id, ctx.episode_iso, "AMB", REASON, CARD_VISIT)
        out.add(enc)
        out.add(R.procedure_resource(ctx.patient_id, enc["id"], ctx.episode_iso, ECG))
        for drug in (ANTIPLATELETS[0], BETA_BLOCKERS[0], STATINS[0]):
            out.add(R.medication_request_resource(
                ctx.patient_id, enc["id"], drug, ctx.episode_iso, REASON,
            ))
        return out
