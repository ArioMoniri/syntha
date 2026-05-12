"""Asthma and COPD Synthea-style modules."""
from __future__ import annotations

import pandas as pd

from ..fhir import resources as R
from ..fhir.rxnorm import BRONCHODILATORS_LABA, BRONCHODILATORS_SABA, INHALED_CORTICOSTEROIDS
from .base import ModuleContext, ModuleOutput, SyntheaModule

ASTHMA = ("195967001", "Asthma (disorder)")
COPD = ("13645005", "Chronic obstructive pulmonary disease (disorder)")
RESP_VISIT = ("390906007", "Follow-up encounter (procedure)")
SPIROMETRY = ("23426006", "Spirometry (procedure)")


class AsthmaModule(SyntheaModule):
    name = "asthma"
    triggers_on = ("Astim",)

    def expand(self, row: pd.Series, ctx: ModuleContext) -> ModuleOutput:
        out = ModuleOutput()
        enc = R.encounter_resource(ctx.patient_id, ctx.episode_iso, "AMB", ASTHMA, RESP_VISIT)
        out.add(enc)
        out.add(R.procedure_resource(ctx.patient_id, enc["id"], ctx.episode_iso, SPIROMETRY))
        for drug in (BRONCHODILATORS_SABA[0], INHALED_CORTICOSTEROIDS[0]):
            out.add(R.medication_request_resource(
                ctx.patient_id, enc["id"], drug, ctx.episode_iso, ASTHMA,
            ))
        return out


class COPDModule(SyntheaModule):
    name = "copd"
    triggers_on = ("COPD",)

    def expand(self, row: pd.Series, ctx: ModuleContext) -> ModuleOutput:
        out = ModuleOutput()
        enc = R.encounter_resource(ctx.patient_id, ctx.episode_iso, "AMB", COPD, RESP_VISIT)
        out.add(enc)
        out.add(R.procedure_resource(ctx.patient_id, enc["id"], ctx.episode_iso, SPIROMETRY))
        for drug in (BRONCHODILATORS_LABA[0], BRONCHODILATORS_SABA[0]):
            out.add(R.medication_request_resource(
                ctx.patient_id, enc["id"], drug, ctx.episode_iso, COPD,
            ))
        return out
