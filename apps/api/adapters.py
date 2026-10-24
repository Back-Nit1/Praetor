"""Service adapters used by the HTTP API.

FixtureServiceAdapter is the milestone-one implementation. CoreServiceAdapter is an
explicit bridge for merged core modules; construction fails if any dependency is absent.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, ClassVar, Protocol

from pydantic import TypeAdapter

from core.schemas import (
    AttackPath,
    AttackResult,
    ExposureGraph,
    Fix,
    LedgerEntry,
    RemediationPlan,
    RiskFinding,
    RoundResult,
    Seeds,
)


class NemesisServiceAdapter(Protocol):
    def personas(self) -> list[dict[str, str]]: ...

    def build_twin(self, persona_id: str | None, seeds: Seeds | None, attest: bool) -> ExposureGraph: ...

    def attack(self, graph: ExposureGraph) -> AttackResult: ...

    def remediate(self, graph: ExposureGraph) -> RemediationPlan: ...

    def league_rounds(self, graph: ExposureGraph, rounds: int) -> list[RoundResult]: ...

    def watch_result(self) -> dict[str, Any]: ...

    def ledger(self) -> dict[str, Any]: ...


class UnknownPersonaError(LookupError):
    pass


class FixtureServiceAdapter:
    """Deterministic adapter backed only by committed, schema-validated fixtures."""

    def __init__(self, fixture_dir: str | Path) -> None:
        fixture_dir = Path(fixture_dir)
        self._graph = ExposureGraph.model_validate_json((fixture_dir / "exposure_graph.json").read_text())
        self._paths = TypeAdapter(list[AttackPath]).validate_json((fixture_dir / "attack_paths.json").read_text())
        self._rounds = TypeAdapter(list[RoundResult]).validate_json((fixture_dir / "round_results.json").read_text())

    def personas(self) -> list[dict[str, str]]:
        person = next(node for node in self._graph.nodes if node.type == "person")
        return [{"id": self._graph.persona_id, "name": person.label}]

    def build_twin(self, persona_id: str | None, seeds: Seeds | None, attest: bool) -> ExposureGraph:
        if persona_id != self._graph.persona_id:
            if seeds is not None:
                raise NotImplementedError("live scans require the core adapter; fixture data was not substituted")
            raise UnknownPersonaError(persona_id or "")
        return self._graph.model_copy(deep=True)

    def attack(self, graph: ExposureGraph) -> AttackResult:
        findings = [
            RiskFinding(
                id=f"finding-{path.id}",
                domain=path.domain,
                severity=path.severity,
                title=f"{path.domain.replace('_', ' ').title()} exposure",
                evidence_node_ids=self._evidence_nodes(path),
                path_ids=[path.id],
                loss_low=path.loss_low,
                loss_high=path.loss_high,
            )
            for path in self._paths
        ]
        return AttackResult(paths=self._copy_paths(), findings=findings)

    def remediate(self, graph: ExposureGraph) -> RemediationPlan:
        remaining = {path.id: set(path.fixable_elements) for path in self._paths}
        fixes: list[Fix] = []
        while remaining:
            counts: dict[str, int] = {}
            for candidates in remaining.values():
                for fix_id in candidates:
                    counts[fix_id] = counts.get(fix_id, 0) + 1
            if not counts:
                break
            fix_id = min(counts, key=lambda item: (-counts[item], item))
            target = fix_id.split(":", 1)[1] if ":" in fix_id else fix_id
            fixes.append(
                Fix(
                    id=fix_id,
                    kind=fix_id.split(":", 1)[0],
                    targets=[target],
                    effort_minutes=15,
                    paths_severed=counts[fix_id],
                )
            )
            remaining = {path_id: values for path_id, values in remaining.items() if fix_id not in values}
        return RemediationPlan(
            fixes=fixes,
            paths_before=len(self._paths),
            paths_after=len(remaining),
            method="greedy",
            residual_notes="Fixture-backed estimate; procedures are populated by the core adapter.",
        )

    def league_rounds(self, graph: ExposureGraph, rounds: int) -> list[RoundResult]:
        return [self._rounds[min(index, len(self._rounds) - 1)].model_copy(update={"round": index}) for index in range(rounds)]

    def watch_result(self) -> dict[str, Any]:
        return {"findings": len(self._paths), "source": "fixture"}

    def ledger(self) -> dict[str, Any]:
        return {"entries": [], "verified": True, "summary": {"entries": 0, "bytes": 0, "by_service": {}}}

    def _copy_paths(self) -> list[AttackPath]:
        return [path.model_copy(deep=True) for path in self._paths]

    @staticmethod
    def _evidence_nodes(path: AttackPath) -> list[str]:
        node_ids: list[str] = []
        for step in path.steps:
            for edge_id in step.edge_ids:
                source, destination = edge_id.split("->", 1)
                for node_id in (source, destination):
                    if node_id not in node_ids:
                        node_ids.append(node_id)
        return node_ids


class CoreServiceAdapter:
    """Strict bridge to real core modules, with no fixture fallback."""

    _REQUIRED: ClassVar[dict[str, tuple[str, str]]] = {
        "twin": ("core.twin", "build_twin"),
        "personas": ("core.personas", "load_personas"),
        "attack": ("core.attack", "run_attacks"),
        "risk": ("core.risk", "score"),
        "remediate": ("core.remediate", "plan"),
        "league": ("core.league", "run_league"),
        "watch": ("core.watch", "run_watch"),
    }

    def __init__(self) -> None:
        self._functions: dict[str, Any] = {}
        for name, (module_name, function_name) in self._REQUIRED.items():
            module = importlib.import_module(module_name)
            function = getattr(module, function_name, None)
            if not callable(function):
                raise TypeError(f"core adapter requires callable {module_name}.{function_name}")
            self._functions[name] = function

    def personas(self) -> list[dict[str, str]]:
        return [{"id": persona.id, "name": persona.name} for persona in self._functions["personas"]()]

    def build_twin(self, persona_id: str | None, seeds: Seeds | None, attest: bool) -> ExposureGraph:
        return self._functions["twin"](persona_id=persona_id, seeds=seeds, attest=attest)

    def attack(self, graph: ExposureGraph) -> AttackResult:
        paths = self._functions["attack"](graph, self._functions["personas"]())
        return AttackResult(paths=paths, findings=self._functions["risk"](graph, paths))

    def remediate(self, graph: ExposureGraph) -> RemediationPlan:
        return self._functions["remediate"](self.attack(graph).paths)

    def league_rounds(self, graph: ExposureGraph, rounds: int) -> list[RoundResult]:
        return self._functions["league"](graph, rounds)

    def watch_result(self) -> dict[str, Any]:
        findings = self._functions["watch"]()
        return {"findings": [finding.model_dump(mode="json") for finding in findings]}

    def ledger(self) -> dict[str, Any]:
        module = importlib.import_module("core.ledger")
        required = ("entries", "verify_chain", "summary")
        if any(not callable(getattr(module, name, None)) for name in required):
            raise RuntimeError("core adapter requires core.ledger entries, verify_chain, and summary")
        entries = TypeAdapter(list[LedgerEntry]).validate_python(module.entries())
        return {
            "entries": [entry.model_dump(mode="json") for entry in entries],
            "verified": module.verify_chain(),
            "summary": module.summary(),
        }
