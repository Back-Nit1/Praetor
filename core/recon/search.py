"""Guarded Tavily wrapper: guard -> cache -> query budget -> (ledger -> call, retried on transient errors).

Live search is self-only: attest=True, persona_id="self", demo mode off, and never a relative/associate token.
Queries carry the user's own identifiers on purpose, so the ledger records them as itemized, not redacted.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from tavily import TavilyClient
from tavily.errors import TimeoutError as TavilyTimeout

from core import ledger
from core.recon.facts import TOKEN
from core.schemas import Seeds

RETRYABLE = (TavilyTimeout, requests.ConnectionError, requests.Timeout)
MAX_QUERY_CHARS = 400  # Tavily's own limit


class QueryBudgetExceeded(RuntimeError):
    pass


def _env(name: str, default: str | None = None) -> str | None:
    """PRAETOR_* wins; NEMESIS_* is the legacy prefix."""
    return os.environ.get(f"PRAETOR_{name}", os.environ.get(f"NEMESIS_{name}", default))


def demo_mode() -> bool:
    return "1" in (os.environ.get("PRAETOR_DEMO_MODE"), os.environ.get("NEMESIS_DEMO_MODE"))  # fail closed on either


def check_live(attest: bool, persona_id: str = "self") -> None:
    if demo_mode():
        raise PermissionError("demo mode: live search is disabled (synthetic personas only)")
    if attest is not True:
        raise ValueError("live search requires attest=True (self-only)")
    if persona_id != "self":
        raise ValueError("live search runs for persona_id='self' only")


def queries_for(seeds: Seeds) -> list[str]:
    """The only queries recon generates. Built from the user's own seeds; relative tokens are refused."""
    fields = [seeds.name, seeds.city or "", *seeds.emails, *seeds.handles]
    if any(TOKEN.search(f) for f in fields):
        raise ValueError("seeds must be the user's own identifiers, not relative tokens")
    who = f'"{seeds.name.strip()}"' + (f" {seeds.city.strip()}" if seeds.city else "")
    return [who, f"{who} people search address phone", *(f'"{e}"' for e in seeds.emails), *(f'"{h}"' for h in seeds.handles)]


class Searcher:
    """One per run: `max_queries` is a per-instance budget. Cache hits cost no budget and leave no ledger entry."""

    def __init__(self, attest: bool, persona_id: str = "self", client=None, *, max_queries: int | None = None,
                 timeout: float = 15.0, max_retries: int = 2, backoff: float = 0.5, max_results: int = 5,
                 cache_dir: str | Path | None = None, sleep=time.sleep):
        """`client` is anything shaped like `TavilyClient` (tests pass a fake)."""
        self.attest, self.persona_id, self._client = attest, persona_id, client
        self.max_queries = max_queries if max_queries is not None else int(_env("TAVILY_MAX_QUERIES", "20"))
        self.timeout, self.max_retries, self.backoff, self.max_results, self._sleep = (
            timeout, max_retries, backoff, max_results, sleep)
        if cache_dir is None and _env("CACHE", "1") == "1":
            cache_dir = _env("TAVILY_CACHE_DIR", ".cache/tavily")
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.used = 0

    def _tavily(self):
        if self._client is None:
            load_dotenv()
            key = os.environ.get("TAVILY_API_KEY")
            if not key:
                raise RuntimeError("TAVILY_API_KEY is not set")
            self._client = TavilyClient(api_key=key)
        return self._client

    def search(self, query: str) -> list[dict]:
        check_live(self.attest, self.persona_id)
        query = query.strip()
        if not query or len(query) > MAX_QUERY_CHARS:
            raise ValueError(f"query must be 1-{MAX_QUERY_CHARS} chars")
        if TOKEN.search(query):
            raise ValueError("refusing to search for a relative/associate token")
        params = {"query": query, "search_depth": "basic", "max_results": self.max_results, "include_answer": False}
        payload = json.dumps(params, sort_keys=True)

        cache_file = self.cache_dir / f"{hashlib.sha256(payload.encode()).hexdigest()}.json" if self.cache_dir else None
        if cache_file:
            try:
                return json.loads(cache_file.read_text())
            except (OSError, ValueError):
                pass  # miss or corrupt entry: fall through to a live call
        if self.used >= self.max_queries:
            raise QueryBudgetExceeded(f"query budget {self.max_queries} exhausted")
        self.used += 1

        client = self._tavily()
        for attempt in range(self.max_retries + 1):
            ledger.record("tavily", "recon-search", payload)  # every attempt leaves the machine
            try:
                resp = client.search(timeout=self.timeout, **params)
                break
            except RETRYABLE:
                if attempt == self.max_retries:
                    raise
                self._sleep(self.backoff * 2**attempt)
        results = [{k: r[k] for k in ("title", "url", "content") if k in r}
                   for r in resp.get("results", []) if isinstance(r, dict)]
        if cache_file:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps(results))
        return results
