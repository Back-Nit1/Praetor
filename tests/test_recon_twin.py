import json
import random
import re
from pathlib import Path

import networkx as nx
import pytest
from pydantic import TypeAdapter

from core.graph.build import build_graph
from core.recon.facts import normalize_facts
from core.recon.synthetic import ROOT, list_personas, load_public, load_truth
from core.schemas import ExposureGraph, Fact
from core.twin import build_twin, twin_gap

IDS = ["pat-example-01", "robin-sample-02", "casey-placeholder-03"]
FIXTURE = TypeAdapter(ExposureGraph).validate_json(
    (Path(__file__).resolve().parents[1] / "data/fixtures/exposure_graph.json").read_bytes())


def fact(kind, value, source_kind="broker", url="https://peoplesearch.example.com/x", conf=0.9, id="f"):
    return Fact(id=id, kind=kind, value=value, source_url=url, source_kind=source_kind, confidence=conf)


def digraph(g):
    return nx.DiGraph([(e.src, e.dst) for e in g.edges])


@pytest.mark.parametrize("pid", IDS)
def test_persona_builds(pid):
    g = build_twin(persona_id=pid)
    assert g.persona_id == pid and g.id == f"g-{pid}"
    assert any(n.type == "person" for n in g.nodes) and g.edges


def test_three_personas_listed():
    assert [p["id"] for p in list_personas()] == sorted(IDS)


@pytest.mark.parametrize("pid", IDS)
def test_deterministic_any_order(pid):
    facts = load_public(pid)
    shuffled = random.Random(1).sample(facts, len(facts))
    a, b = build_graph(facts, pid), build_graph(shuffled, pid)
    assert a.model_dump_json() == b.model_dump_json() == build_twin(persona_id=pid).model_dump_json()


@pytest.mark.parametrize("pid", IDS)
def test_edges_and_fixes_valid(pid):
    g = build_twin(persona_id=pid)
    ids = [n.id for n in g.nodes]
    assert len(ids) == len(set(ids))
    keys = [e.key for e in g.edges]
    assert len(keys) == len(set(keys))
    for e in g.edges:
        assert e.src in ids and e.dst in ids and e.src != e.dst
        assert 0 <= e.effort <= 1
        for fx in e.fixable_by:  # <kind>:<target_node_id>
            kind, target = fx.split(":", 1)
            assert kind and target in ids, fx


EMAIL = re.compile(r"[\w.+-]+@([\w.-]+)")
URL = re.compile(r"https?://([\w.-]+)")


@pytest.mark.parametrize("pid", IDS)
def test_reserved_synthetic_values(pid):
    for f in sorted((ROOT / pid).glob("*.json")):
        text = f.read_text()
        for dom in EMAIL.findall(text) + URL.findall(text):
            assert dom.endswith(("example.com", "example.org")), (f, dom)
        for phone in re.findall(r"\b\d{3}[- ]\d{4}\b", text):
            assert re.fullmatch(r"555[- ]01\d\d", phone), (f, phone)
        for addr in re.findall(r"\b\d+ [A-Z]\w+ (?:Street|Avenue|Ave|Road)\b", text):
            assert " Example " in addr, (f, addr)
        assert not re.search(r"password|ssn|passwd|credit", text, re.IGNORECASE)


def test_relatives_only_tokens():
    for pid in IDS:
        g = build_twin(persona_id=pid)
        rel = [n for n in g.nodes if n.type == "relative_token"]
        assert all(re.fullmatch(r"relative_\d+", n.id) and n.label == n.id and not n.attrs.get("value") for n in rel)
        raw = {f.value for f in load_public(pid) if f.kind == "relative_token"}
        dump = g.model_dump_json()
        assert not [r for r in raw if not r.startswith("relative_") and r in dump]
    assert len([n for n in build_twin(persona_id="robin-sample-02").nodes if n.type == "relative_token"]) == 2
    out = normalize_facts([fact("relative_token", "  Zed   Example "), fact("relative_token", "relative_1", id="g")])
    assert {f.value for f in out} == {"relative_1", "relative_2"}
    assert all("Zed" not in f.id + f.value for f in out)


def test_private_truth_not_exposed():
    for pid in IDS:
        private = json.loads((ROOT / pid / "truth.json").read_text())["private"]
        dump = build_twin(persona_id=pid).model_dump_json() + (ROOT / pid / "public.json").read_text()
        assert private and not [f["value"] for f in private if f["value"] in dump]


def test_normalize_dedupes():
    out = normalize_facts([
        fact("phone", "(555) 555-0142", id="a"), fact("phone", "555 555 0142", id="b", conf=0.5),
        fact("email", "A@Example.com", id="c"), fact("email", "a@example.com", id="d", conf=0.5),
        fact("address", "1 Example St.", id="e"), fact("address", "1 example street", id="f", conf=0.5),
        fact("phone", "555-0142", source_kind="breach", url="https://x.example.org/b", id="g"),
    ])
    assert sorted((f.kind, f.value, f.source_kind) for f in out) == [
        ("address", "1 Example St.", "broker"), ("email", "a@example.com", "broker"),
        ("phone", "555-0142", "breach"), ("phone", "555-555-0142", "broker")]
    assert normalize_facts(out) == out


def test_live_seeds_need_attest_and_not_demo(monkeypatch):
    seeds = {"name": "Pat Example", "emails": ["pat.example@example.com"]}
    with pytest.raises(ValueError, match="attest"):
        build_twin(seeds=seeds)
    with pytest.raises(NotImplementedError):  # attested: valid, but live recon is not built yet
        build_twin(seeds=seeds, attest=True)
    with pytest.raises(ValueError):
        build_twin(persona_id="pat-example-01", seeds=seeds, attest=True)
    with pytest.raises(ValueError):
        build_twin()
    monkeypatch.setenv("PRAETOR_DEMO_MODE", "1")
    for attest in (True, False):
        with pytest.raises(PermissionError, match="demo"):
            build_twin(seeds=seeds, attest=attest)
    assert build_twin(persona_id="pat-example-01").persona_id == "pat-example-01"


@pytest.mark.parametrize("bad", ["../etc/passwd", "nobody", "pat-example-01/../x"])
def test_unknown_persona_rejected(bad):
    with pytest.raises(ValueError, match="unknown"):
        build_twin(persona_id=bad)


def test_pat_matches_contract_fixture():
    g = build_twin(persona_id="pat-example-01")
    shape = lambda x: ({(n.id, n.type, n.public) for n in x.nodes},
                       {(e.key, e.rel, e.effort, tuple(e.fixable_by)) for e in x.edges})
    assert shape(g) == shape(FIXTURE)


def test_pat_attack_paths():
    d = digraph(build_twin(persona_id="pat-example-01"))
    for chain in (["person", "broker_peoplesearch", "phone", "acct_email", "acct_bank", "asset_funds"],
                  ["person", "broker_peoplesearch", "address", "asset_location"],
                  ["person", "acct_social", "employer"]):
        assert nx.is_path(d, chain), chain
    d.remove_node("broker_peoplesearch")  # opt-out cuts the physical chain; funds stay reachable via the breached email
    assert not nx.has_path(d, "person", "asset_location")
    assert nx.has_path(d, "person", "asset_funds") and not nx.has_path(d, "person", "phone")


def test_other_personas_shapes():
    r = digraph(build_twin(persona_id="robin-sample-02"))
    assert nx.has_path(r, "person", "asset_funds") and nx.has_path(r, "photo_meta", "asset_location")
    g = build_twin(persona_id="robin-sample-02")
    loc = next(e for e in g.edges if e.key == "address->asset_location")
    assert loc.fixable_by == ["optout:broker_findfolks", "optout:broker_peoplesearch"]  # two brokers expose it
    c = build_twin(persona_id="casey-placeholder-03")
    assert not any(n.type == "broker" for n in c.nodes)
    assert next(e for e in c.edges if e.key == "address->asset_location").fixable_by == []  # unfixable residual


def test_twin_gap():
    assert twin_gap(load_truth("pat-example-01"), build_twin(persona_id="pat-example-01")) == 0.0
    assert twin_gap(load_truth("robin-sample-02"), build_twin(persona_id="robin-sample-02")) == 0.0
    gap = twin_gap(load_truth("casey-placeholder-03"), build_twin(persona_id="casey-placeholder-03"))
    assert 0 < gap < 1
    assert twin_gap([], build_twin(persona_id="pat-example-01")) == 0.0
