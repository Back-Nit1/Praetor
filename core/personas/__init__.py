"""Validated deterministic attacker persona and technique definitions."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from core.schemas import EdgeRel, Persona

_HERE = Path(__file__).resolve().parent


class _DefinitionFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    personas: list[Persona]

    @model_validator(mode="after")
    def _unique_contracted_personas(self):
        expected = {
            "opportunist",
            "id_theft_reseller",
            "targeted_fraudster",
            "personal_threat",
            "insider",
        }
        ids = [persona.id for persona in self.personas]
        if len(ids) != len(set(ids)):
            raise ValueError("persona ids must be unique")
        if set(ids) != expected:
            raise ValueError("persona definitions must contain exactly the five contracted ids")
        return self


class Technique(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    unlock_round: int = Field(ge=0)
    relations: list[EdgeRel] = Field(min_length=1)
    base_minutes: float = Field(ge=0)
    base_cost_usd: float = Field(ge=0)
    base_success: float = Field(gt=0, le=1)


class _TechniqueFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    techniques: list[Technique]

    @model_validator(mode="after")
    def _complete_tree(self):
        ids = [technique.id for technique in self.techniques]
        if len(ids) != len(set(ids)):
            raise ValueError("technique ids must be unique")
        relations = [relation for technique in self.techniques for relation in technique.relations]
        if len(relations) != len(set(relations)):
            raise ValueError("each edge relation must map to one technique")
        expected = set(TypeAdapter(EdgeRel).json_schema()["enum"])
        if set(relations) != expected:
            raise ValueError("technique tree must cover every contracted edge relation")
        return self


def _yaml(path: Path) -> object:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_personas() -> list[Persona]:
    """Load and validate the five contracted attacker personas."""
    definitions = _DefinitionFile.model_validate(_yaml(_HERE / "personas.yaml"))
    return [persona.model_copy(deep=True) for persona in definitions.personas]


def technique_definitions() -> tuple[Technique, ...]:
    """Return validated technique metadata for the deterministic engine."""
    definitions = _TechniqueFile.model_validate(_yaml(_HERE / "techniques.yaml"))
    return tuple(definitions.techniques)


def techniques_for(round: int) -> list[str]:
    """Return cumulative technique ids unlocked through ``round``."""
    if isinstance(round, bool) or not isinstance(round, int):
        raise TypeError("round must be an integer")
    if round < 0:
        raise ValueError("round must be non-negative")
    return [
        technique.id
        for technique in technique_definitions()
        if technique.unlock_round <= round
    ]


__all__ = ["load_personas", "techniques_for"]
