"""Gate e2e: offline build_twin -> load_personas -> run_attacks -> score on pat-example-01.

Calls core modules directly. Fails on any schema violation, non-determinism, or fixture-only fallback.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

from core.twin import build_twin
from pydantic import TypeAdapter

from core.attack import run_attacks
from core.personas import load_personas
from core.risk import score
from core.schemas import AttackPath, ExposureGraph, Persona, RiskFinding

PERSONA = "pat-example-01"
FIXTURES = Path("data/fixtures")


def flow() -> tuple[ExposureGraph, list[Persona], list[AttackPath], list[RiskFinding]]:
    graph = build_twin(persona_id=PERSONA)
    personas = load_personas()
    paths = run_attacks(graph, personas, seed=0, round=0)
    return graph, personas, paths, score(graph, paths)


def validated(graph, personas, paths, findings) -> dict:
    """Round-trip every object through core.schemas; return plain JSON for hashing."""
    out = {
        "graph": ExposureGraph.model_validate_json(graph.model_dump_json()).model_dump(mode="json"),
        "personas": TypeAdapter(list[Persona]).dump_python(
            TypeAdapter(list[Persona]).validate_json(TypeAdapter(list[Persona]).dump_json(personas)), mode="json"),
        "paths": TypeAdapter(list[AttackPath]).dump_python(paths, mode="json"),
        "findings": TypeAdapter(list[RiskFinding]).dump_python(findings, mode="json"),
    }
    TypeAdapter(list[AttackPath]).validate_python(out["paths"])
    TypeAdapter(list[RiskFinding]).validate_python(out["findings"])
    return out


def main() -> int:
    os.environ.pop("NEMESIS_API_ADAPTER", None)
    first = validated(*flow())
    second = validated(*flow())
    digest = lambda o: hashlib.sha256(json.dumps(o, sort_keys=True).encode()).hexdigest()
    errors = []
    if digest(first) != digest(second):
        errors.append("non-deterministic: two runs differ")
    if not first["paths"] or not first["findings"]:
        errors.append("empty paths or findings")
    # fixture-only fallback guard: attack/risk output must be computed, not copied from fixtures
    fixture_paths = json.loads((FIXTURES / "attack_paths.json").read_text())
    if first["paths"] == fixture_paths:
        errors.append("attack paths identical to fixtures/attack_paths.json (fixture fallback)")
    if {f["id"] for f in first["findings"]} & {f"finding-{p['id']}" for p in fixture_paths}:
        errors.append("findings carry fixture adapter ids (fixture fallback)")
    for fn in (build_twin, run_attacks, score, load_personas):
        if not fn.__module__.startswith("core."):
            errors.append(f"{fn.__name__} not from core ({fn.__module__})")
    if errors:
        print("E2E FAIL:\n  " + "\n  ".join(errors), file=sys.stderr)
        return 1
    print(f"E2E OK persona={PERSONA} nodes={len(first['graph']['nodes'])} paths={len(first['paths'])} "
          f"findings={len(first['findings'])} sha256={digest(first)[:16]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
