from types import SimpleNamespace as NS

from core import ledger
from scripts.check_models import available_nvidia, recommend_models
from scripts.smoke_models import run_smoke


class FakeSDK:
    def __init__(self):
        self.replies = ['{"ok": true}', "OK"]
        self.chat = NS(completions=NS(create=self._create))

    def _create(self, **_request):
        return NS(
            choices=[NS(message=NS(content=self.replies.pop(0)))],
            usage=NS(prompt_tokens=4, completion_tokens=2),
        )


def test_recommendations_only_use_returned_nvidia_verbose_metadata():
    models = [
        {
            "id": "nvidia/example-deep",
            "architecture": {"modality": "text->text"},
            "quality": 10,
            "context_length": 200,
            "tokens_per_second": 2,
            "pricing": {"prompt": "9", "completion": "9"},
        },
        {
            "id": "nvidia/example-fast",
            "architecture": {"modality": "text->text"},
            "quality": 2,
            "context_length": 20,
            "tokens_per_second": 100,
            "pricing": {"prompt": "1", "completion": "1"},
        },
        {
            "id": "nvidia/example-balanced",
            "architecture": {"modality": "text->text"},
            "quality": 7,
            "context_length": 100,
            "tokens_per_second": 60,
            "pricing": {"prompt": "4", "completion": "4"},
        },
        {"id": "other/example", "quality": 99, "tokens_per_second": 999},
    ]

    assert [model["id"] for model in available_nvidia(models)] == [
        "nvidia/example-balanced", "nvidia/example-deep", "nvidia/example-fast"
    ]
    assert recommend_models(models) == {
        "MODEL_ULTRA": "nvidia/example-deep",
        "MODEL_SUPER": "nvidia/example-balanced",
        "MODEL_NANO": "nvidia/example-fast",
    }


def test_no_recommendation_without_returned_ranking_metadata():
    assert recommend_models([{"id": "nvidia/example"}]) == {}
    assert recommend_models([{"id": "other/example", "quality": 10}]) == {}


def test_smoke_calls_are_visible_in_ledger_without_capturing_outputs(tmp_path, monkeypatch):
    monkeypatch.setenv("NEMESIS_LEDGER_DB", str(tmp_path / "ledger.sqlite"))
    report = run_smoke(FakeSDK(), {"NANO": "nvidia/example-nano", "SUPER": "nvidia/example-super"})

    assert report["errors"] == []
    assert report["endpoint_result"] == {
        "NANO": {"status": "ok", "ledger_recorded": True},
        "SUPER": {"status": "ok", "ledger_recorded": True},
    }
    assert [entry.purpose for entry in ledger.entries()] == ["smoke", "smoke"]
    assert "OK" not in str(report) and "Return JSON" not in str(report)
