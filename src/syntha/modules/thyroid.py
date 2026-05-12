"""Thyroid disorder Synthea-style module (treats as hypothyroid by default)."""
from __future__ import annotations

import pandas as pd

from ..fhir import resources as R
from ..fhir.rxnorm import LEVOTHYROXINE
from .base import ModuleContext, ModuleOutput, SyntheaModule

REASON = ("40930008", "Hypothyroidism (disorder)")
TSH = ("3055005", "Thyroid stimulating hormone level test (procedure)")
VISIT = ("185349003", "Encounter for check up (procedure)")


class ThyroidModule(SyntheaModule):
    name = "thyroid"
    triggers_on = ("Tiroid",)

    def expand(self, row: pd.Series, ctx: ModuleContext) -> ModuleOutput:
        out = ModuleOutput()
        enc = R.encounter_resource(ctx.patient_id, ctx.episode_iso, "AMB", REASON, VISIT)
        out.add(enc)
        out.add(R.procedure_resource(ctx.patient_id, enc["id"], ctx.episode_iso, TSH))
        for drug in LEVOTHYROXINE:
            out.add(R.medication_request_resource(
                ctx.patient_id, enc["id"], drug, ctx.episode_iso, REASON,
            ))
        return out
