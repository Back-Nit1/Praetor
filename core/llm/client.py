"""OpenAI-compatible Token Factory client: redact -> budget check -> cache -> ledger -> call -> rehydrate."""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path

import openai
from dotenv import load_dotenv

from core import ledger
from core.llm.redact import redact, rehydrate

TIERS = ("ULTRA", "SUPER", "NANO")
RETRYABLE = (openai.APIConnectionError, openai.RateLimitError, openai.InternalServerError)  # timeouts subclass the first


class BudgetExceeded(RuntimeError):
    pass


def _rehydrate_any(obj, mapping):
    if isinstance(obj, str):
        return rehydrate(obj, mapping)
    if isinstance(obj, list):
        return [_rehydrate_any(v, mapping) for v in obj]
    if isinstance(obj, dict):
        return {k: _rehydrate_any(v, mapping) for k, v in obj.items()}
    return obj


class Client:
    def __init__(self, sdk, models: dict[str, str] | None = None, *, max_tokens_ceiling: int | None = None,
                 max_usd: float | None = None, prices: dict[str, tuple[float, float]] | None = None,
                 cache_dir: str | Path | None = None, max_retries: int = 3, backoff: float = 0.5,
                 max_output_tokens: int = 2048, sleep=time.sleep):
        """`sdk` is anything shaped like `openai.OpenAI` (tests pass a fake). `prices[tier]` = USD per 1M (in, out)
        tokens; unset tiers are covered by the token ceiling only — prices are never guessed."""
        env = os.environ.get
        self.sdk = sdk
        self.models = models or {t: env(f"MODEL_{t}", "") for t in TIERS}
        self.ceiling = max_tokens_ceiling if max_tokens_ceiling is not None else int(env("PRAETOR_MAX_TOKENS", "2000000"))
        self.max_usd = max_usd if max_usd is not None else float(env("PRAETOR_MAX_USD", "15"))
        self.prices = prices if prices is not None else {
            t: (float(env(f"PRICE_{t}_IN_PER_MTOK")), float(env(f"PRICE_{t}_OUT_PER_MTOK")))
            for t in TIERS if env(f"PRICE_{t}_IN_PER_MTOK") and env(f"PRICE_{t}_OUT_PER_MTOK")
        }
        if cache_dir is None and env("PRAETOR_CACHE", "1") == "1":
            cache_dir = env("PRAETOR_CACHE_DIR", ".cache/llm")
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.max_retries, self.backoff, self.max_output_tokens, self._sleep = max_retries, backoff, max_output_tokens, sleep
        self._lock = threading.Lock()
        self.usage = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "usd": 0.0}

    def _cost(self, tier: str, tokens_in: int, tokens_out: int) -> float:
        pin, pout = self.prices.get(tier, (0.0, 0.0))
        return (tokens_in * pin + tokens_out * pout) / 1e6

    def _check_budget(self, tier: str, request_bytes: int) -> None:
        est_in = request_bytes // 4 + 1  # ponytail: crude 4 bytes/token estimate; real usage replaces it after the call
        with self._lock:
            used = self.usage["prompt_tokens"] + self.usage["completion_tokens"]
            if used + est_in + self.max_output_tokens > self.ceiling:
                raise BudgetExceeded(f"token ceiling {self.ceiling} would be exceeded ({used} used)")
            if tier in self.prices and self.usage["usd"] + self._cost(tier, est_in, self.max_output_tokens) > self.max_usd:
                raise BudgetExceeded(f"USD cap {self.max_usd} would be exceeded (${self.usage['usd']:.4f} used)")

    def _call(self, tier: str, request: dict, purpose: str, redactions: int):
        payload = json.dumps(request, sort_keys=True).encode()
        self._check_budget(tier, len(payload))
        for attempt in range(self.max_retries + 1):
            ledger.record("tokenfactory", purpose, payload, redactions)  # every attempt may leave the machine
            try:
                resp = self.sdk.chat.completions.create(**request)
                break
            except RETRYABLE:
                if attempt == self.max_retries:
                    raise
                self._sleep(self.backoff * 2**attempt)
        u = getattr(resp, "usage", None)
        tin = (u.prompt_tokens if u else None) or len(payload) // 4
        tout = (u.completion_tokens if u else None) or 0
        with self._lock:
            self.usage["calls"] += 1
            self.usage["prompt_tokens"] += tin
            self.usage["completion_tokens"] += tout
            self.usage["usd"] += self._cost(tier, tin, tout)
        return resp.choices[0].message.content or ""

    def chat(self, tier: str, messages: list[dict], purpose: str, json_schema: dict | None = None) -> str | dict:
        if tier not in TIERS:
            raise ValueError(f"unknown tier {tier!r}; expected one of {TIERS}")
        model = self.models.get(tier)
        if not model:
            raise RuntimeError(f"MODEL_{tier} is not set")
        mapping: dict[str, str] = {}
        safe = [{**m, "content": redact(m["content"], mapping)[0]} for m in messages]  # shared map: stable placeholders
        request = {"model": model, "messages": safe, "max_tokens": self.max_output_tokens}
        if json_schema is not None:
            request["response_format"] = {"type": "json_schema", "json_schema": {"name": "response", "schema": json_schema, "strict": True}}

        cache_file = None
        if self.cache_dir:  # cache holds model output with placeholders only; the map is never persisted
            key = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
            cache_file = self.cache_dir / f"{key}.json"
            if cache_file.exists():
                text = json.loads(cache_file.read_text())["text"]
                return _rehydrate_any(json.loads(text) if json_schema is not None else text, mapping)

        text = self._call(tier, request, purpose, len(mapping))
        parsed = json.loads(text) if json_schema is not None else text  # bad JSON raises before anything is cached
        if cache_file:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps({"text": text}))
        return _rehydrate_any(parsed, mapping)


_default: Client | None = None


def chat(tier: str, messages: list[dict], purpose: str, json_schema: dict | None = None) -> str | dict:
    global _default
    if _default is None:
        load_dotenv()
        key = os.environ.get("NEBIUS_API_KEY")
        if not key:
            raise RuntimeError("NEBIUS_API_KEY is not set")
        sdk = openai.OpenAI(api_key=key, base_url=os.environ.get("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1"),
                            timeout=60.0, max_retries=0)  # we own retry/backoff so every attempt hits the ledger
        _default = Client(sdk)
    return _default.chat(tier, messages, purpose, json_schema)
