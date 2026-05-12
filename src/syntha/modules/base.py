"""Abstract base for Synthea-style modules.

A module is given a patient row + context and returns extra FHIR resource
dicts. Modules are pure functions over the row — no shared state — which
keeps them composable and easy to test.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class ModuleContext:
    patient_id: str
    episode_iso: str  # ISO 8601 datetime for the episode
    condition_ids: dict[str, str] = field(default_factory=dict)  # flag -> Condition.id


@dataclass
class ModuleOutput:
    resources: list[dict] = field(default_factory=list)

    def add(self, resource: dict) -> None:
        self.resources.append(resource)


class SyntheaModule(ABC):
    name: str = "base"
    triggers_on: tuple[str, ...] = ()  # comorbidity flag columns

    def applies(self, row: pd.Series) -> bool:
        if not self.triggers_on:
            return False
        for flag in self.triggers_on:
            if flag in row.index:
                val = row.get(flag)
                if pd.notna(val) and int(val) == 1:
                    return True
        return False

    @abstractmethod
    def expand(self, row: pd.Series, ctx: ModuleContext) -> ModuleOutput:
        """Return the extra FHIR resources for this episode."""
