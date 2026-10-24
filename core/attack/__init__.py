"""Deterministic, bounded attack-path simulation over an exposure graph."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from hashlib import sha256
from math import prod

import networkx as nx

from core.personas import technique_definitions, techniques_for
from core.schemas import AttackPath, AttackStep, Edge, ExposureGraph, Node, Persona


@dataclass(frozen=True)
class _State:
    node_id: str
    edges: tuple[Edge, ...]
    effort: float


def _tokens(node: Node) -> str:
    attrs = " ".join(str(value) for value in node.attrs.values())
    return f"{node.id} {node.type} {node.label} {attrs}".lower()


def _is_target(node: Node, domain: str) -> bool:
    tokens = _tokens(node)
    kind = str(node.attrs.get("kind", "")).lower()
    if domain == "financial":
        return node.type == "asset" and any(word in tokens for word in ("fund", "bank", "money", "payment", "financial"))
    if domain == "identity":
        return node.type == "identifier" and kind in {"name", "address", "phone", "email"}
    if domain == "fraud":
        return (node.type == "account" and not node.public) or "fraud" in tokens
    if domain == "physical":
        return kind == "address" or (node.type == "asset" and "location" in tokens)
    if domain == "social":
        return node.type == "relative_token" or "social" in tokens
    if domain == "surveillance":
        return node.public and node.type in {"identifier", "account", "broker"}
    if domain == "professional":
        return kind == "employer" or any(word in tokens for word in ("employer", "workplace", "professional"))
    if domain == "inference":
        return kind == "inference" or "inference" in tokens
    return False


def _rank(seed: int, persona_id: str, round: int, edge: Edge) -> int:
    material = f"{seed}|{persona_id}|{round}|{edge.key}|{edge.rel}".encode()
    return int.from_bytes(sha256(material).digest()[:8], "big")


def _starts(graph: ExposureGraph, persona: Persona) -> list[str]:
    public = [node for node in graph.nodes if node.public]

    def priority(node: Node) -> tuple[int, int, str]:
        known = bool(node.attrs.get("known_public_context"))
        if persona.id == "insider":
            return (0 if known else 1, 0 if node.type == "account" else 1, node.id)
        return (0 if node.type == "person" else 1, 0, node.id)

    return [node.id for node in sorted(public, key=priority)]


def _find_path(graph: ExposureGraph, persona: Persona, seed: int, round: int) -> tuple[Edge, ...] | None:
    nx_graph = nx.DiGraph()
    nodes = {node.id: node for node in graph.nodes}
    nx_graph.add_nodes_from(nodes)
    for edge in graph.edges:
        nx_graph.add_edge(edge.src, edge.dst, edge=edge)

    technique_by_relation = {
        relation: technique
        for technique in technique_definitions()
        for relation in technique.relations
    }
    unlocked = set(techniques_for(round))
    skill_tolerance = min(1.0, 0.20 + 0.16 * persona.skill)
    edge_tolerance = skill_tolerance * (1.0 - 0.55 * persona.laziness)
    effort_budget = max(
        0.05,
        persona.budget_steps * ((1.0 - persona.laziness) * 0.50 + persona.skill * 0.06),
    )
    dead_ends = 0

    for start in _starts(graph, persona):
        queue = deque([_State(start, (), 0.0)])
        best_effort: dict[tuple[str, int], float] = {(start, 0): 0.0}
        while queue:
            state = queue.popleft()
            node = nodes[state.node_id]
            if state.edges and _is_target(node, persona.goal_domain):
                return state.edges
            if len(state.edges) >= persona.budget_steps:
                dead_ends += 1
                if dead_ends > persona.patience:
                    return None
                continue

            candidates = [nx_graph.edges[state.node_id, dst]["edge"] for dst in nx_graph.successors(state.node_id)]
            candidates.sort(key=lambda edge: (edge.effort, _rank(seed, persona.id, round, edge), edge.key))
            candidates = candidates[: persona.attention_k]
            advanced = False
            visited = {edge.src for edge in state.edges} | {state.node_id}
            for edge in candidates:
                technique = technique_by_relation[edge.rel]
                next_effort = state.effort + edge.effort
                if (
                    technique.id not in unlocked
                    or edge.dst in visited
                    or edge.effort > edge_tolerance
                    or next_effort > effort_budget
                ):
                    continue
                next_depth = len(state.edges) + 1
                key = (edge.dst, next_depth)
                if next_effort >= best_effort.get(key, float("inf")):
                    continue
                best_effort[key] = next_effort
                queue.append(_State(edge.dst, (*state.edges, edge), next_effort))
                advanced = True
            if not advanced:
                dead_ends += 1
                if dead_ends > persona.patience:
                    return None
    return None


def _step(edge: Edge, persona: Persona) -> AttackStep:
    technique = next(
        technique
        for technique in technique_definitions()
        if edge.rel in technique.relations
    )
    probability = technique.base_success * (0.55 + 0.09 * persona.skill) * (1.0 - 0.45 * edge.effort)
    minutes = technique.base_minutes * (1.0 + 2.0 * edge.effort) * (1.15 - 0.05 * persona.skill)
    cost = technique.base_cost_usd + edge.effort * technique.unlock_round * 2.0
    return AttackStep(
        edge_ids=[edge.key],
        action=f"Traverse the {edge.rel.replace('_', ' ')} relationship recorded in the exposure twin.",
        success_prob=round(max(0.01, min(0.99, probability)), 6),
        minutes=round(minutes, 3),
        cost_usd=round(cost, 2),
    )


def _severity(domain: str, probability: float) -> int:
    base = 3 if domain in {"financial", "physical"} else 2
    if probability >= 0.65:
        base += 1
    elif probability < 0.15:
        base -= 1
    return max(0, min(4, base))


def _financial_range(severity: int, edge_count: int) -> tuple[float, float]:
    low = float(500 * (severity + 1))
    high = float(low * (4 + edge_count / 2))
    return low, high


def _attack_path(graph: ExposureGraph, persona: Persona, edges: tuple[Edge, ...], round_number: int) -> AttackPath:
    steps = [_step(edge, persona) for edge in edges]
    probability = round(prod(step.success_prob for step in steps), 6)
    severity = _severity(persona.goal_domain, probability)
    fixes = list(dict.fromkeys(fix for edge in edges for fix in edge.fixable_by))
    digest = sha256(
        f"{graph.id}|{persona.id}|{round_number}|{'|'.join(edge.key for edge in edges)}".encode()
    ).hexdigest()[:12]
    loss_low = loss_high = None
    narrative = None
    if persona.goal_domain == "financial":
        loss_low, loss_high = _financial_range(severity, len(edges))
        narrative = "Illustrative estimate only; not financial advice."
    return AttackPath(
        id=f"attack-{persona.id}-{digest}",
        persona_id=persona.id,
        domain=persona.goal_domain,
        steps=steps,
        total_minutes=round(sum(step.minutes for step in steps), 3),
        total_cost_usd=round(sum(step.cost_usd for step in steps), 2),
        success_prob=probability,
        loss_low=loss_low,
        loss_high=loss_high,
        severity=severity,
        fixable_elements=fixes,
        narrative=narrative,
        pretext_template=None,
    )


def run_attacks(
    graph: ExposureGraph,
    personas: list[Persona],
    seed: int = 0,
    round: int = 0,
) -> list[AttackPath]:
    """Simulate one bounded, reproducible path per persona against facts in ``graph`` only."""
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    techniques_for(round)  # validate the round even when the graph or persona list is empty
    results: list[AttackPath] = []
    for persona in personas:
        edges = _find_path(graph, persona, seed, round)
        if edges:
            results.append(_attack_path(graph, persona, edges, round))
    return results


__all__ = ["run_attacks"]
