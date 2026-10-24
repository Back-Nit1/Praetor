"""Facts -> ExposureGraph. Pure and deterministic: same facts in any order give the same ids, order and built_at.

Fix ids are `<kind>:<node_id>` (docs/CONTRACTS.md); every target is a node in the graph.
"""
import re
from datetime import UTC, datetime

from core.recon.facts import fact_key, host, normalize_facts
from core.schemas import Edge, ExposureGraph, Fact, Node

IDENTIFIERS = ("address", "phone", "email", "employer", "handle", "relative_token", "photo_meta")
_FIRST = {"email": "email_personal"}  # id of the first node of a kind (kind name otherwise)
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def _slug(s: str) -> str:
    return re.sub(r"\W+", "_", s.casefold()).strip("_")


def build_graph(facts: list[Fact], persona_id: str = "self") -> ExposureGraph:
    facts = normalize_facts(facts)
    nodes: dict[str, Node] = {}
    edges: dict[str, Edge] = {}

    def node(id, type, label, f: Fact | None = None, public=True, **attrs):
        if f:
            attrs |= dict(zip(("kind", "key"), fact_key(f)))
        nodes.setdefault(id, Node(id=id, type=type, label=label, attrs=attrs, public=public))

    def edge(src, dst, rel, effort, fixes=()):
        e = edges.setdefault(f"{src}->{dst}", Edge(src=src, dst=dst, rel=rel, effort=effort))
        e.effort = min(e.effort, effort)
        e.fixable_by = sorted({*e.fixable_by, *fixes})

    # person
    names = [f for f in facts if f.kind == "name"]
    who = max(names, key=lambda f: (f.confidence, f.value), default=None)
    node("person", "person", who.value if who else "Unknown", who)

    # brokers (listings first so their label wins)
    broker: dict[str, str] = {}  # host -> node id
    for f in sorted((f for f in facts if f.source_kind == "broker"), key=lambda f: f.kind != "listing"):
        bid = broker.setdefault(host(f), f"broker_{_slug(host(f).split('.')[0]) or 'unknown'}")
        node(bid, "broker", f.value if f.kind == "listing" else host(f) or "unknown broker",
             f if f.kind == "listing" else None, **({"url": f.source_url} if f.source_url else {}))
        edge("person", bid, "listed_on", 0.05, [f"optout:{bid}"])

    # breaches
    breaches = []
    for f in (f for f in facts if f.kind == "breach"):
        year = re.search(r"\b(?:19|20)\d\d\b", f.value)
        bid = f"breach_{year[0] if year else _slug(f.value)}"
        node(bid, "event", f.value, f, **({"year": int(year[0])} if year else {}))
        edge("person", bid, "related_to", 0.3)
        breaches.append(bid)
    breaches.sort()

    # accounts
    socials = []
    for f in (f for f in facts if f.kind == "account"):
        aid = f"acct_{_slug(f.value)}"
        node(aid, "account", f"{f.value.title()} account", f, public=f.source_kind == "social")
        if f.source_kind == "social":
            edge("person", aid, "owns", 0.1)
            socials.append(aid)
    socials.sort()

    # identifiers: one node per (kind, value), one edge per place it was seen
    groups: dict[tuple, list[Fact]] = {}
    for f in facts:
        if f.kind in IDENTIFIERS:
            groups.setdefault(fact_key(f), []).append(f)
    seen: dict[str, int] = {}
    ids: dict[str, list[str]] = {}
    for (kind, _), grp in sorted(groups.items()):
        n = seen[kind] = seen.get(kind, -1) + 1
        best = max(grp, key=lambda f: (f.confidence, f.value))
        nid = best.value if kind == "relative_token" else _FIRST.get(kind, kind) if n == 0 else f"{kind}_{n + 1}"
        ids.setdefault(kind, []).append(nid)
        node(nid, {"relative_token": "relative_token", "photo_meta": "asset"}.get(kind, "identifier"),
             best.value, best)
        for f in grp:
            if f.source_kind == "broker":
                b = broker[host(f)]
                edge(b, nid, "reveals", 0.1, [f"optout:{b}"])
            elif f.source_kind == "breach" and breaches:  # ponytail: first breach only; link by source host if >1 matters
                edge(breaches[0], nid, "reveals", 0.2, [f"alias_swap:{nid}"] if kind == "email" else [])
            elif f.source_kind == "social" and socials:
                edge(socials[0], nid, "reveals", 0.1, [f"privacy_setting:{socials[0]}"])
            else:
                edge("person", nid, "reveals", 0.2 if f.source_kind == "public_record" else 0.3)

    # home location: from any address, or a geotagged photo
    if ids.get("address") or ids.get("photo_meta"):
        node("asset_location", "asset", "Home location", public=False)
        for a in ids.get("address", []):
            edge(a, "asset_location", "reveals", 0.1,
                 [x for e in edges.values() if e.dst == a and e.src.startswith("broker_") for x in e.fixable_by])
        for p in ids.get("photo_meta", []):
            edge(p, "asset_location", "reveals", 0.3, [f"privacy_setting:{socials[0]}"] if socials else [])

    # account takeover chain: phone/email -> webmail -> other accounts -> funds
    if "acct_email" in nodes:
        for p in ids.get("phone", []):
            edge(p, "acct_email", "verifies", 0.5, ["passkey:acct_email", "recovery_change:acct_email"])
        if ids.get("email"):  # ponytail: assumes the first email is the webmail address
            edge(ids["email"][0], "acct_email", "recovers", 0.6, [f"alias_swap:{ids['email'][0]}"])
        for aid in [a for a in nodes if a.startswith("acct_") and a not in ("acct_email", *socials)]:
            edge("acct_email", aid, "recovers", 0.3, [f"recovery_change:{aid}"])
    for aid in ("acct_bank", "acct_payments"):
        if aid in nodes:
            node("asset_funds", "asset", "Funds", public=False)
            edge(aid, "asset_funds", "owns", 0.4, [f"passkey:{aid}"])

    return ExposureGraph(
        id=f"g-{persona_id}", persona_id=persona_id,
        nodes=sorted(nodes.values(), key=lambda n: n.id), edges=sorted(edges.values(), key=lambda e: e.key),
        built_at=max((f.found_at for f in facts), default=_EPOCH),
    )
