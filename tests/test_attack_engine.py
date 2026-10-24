import json
from pathlib import Path

from core.attack import run_attacks
from core.personas import load_personas, techniques_for
from core.risk import score
from core.schemas import DOMAINS, Edge, ExposureGraph, Node, Persona

FIXTURES = Path(__file__).resolve().parents[1] / "data" / "fixtures"


def pat_graph() -> ExposureGraph:
    return ExposureGraph.model_validate_json((FIXTURES / "exposure_graph.json").read_text())


def test_definitions_are_valid_and_round_unlocks_are_cumulative():
    personas = load_personas()
    assert {persona.id for persona in personas} == {
        "opportunist",
        "id_theft_reseller",
        "targeted_fraudster",
        "personal_threat",
        "insider",
    }
    assert techniques_for(0) == ["public_lookup", "public_correlation", "ownership_mapping"]
    assert techniques_for(1) == [*techniques_for(0), "recovery_mapping"]


def test_same_graph_and_seed_produce_identical_results():
    graph = pat_graph()
    personas = load_personas()
    first = run_attacks(graph, personas, seed=42, round=1)
    second = run_attacks(graph, personas, seed=42, round=1)
    assert first == second


def test_at_least_three_personas_find_paths_on_pat_fixture():
    paths = run_attacks(pat_graph(), load_personas(), seed=7)
    assert len({path.persona_id for path in paths}) >= 3


def test_opportunist_quits_on_hardened_graph():
    raw = json.loads((FIXTURES / "exposure_graph.json").read_text())
    for edge in raw["edges"]:
        edge["effort"] = 1.0
    graph = ExposureGraph.model_validate(raw)
    opportunist = next(persona for persona in load_personas() if persona.id == "opportunist")
    assert run_attacks(graph, [opportunist], seed=0, round=1) == []


def test_human_step_budget_materially_changes_traversal():
    graph = ExposureGraph(
        id="limits",
        persona_id="pat-example-01",
        nodes=[
            Node(id="person", type="person", label="Pat Example", public=True),
            Node(id="mid", type="broker", label="Example broker", public=False),
            Node(id="address", type="identifier", label="100 Example Street", attrs={"kind": "address"}, public=False),
        ],
        edges=[
            Edge(src="person", dst="mid", rel="listed_on", effort=0.1, fixable_by=["optout:mid"]),
            Edge(src="mid", dst="address", rel="reveals", effort=0.1, fixable_by=["optout:mid"]),
        ],
    )
    base = next(persona for persona in load_personas() if persona.id == "personal_threat")
    short = base.model_copy(update={"budget_steps": 1, "patience": 2})
    long = base.model_copy(update={"budget_steps": 2, "patience": 2})
    assert run_attacks(graph, [short]) == []
    assert len(run_attacks(graph, [long])) == 1


def test_every_generated_edge_and_fix_exists_on_graph():
    graph = pat_graph()
    paths = run_attacks(graph, load_personas(), seed=11, round=2)
    edge_ids = {edge.key for edge in graph.edges}
    fix_ids = {fix for edge in graph.edges for fix in edge.fixable_by}
    for path in paths:
        assert {edge_id for step in path.steps for edge_id in step.edge_ids} <= edge_ids
        assert set(path.fixable_elements) <= fix_ids
        assert path.pretext_template is None
        if path.domain == "financial":
            assert "Illustrative" in (path.narrative or "")
            assert path.loss_low is not None and path.loss_high is not None
        else:
            assert path.loss_low is None and path.loss_high is None


def risk_graph() -> ExposureGraph:
    return ExposureGraph(
        id="all-risks",
        persona_id="pat-example-01",
        nodes=[
            Node(id="person", type="person", label="Pat Example", public=True),
            Node(id="broker", type="broker", label="Example broker", public=True),
            Node(id="email", type="identifier", label="pat@example.com", attrs={"kind": "email"}, public=True),
            Node(id="account", type="account", label="Bank account", public=False),
            Node(id="funds", type="asset", label="Bank funds", public=False),
            Node(id="address", type="identifier", label="100 Example Street", attrs={"kind": "address"}, public=True),
            Node(id="relative", type="relative_token", label="relative_1", public=True),
            Node(id="social", type="account", label="Social profile", public=True),
            Node(id="employer", type="identifier", label="Example Corp", attrs={"kind": "employer"}, public=True),
            Node(id="inference", type="identifier", label="Inferred region", attrs={"kind": "inference"}, public=True),
        ],
        edges=[
            Edge(src="person", dst="broker", rel="listed_on", effort=0.1, fixable_by=["optout:broker"]),
            Edge(src="broker", dst="email", rel="reveals", effort=0.1, fixable_by=["optout:broker"]),
            Edge(src="email", dst="account", rel="verifies", effort=0.4, fixable_by=["passkey:account"]),
            Edge(src="account", dst="funds", rel="owns", effort=0.4, fixable_by=["passkey:account"]),
            Edge(src="broker", dst="address", rel="reveals", effort=0.1, fixable_by=["optout:broker"]),
            Edge(src="person", dst="relative", rel="related_to", effort=0.1, fixable_by=["optout:broker"]),
            Edge(src="person", dst="social", rel="owns", effort=0.1, fixable_by=["privacy_setting:social"]),
            Edge(src="social", dst="employer", rel="reveals", effort=0.1, fixable_by=["privacy_setting:social"]),
            Edge(src="email", dst="inference", rel="derived_from", effort=0.1, fixable_by=["alias_swap:email"]),
        ],
    )


def test_all_eight_detectors_handle_relevant_and_empty_evidence_safely():
    findings = score(risk_graph(), [])
    assert {finding.domain for finding in findings} == set(DOMAINS)
    for finding in findings:
        if finding.domain == "financial":
            assert "Illustrative" in finding.title and "not financial advice" in finding.title
            assert finding.loss_low is not None and finding.loss_high is not None
        else:
            assert finding.loss_low is None and finding.loss_high is None
    empty = ExposureGraph(id="empty", persona_id="pat-example-01")
    assert score(empty, []) == []


def test_custom_persona_is_schema_valid():
    persona = Persona(
        id="test",
        name="Test",
        goal_domain="inference",
        skill=2,
        budget_steps=2,
        patience=1,
        laziness=0.2,
        attention_k=1,
        motive="Test deterministic limits.",
    )
    assert persona.goal_domain == "inference"
