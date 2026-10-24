"""Offline synthetic personas: data/synthetic/<id>/{truth,public}.json. `public` is the simulated footprint;
`truth.findable` is what a stranger could really find, `truth.private` never leaves the persona."""
import json
from pathlib import Path

from pydantic import TypeAdapter

from core.schemas import Fact

ROOT = Path(__file__).resolve().parents[2] / "data" / "synthetic"
_FACTS = TypeAdapter(list[Fact])


def list_personas() -> list[dict]:
    return [{"id": d.name, "name": json.loads((d / "truth.json").read_text())["name"]}
            for d in sorted(ROOT.iterdir()) if (d / "truth.json").is_file()]


def _dir(persona_id: str) -> Path:
    if persona_id not in {p["id"] for p in list_personas()}:  # allowlist: no path built from raw input
        raise ValueError(f"unknown synthetic persona: {persona_id!r}")
    return ROOT / persona_id


def load_public(persona_id: str) -> list[Fact]:
    return _FACTS.validate_json((_dir(persona_id) / "public.json").read_bytes())


def load_truth(persona_id: str) -> list[Fact]:
    """Findable ground truth, for twin_gap()."""
    return _FACTS.validate_python(json.loads((_dir(persona_id) / "truth.json").read_text())["findable"])
