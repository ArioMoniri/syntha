"""Hyperlipidemia Synthea-style module."""
from __future__ import annotations

import pandas as pd

from ..fhir import resources as R
from ..fhir.rxnorm import STATINS
from .base import ModuleContext, ModuleOutput, SyntheaModule

REASON = ("55822004", "Hyperlipidemia (disorder)")
LIPID_PANEL = ("252150000", "Lipid measurement (procedure)")
VISIT = ("185349003", "Encounter for check up (procedure)")


class HyperlipidemiaModule(SyntheaModule):
    name = "hyperlipidemia"
    triggers_on = ("Hiperlipidemi",)

    def expand(self, row: pd.Series, ctx: ModuleContext) -> ModuleOutput:
        out = ModuleOutput()
        enc = R.encounter_resource(
            ctx.patient_id, ctx.episode_iso, "AMB", REASON, VISIT,
        )
        out.add(enc)
        out.add(R.procedure_resource(ctx.patient_id, enc["id"], ctx.episode_iso, LIPID_PANEL))
        # Pick atorvastatin by default; high-intensity (rosuvastatin) if LDL > 190.
        ldl = row.get("ldl_direct_latest")
        choice = STATINS[1] if (pd.notna(ldl) and ldl >= 190) else STATINS[0]
        out.add(R.medication_request_resource(
            ctx.patient_id, enc["id"], choice, ctx.episode_iso, REASON,
        ))
        return out
