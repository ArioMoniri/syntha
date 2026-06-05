"""Synthea-style clinical modules.

Each module subclasses SyntheaModule and is registered in REGISTRY below. The
FHIR exporter walks REGISTRY for every episode and lets matching modules emit
additional Encounter/MedicationRequest/Procedure/CarePlan resources.
"""
from __future__ import annotations

from .asthma_copd import AsthmaModule, COPDModule
from .base import ModuleContext, ModuleOutput, SyntheaModule
from .ckd import CKDModule
from .depression_anxiety import AnxietyModule, DepressionModule
from .diabetes import DiabetesModule
from .hyperlipidemia import HyperlipidemiaModule
from .hypertension import HypertensionModule
from .ihd import IschemicHeartDiseaseModule
from .thyroid import ThyroidModule

# Order matters: list "upstream" risk factors first so reasonCode references
# remain coherent (e.g. statin Rx may cross-reference cardiovascular history).
REGISTRY: list[SyntheaModule] = [
    HypertensionModule(),
    DiabetesModule(),
    HyperlipidemiaModule(),
    ThyroidModule(),
    DepressionModule(),
    AnxietyModule(),
    IschemicHeartDiseaseModule(),
    CKDModule(),
    AsthmaModule(),
    COPDModule(),
]

__all__ = ["REGISTRY", "SyntheaModule", "ModuleContext", "ModuleOutput"]
