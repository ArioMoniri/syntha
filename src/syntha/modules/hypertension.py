"""Hypertension Synthea-style module."""
from __future__ import annotations

import pandas as pd

from ..fhir import resources as R
from ..fhir.rxnorm import ANTIHYPERTENSIVES
from .base import ModuleContext, ModuleOutput, SyntheaModule

REASON = ("38341003", "Hypertensive disorder, systemic arterial (disorder)")
VISIT_TYPE = ("390906007", "Follow-up encounter (procedure)")
LIFESTYLE = [
    ("710081004", "Dietary regime education"),
    ("1303001003", "Lifestyle counseling about cardiovascular disease prevention"),
]


class HypertensionModule(SyntheaModule):
    name = "hypertension"
    triggers_on = ("Hipertansiyon",)

    def expand(self, row: pd.Series, ctx: ModuleContext) -> ModuleOutput:
        out = ModuleOutput()
        enc = R.encounter_resource(
            ctx.patient_id, ctx.episode_iso,
            encounter_class="AMB", reason_snomed=REASON, type_snomed=VISIT_TYPE,
        )
        out.add(enc)

        # Severity heuristic: stage-2 BP → dual therapy.
        sys_ = row.get("bp_systolic")
        n_agents = 2 if (pd.notna(sys_) and sys_ >= 160) else 1
        for drug in ANTIHYPERTENSIVES[:n_agents]:
            out.add(R.medication_request_resource(
                ctx.patient_id, enc["id"], drug, ctx.episode_iso,
                reason_snomed=REASON,
            ))

        cond_ref = ctx.condition_ids.get("Hipertansiyon")
        out.add(R.careplan_resource(
            ctx.patient_id,
            title="Hypertension care plan",
            activities=LIFESTYLE,
            period_start_iso=ctx.episode_iso,
            addresses_condition_id=cond_ref,
        ))
        return out
