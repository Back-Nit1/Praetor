"""Public digital twin. Milestone 1: synthetic personas only; live recon arrives with Tavily."""
import os

from core.graph.build import build_graph
from core.recon.facts import fact_key, normalize_facts
from core.recon.synthetic import load_public
from core.schemas import ExposureGraph, Fact, TwinRequest


def build_twin(persona_id: str | None = None, seeds=None, attest: bool = False) -> ExposureGraph:
    if seeds is not None and os.environ.get("PRAETOR_DEMO_MODE") == "1":
        raise PermissionError("demo mode accepts synthetic personas only")
    req = TwinRequest(persona_id=persona_id, seeds=seeds, attest=attest)  # exactly one target; seeds need attest
    if req.seeds is not None:
        raise NotImplementedError("live recon is not built yet")
    return build_graph(load_public(req.persona_id), persona_id=req.persona_id)


def twin_gap(truth: list[Fact], twin: ExposureGraph) -> float:
    """Share of findable ground-truth facts the twin missed: 0.0 = complete, 1.0 = blind."""
    want = {fact_key(f) for f in normalize_facts(truth)}
    have = {(n.attrs["kind"], n.attrs["key"]) for n in twin.nodes if "key" in n.attrs}
    return len(want - have) / len(want) if want else 0.0
