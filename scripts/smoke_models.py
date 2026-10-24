"""Minimal live Token Factory smoke calls with metadata-only output."""
from __future__ import annotations

import json
import os
import time
from typing import Any

import openai
from dotenv import load_dotenv

from core import ledger
from core.llm import Client

try:  # support both `python -m scripts.smoke_models` and `python scripts/smoke_models.py`
    from scripts.check_models import DEFAULT_BASE_URL
except ModuleNotFoundError:
    from check_models import DEFAULT_BASE_URL


def _usage_delta(after: dict[str, Any], before: dict[str, Any]) -> dict[str, Any]:
    return {key: after[key] - before[key] for key in ("calls", "prompt_tokens", "completion_tokens", "usd")}


def _error(exc: BaseException) -> dict[str, Any]:
    result: dict[str, Any] = {"type": type(exc).__name__}
    status_code = getattr(exc, "status_code", None)
    if status_code is not None:
        result["status_code"] = status_code
    return result


def run_smoke(sdk: Any, models: dict[str, str]) -> dict[str, Any]:
    client = Client(sdk, models, cache_dir="", max_output_tokens=64, max_retries=0)
    report: dict[str, Any] = {
        "model_ids": {tier: models[tier] for tier in ("NANO", "SUPER")},
        "endpoint_result": {},
        "timings_ms": {},
        "usage": {},
        "errors": [],
    }
    calls = {
        "NANO": (
            [{"role": "user", "content": "Return JSON with ok set to true."}],
            {
                "type": "object",
                "properties": {"ok": {"type": "boolean"}},
                "required": ["ok"],
                "additionalProperties": False,
            },
        ),
        "SUPER": ([{"role": "user", "content": "Reply with OK."}], None),
    }
    for tier, (messages, schema) in calls.items():
        entries_before = len(ledger.entries())
        usage_before = dict(client.usage)
        started = time.perf_counter()
        try:
            output = client.chat(tier, messages, "smoke", schema)
            valid = output == {"ok": True} if tier == "NANO" else isinstance(output, str) and bool(output.strip())
            status = "ok" if valid else "invalid_response"
        except (openai.OpenAIError, RuntimeError, ValueError) as exc:
            status = "error"
            report["errors"].append({"tier": tier, **_error(exc)})
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        new_entries = ledger.entries()[entries_before:]
        report["endpoint_result"][tier] = {
            "status": status,
            "ledger_recorded": any(entry.service == "tokenfactory" for entry in new_entries),
        }
        report["timings_ms"][tier] = elapsed_ms
        report["usage"][tier] = _usage_delta(client.usage, usage_before)
    return report


def main() -> int:
    load_dotenv()
    required = ("NEBIUS_API_KEY", "MODEL_NANO", "MODEL_SUPER")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        print(json.dumps({
            "model_ids": {},
            "endpoint_result": "blocked",
            "timings_ms": {},
            "usage": {},
            "errors": [{"type": "missing_configuration", "fields": missing}],
        }, indent=2, sort_keys=True))
        return 2

    sdk = openai.OpenAI(
        api_key=os.environ["NEBIUS_API_KEY"],
        base_url=os.environ.get("NEBIUS_BASE_URL", DEFAULT_BASE_URL),
        timeout=60.0,
        max_retries=0,
    )
    report = run_smoke(sdk, {tier: os.environ[f"MODEL_{tier}"] for tier in ("NANO", "SUPER")})
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not report["errors"] and all(
        result["status"] == "ok" and result["ledger_recorded"] for result in report["endpoint_result"].values()
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
