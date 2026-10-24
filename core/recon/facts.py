"""Fact normalization + dedup. Pure and deterministic. Relatives are tokenized here, so no name goes downstream."""
import re
from itertools import count
from urllib.parse import urlparse

from core.schemas import Fact

TOKEN = re.compile(r"relative_\d+")
_ABBR = {"street": "st", "avenue": "ave", "road": "rd"}


def host(f: Fact) -> str:
    return (urlparse(f.source_url).hostname or "") if f.source_url else ""


def _display(kind: str, value: str) -> str:
    v = " ".join(value.split())
    if kind == "email":
        return v.lower()
    if kind == "handle":
        return v.lstrip("@")
    if kind == "phone":
        d = re.sub(r"\D", "", v)
        if len(d) == 11 and d[0] == "1":
            d = d[1:]
        if len(d) >= 7:
            return "-".join(p for p in (d[:-7], d[-7:-4], d[-4:]) if p)
    return v


def key(kind: str, display: str) -> str:
    k = display.casefold()
    if kind in ("email", "handle", "phone", "relative_token"):
        return k
    words = re.sub(r"[^\w\s]", "", k).split()
    return " ".join(_ABBR.get(w, w) if kind == "address" else w for w in words)


def fact_key(f: Fact) -> tuple[str, str]:
    return f.kind, key(f.kind, f.value)


def normalize_facts(facts: list[Fact]) -> list[Fact]:
    """Canonical values, one fact per (kind, value, source), sorted. Idempotent."""
    raw = sorted({" ".join(f.value.split()) for f in facts if f.kind == "relative_token"}, key=lambda s: (len(s), s))
    tok = {r: r for r in raw if TOKEN.fullmatch(r)}
    free = (t for i in count(1) if (t := f"relative_{i}") not in tok.values())
    tok |= {r: next(free) for r in raw if r not in tok}
    best: dict[tuple, Fact] = {}
    for f in facts:
        if f.kind == "relative_token":
            g = f.model_copy(update={"value": (v := tok[" ".join(f.value.split())]), "id": f"rel-{v}-{f.source_kind}"})
        else:
            g = f.model_copy(update={"value": _display(f.kind, f.value)})
        k = (*fact_key(g), g.source_kind, host(g))
        old = best.get(k)
        if old is None or (-g.confidence, g.found_at, g.id) < (-old.confidence, old.found_at, old.id):
            best[k] = g
    return [best[k] for k in sorted(best)]
