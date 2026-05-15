"""Depression and anxiety Synthea-style modules (kept separate so prevalence
flags fire independently, but they share the SSRI prescribing pattern)."""
from __future__ import annotations

import pandas as pd

from ..fhir import resources as R
from ..fhir.rxnorm import ANXIOLYTICS, SSRIS
from .base import ModuleContext, ModuleOutput, SyntheaModule

PSYCH_VISIT = ("390906007", "Follow-up encounter (procedure)")
DEPRESSION = ("35489007", "Depressive disorder (disorder)")
ANXIETY = ("48694002", "Anxiety (finding)")
COUNSELING = [
    ("304891004", "Cognitive behavioral therapy (regime/therapy)"),
]


class DepressionModule(SyntheaModule):
    name = "depression"
    triggers_on = ("Depresyon",)

    def expand(self, row: pd.Series, ctx: ModuleContext) -> ModuleOutput:
        out = ModuleOutput()
        enc = R.encounter_resource(ctx.patient_id, ctx.episode_iso, "AMB", DEPRESSION, PSYCH_VISIT)
        out.add(enc)
        out.add(R.medication_request_resource(
            ctx.patient_id, enc["id"], SSRIS[0], ctx.episode_iso, DEPRESSION,
        ))
        out.add(R.careplan_resource(
            ctx.patient_id, "Depression management plan",
            activities=COUNSELING, period_start_iso=ctx.episode_iso,
            addresses_condition_id=ctx.condition_ids.get("Depresyon"),
        ))
        return out


class AnxietyModule(SyntheaModule):
    name = "anxiety"
    triggers_on = ("Anksiyete",)

    # Prescribing logic (per joint CMO + ML-eng review v0.5):
    #   * SSRI (escitalopram) is first-line for GAD globally.
    #   * Patients who already carry the depression flag are assumed to be
    #     on sertraline from the Depression module. To avoid dual-SSRI
    #     exposure, the Anxiety module emits buspirone (NaSSA non-SSRI
    #     anxiolytic) as the second agent on top of the existing SSRI.
    #     This is a defensible clinical pattern — SSRI continues to
    #     address mood, buspirone supplements anxiolysis without dual
    #     serotonergic load. Alternative patterns (single-SSRI for both
    #     dx, or dose-escalating SSRI) are equally defensible; this is a
    #     judgement call the CMO reviewed and accepted.
    def expand(self, row: pd.Series, ctx: ModuleContext) -> ModuleOutput:
        out = ModuleOutput()
        enc = R.encounter_resource(ctx.patient_id, ctx.episode_iso, "AMB", ANXIETY, PSYCH_VISIT)
        out.add(enc)
        already_on_ssri = (
            pd.notna(row.get("Depresyon")) and int(row.get("Depresyon", 0)) == 1
        )
        drug = ANXIOLYTICS[0] if already_on_ssri else SSRIS[1]
        out.add(R.medication_request_resource(
            ctx.patient_id, enc["id"], drug, ctx.episode_iso, ANXIETY,
        ))
        return out
