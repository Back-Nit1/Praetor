"""Discover Token Factory NVIDIA models and derive tier recommendations from live metadata."""
from __future__ import annotations

import json
import os
import time
from collections.abc import Iterable
from typing import Any

import httpx
from dotenv import load_dotenv

DEFAULT_BASE_URL = "https://api.tokenfactory.nebius.com/v1"
TIERS = ("ULTRA", "SUPER", "NANO")


def _number(model: dict[str, Any], *paths: tuple[str, ...]) -> float | None:
    for path in paths:
        value: Any = model
        for part in path:
            if not isinstance(value, dict):
                value = None
                break
            value = value.get(part)
        try:
            if value is not None:
                return float(value)
        except (TypeError, ValueError):
            pass
    return None


def _signals(model: dict[str, Any]) -> dict[str, float | None]:
    prompt_price = _number(model, ("pricing", "prompt"), ("input_price_per_million_tokens",))
    completion_price = _number(model, ("pricing", "completion"), ("output_price_per_million_tokens",))
    price = None if prompt_price is None and completion_price is None else (prompt_price or 0) + (completion_price or 0)
    return {
        "quality": _number(model, ("quality",), ("size_b",)),
        "context": _number(model, ("context_length",), ("max_model_len",), ("context_window_k",)),
        "throughput": _number(model, ("tokens_per_second",), ("input_tps",)),
        "rpm": _number(model, ("per_request_limits", "requests_per_minute"), ("limits", "requests_per_minute")),
        "tpm": _number(model, ("per_request_limits", "tokens_per_minute"), ("limits", "tokens_per_minute")),
        "price": price,
    }


def _normalize(rows: list[dict[str, Any]], key: str, *, lower_is_better: bool = False) -> dict[str, float]:
    present = [(row["id"], row["signals"][key]) for row in rows if row["signals"][key] is not None]
    if not present:
        return {row["id"]: 0.0 for row in rows}
    values = [value for _, value in present]
    low, high = min(values), max(values)
    scores = {}
    for model_id, value in present:
        score = 1.0 if high == low else (value - low) / (high - low)
        scores[model_id] = 1.0 - score if lower_is_better else score
    return {row["id"]: scores.get(row["id"], 0.0) for row in rows}


def _is_nvidia(model: dict[str, Any]) -> bool:
    fields: Iterable[Any] = (model.get("id"), model.get("name"), model.get("vendor"), model.get("owned_by"))
    text = " ".join(str(value).lower() for value in fields if value)
    return "nvidia" in text or "nemotron" in text


def available_nvidia(models: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return NVIDIA text-generation entries exactly as advertised by the endpoint."""
    found = []
    for model in models:
        model_id = model.get("id")
        modality = str((model.get("architecture") or {}).get("modality", "")).lower()
        if isinstance(model_id, str) and _is_nvidia(model) and (not modality or "text" in modality):
            found.append(model)
    return sorted(found, key=lambda model: model["id"].lower())


def recommend_models(models: Iterable[dict[str, Any]]) -> dict[str, str]:
    """Rank only returned NVIDIA IDs using numeric fields from the verbose response."""
    candidates = available_nvidia(models)
    rows = [{"id": model["id"], "signals": _signals(model)} for model in candidates]
    if not rows:
        return {}
    if not any(value is not None for row in rows for value in row["signals"].values()):
        return {}

    normalized = {
        key: _normalize(rows, key, lower_is_better=key == "price")
        for key in ("quality", "context", "throughput", "rpm", "tpm", "price")
    }

    def rank(weights: dict[str, float], excluded: set[str] | None = None) -> str:
        pool = [row["id"] for row in rows if row["id"] not in (excluded or set())] or [row["id"] for row in rows]
        return max(pool, key=lambda model_id: (sum(normalized[key][model_id] * weight for key, weight in weights.items()), model_id))

    ultra = rank({"quality": 0.50, "context": 0.35, "throughput": 0.15})
    nano = rank({"throughput": 0.35, "tpm": 0.25, "rpm": 0.20, "price": 0.20}, {ultra})
    super_model = rank(
        {"quality": 0.30, "context": 0.20, "throughput": 0.20, "tpm": 0.10, "rpm": 0.10, "price": 0.10},
        {ultra, nano},
    )
    return {"MODEL_ULTRA": ultra, "MODEL_SUPER": super_model, "MODEL_NANO": nano}


def fetch_models(base_url: str, key: str) -> tuple[list[dict[str, Any]], int, float]:
    started = time.perf_counter()
    response = httpx.get(
        f"{base_url.rstrip('/')}/models",
        params={"verbose": "true"},
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
        timeout=30.0,
    )
    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    response.raise_for_status()
    payload = response.json()
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise ValueError("models endpoint returned an invalid data list")
    return data, response.status_code, elapsed_ms


def _error(exc: BaseException) -> dict[str, Any]:
    error: dict[str, Any] = {"type": type(exc).__name__}
    response = getattr(exc, "response", None)
    if response is not None:
        error["status_code"] = response.status_code
    return error


def main() -> int:
    load_dotenv()
    key = os.environ.get("NEBIUS_API_KEY")
    report: dict[str, Any] = {
        "model_ids": {"available_nvidia": [], "recommended": {}},
        "endpoint_result": "blocked",
        "timings_ms": {},
        "usage": {"models_returned": 0, "nvidia_models": 0},
        "errors": [],
    }
    if not key:
        report["errors"].append({"type": "missing_configuration", "fields": ["NEBIUS_API_KEY"]})
        print(json.dumps(report, indent=2, sort_keys=True))
        return 2

    try:
        models, status_code, elapsed_ms = fetch_models(os.environ.get("NEBIUS_BASE_URL", DEFAULT_BASE_URL), key)
        nvidia = available_nvidia(models)
        recommendations = recommend_models(models)
        report["model_ids"] = {
            "available_nvidia": [model["id"] for model in nvidia],
            "recommended": recommendations,
        }
        report["endpoint_result"] = f"http_{status_code}"
        report["timings_ms"] = {"models": elapsed_ms}
        report["usage"] = {"models_returned": len(models), "nvidia_models": len(nvidia)}
        if not nvidia:
            report["errors"].append({"type": "no_nvidia_models"})
        elif not recommendations:
            report["errors"].append({"type": "insufficient_verbose_metadata"})
    except (httpx.HTTPError, ValueError) as exc:
        report["endpoint_result"] = "error"
        report["errors"].append(_error(exc))

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not report["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
