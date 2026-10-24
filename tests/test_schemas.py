import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from core.schemas import AttackPath, ExposureGraph, RoundResult, TwinRequest

FIX = Path(__file__).resolve().parents[1] / "data" / "fixtures"


def load(name, typ):
    return TypeAdapter(typ).validate_json((FIX / name).read_text())


@pytest.mark.parametrize("name,typ", [
    ("exposure_graph.json", ExposureGraph),
    ("attack_paths.json", list[AttackPath]),
    ("round_results.json", list[RoundResult]),
])
def test_fixture_round_trip(name, typ):
    ta = TypeAdapter(typ)
    obj = load(name, typ)
    assert ta.validate_json(ta.dump_json(obj)) == obj


def test_paths_reference_graph_edges():
    g = load("exposure_graph.json", ExposureGraph)
    keys = {e.key for e in g.edges}
    fix_ids = {f for e in g.edges for f in e.fixable_by}
    for p in load("attack_paths.json", list[AttackPath]):
        assert {k for s in p.steps for k in s.edge_ids} <= keys
        assert p.fixable_elements and set(p.fixable_elements) <= fix_ids


def test_guardrails():
    g = json.loads((FIX / "exposure_graph.json").read_text())
    g["edges"].append({"src": "person", "dst": "ghost", "rel": "reveals", "effort": 0.1})
    with pytest.raises(ValidationError):
        ExposureGraph.model_validate(g)

    p = json.loads((FIX / "attack_paths.json").read_text())[2]
    p["pretext_template"] = "Hi {{FIRST_NAME}}"
    with pytest.raises(ValidationError):
        AttackPath.model_validate(p)

    with pytest.raises(ValidationError):
        TwinRequest(seeds={"name": "Pat Example"})  # no attest
    with pytest.raises(ValidationError):
        TwinRequest()
    with pytest.raises(ValidationError):
        TwinRequest(persona_id="pat-example-01", password="x")  # extra fields forbidden
    assert TwinRequest(persona_id="pat-example-01").persona_id
