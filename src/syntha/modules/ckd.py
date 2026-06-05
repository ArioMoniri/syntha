"""Chronic kidney disease (CKD) staging Synthea-style module.

eGFR-driven: stages the patient G1–G5 per KDIGO 2024 from ``egfr_latest`` and
emits a stage-appropriate Encounter / Procedure / CarePlan. Fires on the
``Kronik_Bobrek`` source flag.

CLINICAL CONFIRMATION NEEDED (flagged in PR for clinician review):
  * KDIGO eGFR thresholds (G1 ≥ 90 … G5 < 15) are the international standard;
    confirm TR primary-care uses the same cut-points.
  * Nephrology-referral stage: implemented as **G3b and worse** (eGFR < 45).
    TR practice may refer earlier/later — confirm.
  * Albumin-creatinine-ratio (ACR) reflex testing modelled from G3a onward.
  * Nephrotoxic-drug avoidance is surfaced as a CarePlan note, not a
    MedicationRequest (the module does not yet de-prescribe).
"""
from __future__ import annotations

import pandas as pd

from ..fhir import resources as R
from ..fhir.codes import ckd_stage_for_egfr
from .base import ModuleContext, ModuleOutput, SyntheaModule

# Generic CKD reason when eGFR is missing and only the flag is set.
REASON_GENERIC = ("709044004", "Chronic kidney disease (disorder)")
NEPHRO_VISIT = ("390906007", "Follow-up encounter (procedure)")
EGFR_PROCEDURE = ("80274001", "Glomerular filtration rate (procedure)")
ACR_PROCEDURE = ("271000000", "Urine albumin/creatinine ratio measurement (procedure)")
NEPHRO_REFERRAL = ("103696004", "Patient referral to nephrologist (procedure)")

# CarePlan activities, escalating by stage.
MONITORING = ("171221003", "Chronic disease monitoring (regime/therapy)")
DIET_COUNSEL = ("284350006", "Dietary education (procedure)")
NEPHROTOXIC_AVOID = (
    "413332001",
    "Avoid nephrotoxic medication (regime/therapy)",
)

# eGFR at/below which we model a nephrology referral (G3b and worse).
REFERRAL_EGFR_THRESHOLD = 45.0
# eGFR at/below which an ACR reflex test is modelled (G3a and worse).
ACR_EGFR_THRESHOLD = 60.0


class CKDModule(SyntheaModule):
    name = "ckd"
    triggers_on = ("Kronik_Bobrek",)

    def expand(self, row: pd.Series, ctx: ModuleContext) -> ModuleOutput:
        out = ModuleOutput()

        egfr = row.get("egfr_latest")
        staged = ckd_stage_for_egfr(egfr if pd.notna(egfr) else None)
        if staged is not None:
            _stage, snomed, _icd10 = staged
            reason = snomed
        else:
            reason = REASON_GENERIC

        enc = R.encounter_resource(
            ctx.patient_id, ctx.episode_iso, "AMB", reason, NEPHRO_VISIT,
        )
        out.add(enc)

        # eGFR is always measured at the CKD encounter.
        out.add(R.procedure_resource(
            ctx.patient_id, enc["id"], ctx.episode_iso, EGFR_PROCEDURE,
        ))

        egfr_val = float(egfr) if pd.notna(egfr) else None

        # ACR reflex test from G3a (eGFR < 60).
        if egfr_val is not None and egfr_val < ACR_EGFR_THRESHOLD:
            out.add(R.procedure_resource(
                ctx.patient_id, enc["id"], ctx.episode_iso, ACR_PROCEDURE,
            ))

        # Nephrology referral at G3b and worse (eGFR < 45).
        if egfr_val is not None and egfr_val < REFERRAL_EGFR_THRESHOLD:
            out.add(R.procedure_resource(
                ctx.patient_id, enc["id"], ctx.episode_iso, NEPHRO_REFERRAL,
            ))

        activities = [MONITORING, DIET_COUNSEL, NEPHROTOXIC_AVOID]
        cond_ref = ctx.condition_ids.get("Kronik_Bobrek")
        out.add(R.careplan_resource(
            ctx.patient_id,
            title="Chronic kidney disease management plan",
            activities=activities,
            period_start_iso=ctx.episode_iso,
            addresses_condition_id=cond_ref,
        ))
        return out
