import os

import openai
import pytest
from dotenv import load_dotenv

from scripts.check_models import DEFAULT_BASE_URL, available_nvidia, fetch_models, recommend_models
from scripts.smoke_models import run_smoke

pytestmark = pytest.mark.network


def _configuration(*names):
    load_dotenv()
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        pytest.skip(f"missing live Token Factory configuration: {', '.join(missing)}")
    return os.environ


def test_live_model_discovery_returns_rankable_nvidia_models():
    env = _configuration("NEBIUS_API_KEY")
    models, status_code, _ = fetch_models(env.get("NEBIUS_BASE_URL", DEFAULT_BASE_URL), env["NEBIUS_API_KEY"])
    assert status_code == 200
    assert available_nvidia(models)
    assert set(recommend_models(models)) == {"MODEL_ULTRA", "MODEL_SUPER", "MODEL_NANO"}


def test_live_nano_and_super_smoke_are_ledgered():
    env = _configuration("NEBIUS_API_KEY", "MODEL_NANO", "MODEL_SUPER")
    sdk = openai.OpenAI(
        api_key=env["NEBIUS_API_KEY"],
        base_url=env.get("NEBIUS_BASE_URL", DEFAULT_BASE_URL),
        timeout=60.0,
        max_retries=0,
    )
    report = run_smoke(sdk, {tier: env[f"MODEL_{tier}"] for tier in ("NANO", "SUPER")})
    assert report["errors"] == []
    assert all(result == {"status": "ok", "ledger_recorded": True} for result in report["endpoint_result"].values())
