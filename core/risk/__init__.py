"""Deterministic risk detectors for every contracted damage domain."""

from __future__ import annotations

import json
from collections.abc import Callable
from hashlib import sha256

from core.schemas import DOMAINS, AttackPath, Edge, ExposureGraph, Node, RiskFinding

NodePredicate = Callable[[Node], bool]


def _tokens(node: Node) -> str:
    attrs = json.dumps(node.attrs, sort_keys=True, default=str)
    return f"{node.id} {node.type} {node.label} {attrs}".lower()


def _kind(node: Node) -> str:
    return str(node.attrs.get("kind", "")).lower()


_NODE_RULES: dict[str, NodePredicate] = {
    "financial": lambda node: (
        node.type in {"account", "asset"}
        and any(word in _tokens(node) for word in ("bank", "fund", "money", "payment", "financial"))
    ),
    "identity": lambda node: (
        (node.type == "identifier" and _kind(node) in {"name", "address", "phone", "email"})
        or (node.type == "event" and "breach" in _tokens(node))
    ),
    "fraud": lambda node: node.type == "account" or "fraud" in _tokens(node),
    "physical": lambda node: _kind(node) == "address" or "location" in _tokens(node),
    "social": lambda node: node.type == "relative_token" or "social" in _tokens(node),
    "surveillance": lambda node: node.public and node.type in {"broker", "identifier", "account"},
    "professional": lambda node: _kind(node) == "employer"
    or any(word in _tokens(node) for word in ("employer", "workplace", "professional")),
    "inference": lambda node: _kind(node) == "inference" or "inference" in _tokens(node),
}

_EDGE_RULES: dict[str, Callable[[Edge], bool]] = {
    "financial": lambda edge: edge.rel in {"recovers", "verifies", "owns"},
    "identity": lambda edge: edge.rel in {"reveals", "derived_from"},
    "fraud": lambda edge: edge.rel in {"recovers", "verifies"},
    "physical": lambda edge: edge.rel == "reveals",
    "social": lambda edge: edge.rel == "related_to",
    "surveillance": lambda edge: edge.rel in {"listed_on", "reveals", "derived_from"},
    "professional": lambda edge: edge.rel in {"reveals", "owns"},
    "inference": lambda edge: edge.rel == "derived_from",
}

_TITLES = {
    "financial": "Illustrative financial exposure estimate (not financial advice)",
    "identity": "Identity data exposure",
    "fraud": "Account fraud exposure",
    "physical": "Physical safety exposure; apply linked defensive fixes",
    "social": "Social relationship exposure",
    "surveillance": "Tracking and profiling exposure",
    "professional": "Professional-context exposure",
    "inference": "Inferred-information exposure",
}

_BASE_SEVERITY = {
    "financial": 3,
    "identity": 2,
    "fraud": 3,
    "physical": 3,
    "social": 2,
    "surveillance": 2,
    "professional": 2,
    "inference": 1,
}


def _path_evidence(paths: list[AttackPath], edge_by_key: dict[str, Edge]) -> set[str]:
    evidence: set[str] = set()
    for path in paths:
        for step in path.steps:
            for edge_id in step.edge_ids:
                edge = edge_by_key.get(edge_id)
                if edge is not None:
                    evidence.update((edge.src, edge.dst))
    return evidence


def _detector_evidence(domain: str, graph: ExposureGraph) -> set[str]:
    evidence = {node.id for node in graph.nodes if _NODE_RULES[domain](node)}
    for edge in graph.edges:
        if _EDGE_RULES[domain](edge):
            relevant_endpoint = any(
                node.id in {edge.src, edge.dst} and _NODE_RULES[domain](node)
                for node in graph.nodes
            )
            if relevant_endpoint or domain in {"fraud", "inference"}:
                evidence.update((edge.src, edge.dst))
    return evidence


def _severity(domain: str, evidence_count: int, paths: list[AttackPath]) -> int:
    if paths:
        return max(path.severity for path in paths)
    return min(4, _BASE_SEVERITY[domain] + min(1, evidence_count // 3))


def _financial_estimate(severity: int, paths: list[AttackPath]) -> tuple[float, float]:
    lows = [path.loss_low for path in paths if path.loss_low is not None]
    highs = [path.loss_high for path in paths if path.loss_high is not None]
    if lows and highs:
        return float(min(lows)), float(max(highs))
    low = float(500 * (severity + 1))
    return low, float(low * 4)


def score(graph: ExposureGraph, paths: list[AttackPath]) -> list[RiskFinding]:
    """Run all eight safe detectors and return findings only for relevant evidence."""
    edge_by_key = {edge.key: edge for edge in graph.edges}
    findings: list[RiskFinding] = []
    for domain in DOMAINS:
        domain_paths = [path for path in paths if path.domain == domain]
        evidence = _detector_evidence(domain, graph)
        evidence.update(_path_evidence(domain_paths, edge_by_key))
        if not evidence and not domain_paths:
            continue
        evidence_ids = sorted(node_id for node_id in evidence if node_id in {node.id for node in graph.nodes})
        severity = _severity(domain, len(evidence_ids), domain_paths)
        digest = sha256(
            f"{graph.id}|{domain}|{'|'.join(evidence_ids)}|{'|'.join(path.id for path in domain_paths)}".encode()
        ).hexdigest()[:12]
        loss_low = loss_high = None
        if domain == "financial":
            loss_low, loss_high = _financial_estimate(severity, domain_paths)
        findings.append(
            RiskFinding(
                id=f"risk-{domain}-{digest}",
                domain=domain,
                severity=severity,
                title=_TITLES[domain],
                evidence_node_ids=evidence_ids,
                path_ids=[path.id for path in domain_paths],
                loss_low=loss_low,
                loss_high=loss_high,
            )
        )
    return findings


__all__ = ["score"]
