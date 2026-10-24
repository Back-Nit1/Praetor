"""Nemesis shared contracts (plan.md §5). Owned by T0 — request changes in docs/STATUS/<you>.md.

Guardrail: no credential fields (password, SSN, card, ID numbers) may ever be added here.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SIM_MARK = "SIMULATION"


def now() -> datetime:
    return datetime.now(UTC)


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


Prob = Field(ge=0.0, le=1.0)
Severity = Field(ge=0, le=4)

FactKind = Literal[
    "name", "address", "phone", "email", "handle", "employer", "relative_token",
    "account", "breach", "photo_meta", "listing", "inference",
]
SourceKind = Literal["broker", "breach", "social", "public_record", "search"]
NodeType = Literal["person", "identifier", "account", "broker", "service", "asset", "relative_token", "event"]
EdgeRel = Literal["listed_on", "recovers", "verifies", "reveals", "derived_from", "owns", "related_to"]
Domain = Literal["financial", "identity", "fraud", "physical", "social", "surveillance", "professional", "inference"]
DOMAINS: tuple[str, ...] = Domain.__args__  # type: ignore[attr-defined]


# ---------- twin ----------
class Fact(Model):
    id: str
    kind: FactKind
    value: str
    source_url: str | None = None
    source_kind: SourceKind
    confidence: float = Prob
    found_at: datetime = Field(default_factory=now)


class Node(Model):
    id: str
    type: NodeType
    label: str
    attrs: dict = Field(default_factory=dict)
    public: bool = True


class Edge(Model):
    src: str
    dst: str
    rel: EdgeRel
    effort: float = Prob  # attacker cost, 0 = free
    fixable_by: list[str] = Field(default_factory=list)  # Fix ids from core/remediate catalog

    @property
    def key(self) -> str:
        """Edge id used by AttackStep.edge_ids and Fix.targets."""
        return f"{self.src}->{self.dst}"


class ExposureGraph(Model):
    id: str
    persona_id: str  # synthetic persona id, or "self" for an attested live scan
    nodes: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)
    built_at: datetime = Field(default_factory=now)

    @model_validator(mode="after")
    def _edges_reference_nodes(self):
        ids = {n.id for n in self.nodes}
        bad = [(e.src, e.dst) for e in self.edges if e.src not in ids or e.dst not in ids]
        if bad:
            raise ValueError(f"edges reference unknown nodes: {bad[:3]}")
        return self


# ---------- attack ----------
class Persona(Model):
    id: str
    name: str
    goal_domain: Domain
    skill: int = Field(ge=1, le=5)
    budget_steps: int = Field(ge=1)
    patience: int = Field(ge=0)  # dead ends tolerated before quitting
    laziness: float = Prob
    attention_k: int = Field(ge=1)  # leads visible per step
    tools: list[str] = Field(default_factory=list)
    motive: str


class AttackStep(Model):
    edge_ids: list[str]  # Edge.key values ("src->dst")
    action: str
    success_prob: float = Prob
    minutes: float = Field(ge=0)
    cost_usd: float = Field(ge=0)


class AttackPath(Model):
    id: str
    persona_id: str
    domain: Domain
    steps: list[AttackStep]
    total_minutes: float = Field(ge=0)
    total_cost_usd: float = Field(ge=0)
    success_prob: float = Prob
    loss_low: float | None = None  # financial only, illustrative, not financial advice
    loss_high: float | None = None
    severity: int = Severity
    fixable_elements: list[str]  # Fix ids
    narrative: str | None = None
    pretext_template: str | None = None  # placeholders only, must carry SIM_MARK

    @model_validator(mode="after")
    def _guardrails(self):
        if self.pretext_template is not None and SIM_MARK not in self.pretext_template:
            raise ValueError(f"pretext_template must contain '{SIM_MARK}'")
        if (self.loss_low is not None or self.loss_high is not None) and self.domain != "financial":
            raise ValueError("loss ranges are for the financial domain only")
        return self


class RiskFinding(Model):
    id: str
    domain: Domain
    severity: int = Severity
    title: str
    evidence_node_ids: list[str] = Field(default_factory=list)
    path_ids: list[str] = Field(default_factory=list)
    loss_low: float | None = None
    loss_high: float | None = None


# ---------- remediation ----------
class Fix(Model):
    id: str
    # optout|alias_swap|recovery_change|freeze|privacy_setting|delete_account|passkey|rotate_security_qa|...
    # open set; T4's core/remediate/catalog.yaml is the source of truth.
    kind: str
    targets: list[str] = Field(default_factory=list)  # node ids / edge keys
    effort_minutes: float = Field(ge=0)
    paths_severed: int = Field(default=0, ge=0)
    procedure: str | None = None  # from Tavily lookup
    draft: str | None = None  # placeholders only; drafted, never submitted


class RemediationPlan(Model):
    fixes: list[Fix]  # ordered
    paths_before: int = Field(ge=0)
    paths_after: int = Field(ge=0)
    method: Literal["milp", "greedy"]
    residual_notes: str = ""


class RoundResult(Model):
    round: int = Field(ge=0)
    paths_remaining: int = Field(ge=0)
    by_persona: dict[str, int] = Field(default_factory=dict)
    fixes_applied: list[str] = Field(default_factory=list)
    unlocked_techniques: list[str] = Field(default_factory=list)


# ---------- ledger ----------
class LedgerEntry(Model):
    id: int
    ts: datetime = Field(default_factory=now)
    service: Literal["tokenfactory", "tavily", "nebius_job"]
    purpose: str
    bytes: int = Field(ge=0)
    payload_sha256: str
    redactions: int = Field(default=0, ge=0)
    prev_hash: str
    hash: str


# ---------- API bodies ----------
class Seeds(Model):
    """The USER's own identifiers only. Never a third party."""
    name: str
    city: str | None = None
    emails: list[str] = Field(default_factory=list)
    handles: list[str] = Field(default_factory=list)


class TwinRequest(Model):
    persona_id: str | None = None
    seeds: Seeds | None = None
    attest: bool = False  # "these seeds are about me"

    @model_validator(mode="after")
    def _one_target(self):
        if (self.persona_id is None) == (self.seeds is None):
            raise ValueError("give exactly one of persona_id or seeds")
        if self.seeds is not None and not self.attest:
            raise ValueError("live scans require attest=True (self-only)")
        return self


class GraphRef(Model):
    graph_id: str


class AttackResult(Model):
    paths: list[AttackPath]
    findings: list[RiskFinding]


class LeagueRunRequest(Model):
    graph_id: str
    rounds: int = Field(default=5, ge=1, le=50)


class RunRef(Model):
    run_id: str


class Event(Model):
    """SSE payload on GET /api/events."""
    type: Literal["progress", "round", "done", "error"]
    run_id: str
    data: dict = Field(default_factory=dict)
    ts: datetime = Field(default_factory=now)
